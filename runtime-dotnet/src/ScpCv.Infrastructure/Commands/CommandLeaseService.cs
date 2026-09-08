using Microsoft.EntityFrameworkCore;
using ScpCv.Domain.Model;
using ScpCv.Infrastructure.Persistence;
using ScpCv.Infrastructure.Runtime;

namespace ScpCv.Infrastructure.Commands;

public sealed record LeaseClaimRequest(
    CommandTargetKind TargetKind,
    int TargetId,
    Guid WorkerInstanceId,
    long OwnerEpoch,
    long GroupEpoch,
    TimeSpan LeaseDuration);

public sealed class CommandLeaseService(
    CommandRepository commands,
    RuntimeAuthorityRepository authority,
    IDbContextFactory<ControlDbContext> contextFactory,
    WriteCoordinator writes,
    TimeProvider? timeProvider = null)
{
    private readonly TimeProvider _timeProvider = timeProvider ?? TimeProvider.System;

    public async Task<CommandRecord?> ClaimAsync(
        LeaseClaimRequest request,
        CancellationToken cancellationToken = default)
    {
        await EnsureWorkerAsync(request, cancellationToken).ConfigureAwait(false);
        return await commands.ClaimAsync(
                new ClaimCommand(
                    request.TargetKind,
                    request.TargetId,
                    request.WorkerInstanceId,
                    request.OwnerEpoch,
                    request.GroupEpoch,
                    request.LeaseDuration),
                cancellationToken)
            .ConfigureAwait(false);
    }

    public Task<bool> RenewAsync(
        Guid commandId,
        Guid claimToken,
        long ownerEpoch,
        TimeSpan leaseDuration,
        CancellationToken cancellationToken = default) =>
        commands.RenewLeaseAsync(commandId, claimToken, ownerEpoch, leaseDuration, cancellationToken);

    /// <summary>
    /// 租约过期只说明旧端失联。只有 Supervisor 已证明旧进程退出时，才可重新置回 pending。
    /// </summary>
    public async Task<CommandRecord?> RequeueExpiredAsync(
        CommandTargetKind targetKind,
        int targetId,
        long groupEpoch,
        Guid newWorkerInstanceId,
        long newOwnerEpoch,
        bool previousOwnerExitConfirmed,
        CancellationToken cancellationToken = default)
    {
        if (!previousOwnerExitConfirmed)
        {
            return null;
        }

        await using var context = await contextFactory.CreateDbContextAsync(cancellationToken).ConfigureAwait(false);
        var group = await context.RuntimeGroupControls.AsNoTracking().SingleAsync(cancellationToken).ConfigureAwait(false);
        if (group.State != RuntimeGroupState.Armed || group.GroupEpoch != groupEpoch)
        {
            return null;
        }

        return await writes.ExecuteAsync(
                async (database, token) =>
                {
                    var now = _timeProvider.GetUtcNow();
                    var command = await database.CommandRecords
                        .Where(item => item.TargetKind == targetKind &&
                                       item.TargetId == targetId &&
                                       item.Status == CommandStatus.Processing &&
                                       item.LeaseExpiresAt != null &&
                                       item.LeaseExpiresAt <= now)
                        .OrderBy(item => item.TargetSequence)
                        .FirstOrDefaultAsync(token)
                        .ConfigureAwait(false);
                    if (command is null)
                    {
                        return null;
                    }

                    command.Status = CommandStatus.Pending;
                    command.ConsumerInstanceId = null;
                    command.ClaimToken = null;
                    command.LeaseExpiresAt = null;
                    command.OwnerEpoch = newOwnerEpoch;
                    command.LastError = $"旧 Worker {newWorkerInstanceId:N} 已由 Supervisor 确认退出后重新领取。";
                    return command;
                },
                cancellationToken)
            .ConfigureAwait(false);
    }

    private async Task EnsureWorkerAsync(LeaseClaimRequest request, CancellationToken cancellationToken)
    {
        var group = await authority.GetGroupAsync(cancellationToken).ConfigureAwait(false);
        if (group.State != RuntimeGroupState.Armed || group.GroupEpoch != request.GroupEpoch)
        {
            throw new CommandFenceException("运行组未 armed 或 group epoch 已失效。");
        }

        await using var context = await contextFactory.CreateDbContextAsync(cancellationToken).ConfigureAwait(false);
        var worker = await context.WorkerOwnerships.AsNoTracking().SingleOrDefaultAsync(
                item => item.TargetKind == request.TargetKind && item.TargetId == request.TargetId,
                cancellationToken)
            .ConfigureAwait(false);
        if (worker is null ||
            worker.WorkerInstanceId != request.WorkerInstanceId ||
            worker.OwnerEpoch != request.OwnerEpoch ||
            worker.Status != WorkerOwnershipState.Online)
        {
            throw new CommandFenceException("Worker instance/owner epoch 未获授权。");
        }
    }
}
