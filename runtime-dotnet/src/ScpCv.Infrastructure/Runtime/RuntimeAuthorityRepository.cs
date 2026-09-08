using Microsoft.EntityFrameworkCore;
using ScpCv.Domain.Model;
using ScpCv.Infrastructure.Persistence;

namespace ScpCv.Infrastructure.Runtime;

public sealed class RuntimeAuthorityRepository(
    IDbContextFactory<ControlDbContext> contextFactory,
    WriteCoordinator writes,
    TimeProvider? timeProvider = null)
{
    private readonly TimeProvider _timeProvider = timeProvider ?? TimeProvider.System;
    public async Task<RuntimeGroupControl> GetGroupAsync(CancellationToken cancellationToken = default)
    {
        await using var context = await contextFactory.CreateDbContextAsync(cancellationToken).ConfigureAwait(false);
        return await context.RuntimeGroupControls.AsNoTracking().SingleAsync(cancellationToken).ConfigureAwait(false);
    }

    public Task<RuntimeGroupControl> BeginStartAsync(
        Guid requestId,
        CancellationToken cancellationToken = default) =>
        writes.ExecuteAsync(
            async (context, token) =>
            {
                var group = await context.RuntimeGroupControls.SingleAsync(token).ConfigureAwait(false);
                if (group.State is RuntimeGroupState.Starting or RuntimeGroupState.Armed)
                {
                    if (group.ExplicitStartRequestId == requestId)
                    {
                        return group;
                    }

                    throw new RuntimeAuthorityException("运行组已由另一个显式启动请求持有。");
                }

                if (group.State == RuntimeGroupState.Draining)
                {
                    throw new RuntimeAuthorityException("运行组仍在停止清理，不能启动。");
                }

                group.GroupEpoch = checked(group.GroupEpoch + 1);
                group.State = RuntimeGroupState.Starting;
                group.StopReason = string.Empty;
                group.ExplicitStartRequestId = requestId;
                return group;
            },
            cancellationToken);

    public Task<RuntimeGroupControl> ArmAsync(
        Guid requestId,
        long expectedGroupEpoch,
        CancellationToken cancellationToken = default) =>
        writes.ExecuteAsync(
            async (context, token) =>
            {
                var group = await context.RuntimeGroupControls.SingleAsync(token).ConfigureAwait(false);
                if (group.State != RuntimeGroupState.Starting ||
                    group.GroupEpoch != expectedGroupEpoch ||
                    group.ExplicitStartRequestId != requestId)
                {
                    throw new RuntimeAuthorityException("显式启动身份或 group epoch 已失效。");
                }

                group.State = RuntimeGroupState.Armed;
                return group;
            },
            cancellationToken);

    public Task<RuntimeGroupControl> BeginDrainAsync(
        string reason,
        CancellationToken cancellationToken = default)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(reason);
        return writes.ExecuteAsync(
            async (context, token) =>
            {
                var group = await context.RuntimeGroupControls.SingleAsync(token).ConfigureAwait(false);
                if (group.State is RuntimeGroupState.Draining or RuntimeGroupState.Stopped)
                {
                    return group;
                }

                group.GroupEpoch = checked(group.GroupEpoch + 1);
                group.State = RuntimeGroupState.Draining;
                group.StopReason = reason;
                return group;
            },
            cancellationToken);
    }

    public Task<RuntimeGroupControl> CompleteStopAsync(
        long expectedGroupEpoch,
        CancellationToken cancellationToken = default) =>
        writes.ExecuteAsync(
            async (context, token) =>
            {
                var group = await context.RuntimeGroupControls.SingleAsync(token).ConfigureAwait(false);
                if (group.State != RuntimeGroupState.Draining || group.GroupEpoch != expectedGroupEpoch)
                {
                    throw new RuntimeAuthorityException("停止确认的 group epoch 已失效。");
                }

                group.State = RuntimeGroupState.Stopped;
                group.ExplicitStartRequestId = null;
                return group;
            },
            cancellationToken);

    public Task<WorkerOwnership> RegisterWorkerAsync(
        RegisterWorker request,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(request);
        return writes.ExecuteAsync(
            async (context, token) =>
            {
                var group = await context.RuntimeGroupControls.SingleAsync(token).ConfigureAwait(false);
                if (group.State is not (RuntimeGroupState.Starting or RuntimeGroupState.Armed) ||
                    group.GroupEpoch != request.GroupEpoch)
                {
                    throw new RuntimeAuthorityException("运行组未授权 Worker 登记。");
                }

                var ownership = await context.WorkerOwnerships.SingleOrDefaultAsync(
                        candidate =>
                            candidate.TargetKind == request.TargetKind && candidate.TargetId == request.TargetId,
                        token)
                    .ConfigureAwait(false);
                if (ownership is not null && ownership.WorkerInstanceId == request.WorkerInstanceId)
                {
                    if (ownership.ProcessId != request.ProcessId || ownership.ProcessStartTime != request.ProcessStartTime)
                    {
                        throw new RuntimeAuthorityException("相同 Worker instance_id 的进程身份不一致。");
                    }

                    ownership.LastTransportHeartbeat = _timeProvider.GetUtcNow();
                    ownership.CapabilitiesJson = request.CapabilitiesJson;
                    ownership.Status = WorkerOwnershipState.Online;
                    return ownership;
                }

                if (ownership is not null && !request.PreviousOwnerExitConfirmed)
                {
                    throw new RuntimeAuthorityException("旧 Worker 尚未证明退出，不能转移 owner epoch。");
                }

                var nextOwnerEpoch = checked((ownership?.OwnerEpoch ?? 0) + 1);
                if (ownership is null)
                {
                    ownership = new WorkerOwnership
                    {
                        TargetKind = request.TargetKind,
                        TargetId = request.TargetId,
                    };
                    context.WorkerOwnerships.Add(ownership);
                }

                ownership.WorkerInstanceId = request.WorkerInstanceId;
                ownership.ProcessId = request.ProcessId;
                ownership.ProcessStartTime = request.ProcessStartTime;
                ownership.LogonSessionId = request.LogonSessionId;
                ownership.OwnerEpoch = nextOwnerEpoch;
                ownership.LastTransportHeartbeat = _timeProvider.GetUtcNow();
                ownership.LastUiProgress = null;
                ownership.CapabilitiesJson = request.CapabilitiesJson;
                ownership.Status = WorkerOwnershipState.Online;
                return ownership;
            },
            cancellationToken);
    }

    public Task<bool> RecordHeartbeatAsync(
        CommandTargetKind targetKind,
        int targetId,
        Guid workerInstanceId,
        long ownerEpoch,
        bool uiProgress,
        CancellationToken cancellationToken = default) =>
        writes.ExecuteAsync(
            async (context, token) =>
            {
                var ownership = await context.WorkerOwnerships.SingleOrDefaultAsync(
                        candidate => candidate.TargetKind == targetKind && candidate.TargetId == targetId,
                        token)
                    .ConfigureAwait(false);
                if (ownership is null ||
                    ownership.WorkerInstanceId != workerInstanceId ||
                    ownership.OwnerEpoch != ownerEpoch)
                {
                    return false;
                }

                var now = _timeProvider.GetUtcNow();
                ownership.LastTransportHeartbeat = now;
                if (uiProgress)
                {
                    ownership.LastUiProgress = now;
                }

                return true;
            },
            cancellationToken);

    public Task<OfficeOperation> RegisterOfficeOperationAsync(
        RegisterOfficeOperation request,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(request);
        return writes.ExecuteAsync(
            async (context, token) =>
            {
                var existing = await context.OfficeOperations.SingleOrDefaultAsync(
                        operation => operation.OperationId == request.OperationId,
                        token)
                    .ConfigureAwait(false);
                if (existing is not null)
                {
                    if (Matches(existing, request))
                    {
                        return existing;
                    }

                    throw new OfficeOperationConflictException("同一 office_operation_id 的身份或参数不一致。");
                }

                var group = await context.RuntimeGroupControls.SingleAsync(token).ConfigureAwait(false);
                if (group.State != RuntimeGroupState.Armed || group.GroupEpoch != request.GroupEpoch)
                {
                    throw new RuntimeAuthorityException("运行组未授权 Office 操作。");
                }

                var operation = new OfficeOperation
                {
                    OperationId = request.OperationId,
                    ParentCommandId = request.ParentCommandId,
                    ParentJobId = request.ParentJobId,
                    ClaimToken = request.ClaimToken,
                    SourceGeneration = request.SourceGeneration,
                    GroupEpoch = request.GroupEpoch,
                    HostEpoch = request.HostEpoch,
                    SlotEpoch = request.SlotEpoch,
                    Deadline = request.Deadline,
                    RequestJson = request.RequestJson,
                };
                context.OfficeOperations.Add(operation);
                return operation;
            },
            cancellationToken);
    }

    public Task<OfficeResultAcceptance> CompleteOfficeOperationAsync(
        CompleteOfficeOperation result,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(result);
        if (result.Status is not (OperationStatus.Succeeded or OperationStatus.Failed or OperationStatus.Uncertain))
        {
            throw new ArgumentOutOfRangeException(nameof(result));
        }

        return writes.ExecuteAsync(
            async (context, token) =>
            {
                var operation = await context.OfficeOperations.SingleOrDefaultAsync(
                        candidate => candidate.OperationId == result.OperationId,
                        token)
                    .ConfigureAwait(false) ?? throw new KeyNotFoundException("Office 操作不存在。");
                if (operation.HostEpoch != result.HostEpoch || operation.SlotEpoch != result.SlotEpoch)
                {
                    throw new RuntimeAuthorityException("Office Host 或槽位 epoch 已失效。");
                }

                if (operation.Status is OperationStatus.Succeeded or OperationStatus.Failed or OperationStatus.Uncertain)
                {
                    if (string.Equals(operation.ResultFingerprint, result.ResultFingerprint, StringComparison.Ordinal))
                    {
                        return new OfficeResultAcceptance(Accepted: true, Duplicate: true);
                    }

                    throw new OfficeOperationConflictException("同一 Office 操作收到了不同结果指纹。");
                }

                operation.Status = result.Status;
                operation.ResultFingerprint = result.ResultFingerprint;
                operation.ErrorMessage = result.ErrorMessage;
                return new OfficeResultAcceptance(Accepted: true, Duplicate: false);
            },
            cancellationToken);
    }

    private static bool Matches(OfficeOperation operation, RegisterOfficeOperation request) =>
        operation.ParentCommandId == request.ParentCommandId &&
        operation.ParentJobId == request.ParentJobId &&
        operation.ClaimToken == request.ClaimToken &&
        operation.SourceGeneration == request.SourceGeneration &&
        operation.GroupEpoch == request.GroupEpoch &&
        operation.HostEpoch == request.HostEpoch &&
        operation.SlotEpoch == request.SlotEpoch &&
        operation.Deadline == request.Deadline &&
        string.Equals(operation.RequestJson, request.RequestJson, StringComparison.Ordinal);
}
