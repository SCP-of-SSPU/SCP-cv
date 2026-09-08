using Microsoft.EntityFrameworkCore;
using ScpCv.Domain.Model;
using ScpCv.Infrastructure.Persistence;

namespace ScpCv.Infrastructure.Commands;

public sealed class CommandRepository(
    WriteCoordinator writes,
    TimeProvider? timeProvider = null)
{
    private readonly TimeProvider _timeProvider = timeProvider ?? TimeProvider.System;
    private static readonly HashSet<string> DisplayReplacementCommands =
        new(StringComparer.Ordinal) { "OPEN", "CLOSE", "RESET_PPT" };

    private static readonly HashSet<string> CoalescingCommands =
        new(StringComparer.Ordinal) { "SEEK", "SET_LOOP", "SET_VOLUME", "SET_MUTE" };

    public Task<CommandRecord> EnqueueAsync(
        EnqueueCommand request,
        CancellationToken cancellationToken = default)
        => EnqueueAsync(request, projection: null, cancellationToken);

    /// <summary>
    /// 在同一短事务中写入 durable command 与兼容 pending 投影。
    /// 投影只允许修改当前事务中的实体，提交完成前不会触发 Wake。
    /// </summary>
    public Task<CommandRecord> EnqueueAsync(
        EnqueueCommand request,
        Func<ControlDbContext, CommandRecord, CancellationToken, Task>? projection,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(request);
        ValidateTarget(request.TargetKind, request.TargetId);
        var commandName = NormalizeCommand(request.Command);

        return writes.ExecuteAsync(
            async (context, token) =>
            {
                var pending = await context.CommandRecords
                    .Where(command =>
                        command.TargetKind == request.TargetKind &&
                        command.TargetId == request.TargetId &&
                        command.Status == CommandStatus.Pending)
                    .ToListAsync(token)
                    .ConfigureAwait(false);

                IEnumerable<CommandRecord> superseded = [];
                if (request.TargetKind == CommandTargetKind.Display && DisplayReplacementCommands.Contains(commandName))
                {
                    superseded = pending;
                }
                else if (CoalescingCommands.Contains(commandName))
                {
                    superseded = pending.Where(command => command.Command == commandName);
                }

                foreach (var command in superseded)
                {
                    command.Status = CommandStatus.Superseded;
                    command.CompletedAt = _timeProvider.GetUtcNow();
                    command.ResultCode = "superseded_by_newer_intent";
                }

                var lastSequence = await context.CommandRecords
                    .Where(command => command.TargetKind == request.TargetKind && command.TargetId == request.TargetId)
                    .Select(command => (long?)command.TargetSequence)
                    .MaxAsync(token)
                    .ConfigureAwait(false) ?? 0;
                var record = new CommandRecord
                {
                    CommandId = Guid.NewGuid(),
                    TargetKind = request.TargetKind,
                    TargetId = request.TargetId,
                    TargetSequence = checked(lastSequence + 1),
                    Command = commandName,
                    ArgsJson = request.ArgsJson,
                    SchemaVersion = request.SchemaVersion,
                    SourceGeneration = request.SourceGeneration,
                    SourceRevision = request.SourceRevision,
                    Deadline = request.Deadline,
                    CreatedAt = _timeProvider.GetUtcNow(),
                };
                context.CommandRecords.Add(record);
                if (projection is not null)
                {
                    await projection(context, record, token).ConfigureAwait(false);
                }

                return record;
            },
            cancellationToken);
    }

    public Task<CommandRecord?> ClaimAsync(
        ClaimCommand request,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(request);
        ValidateTarget(request.TargetKind, request.TargetId);
        ArgumentOutOfRangeException.ThrowIfLessThanOrEqual(request.LeaseDuration, TimeSpan.Zero);

        return writes.ExecuteAsync(
            async (context, token) =>
            {
                var group = await context.RuntimeGroupControls.SingleAsync(token).ConfigureAwait(false);
                if (group.State != RuntimeGroupState.Armed || group.GroupEpoch != request.GroupEpoch)
                {
                    return null;
                }

                var hasProcessing = await context.CommandRecords.AnyAsync(
                        command =>
                            command.TargetKind == request.TargetKind &&
                            command.TargetId == request.TargetId &&
                            command.Status == CommandStatus.Processing,
                        token)
                    .ConfigureAwait(false);
                if (hasProcessing)
                {
                    return null;
                }

                var command = await context.CommandRecords
                    .Where(candidate =>
                        candidate.TargetKind == request.TargetKind &&
                        candidate.TargetId == request.TargetId &&
                        candidate.Status == CommandStatus.Pending)
                    .OrderBy(candidate => candidate.TargetSequence)
                    .FirstOrDefaultAsync(token)
                    .ConfigureAwait(false);
                if (command is null)
                {
                    return null;
                }

                var now = _timeProvider.GetUtcNow();
                command.Status = CommandStatus.Processing;
                command.ConsumerInstanceId = request.WorkerInstanceId;
                command.OwnerEpoch = request.OwnerEpoch;
                command.ClaimToken = Guid.NewGuid();
                command.LeaseExpiresAt = now.Add(request.LeaseDuration);
                command.AttemptCount++;
                command.StartedAt ??= now;
                return command;
            },
            cancellationToken);
    }

    public Task<bool> RenewLeaseAsync(
        Guid commandId,
        Guid claimToken,
        long ownerEpoch,
        TimeSpan leaseDuration,
        CancellationToken cancellationToken = default)
    {
        ArgumentOutOfRangeException.ThrowIfLessThanOrEqual(leaseDuration, TimeSpan.Zero);

        return writes.ExecuteAsync(
            async (context, token) =>
            {
                var command = await context.CommandRecords.SingleOrDefaultAsync(
                        candidate => candidate.CommandId == commandId,
                        token)
                    .ConfigureAwait(false);
                if (command is null ||
                    command.Status != CommandStatus.Processing ||
                    command.ClaimToken != claimToken ||
                    command.OwnerEpoch != ownerEpoch)
                {
                    return false;
                }

                command.LeaseExpiresAt = _timeProvider.GetUtcNow().Add(leaseDuration);
                return true;
            },
            cancellationToken);
    }

    public Task<CommandResultAcceptance> CompleteAsync(
        CompleteCommand result,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(result);
        if (result.Status is not (CommandStatus.Completed or CommandStatus.Failed or CommandStatus.Uncertain))
        {
            throw new ArgumentOutOfRangeException(nameof(result), "结果状态必须是 completed、failed 或 uncertain。");
        }

        return writes.ExecuteAsync(
            async (context, token) =>
            {
                var command = await context.CommandRecords.SingleOrDefaultAsync(
                        candidate => candidate.CommandId == result.CommandId,
                        token)
                    .ConfigureAwait(false) ?? throw new KeyNotFoundException("命令不存在。");

                if (command.Status is CommandStatus.Completed or CommandStatus.Failed or CommandStatus.Uncertain)
                {
                    if (command.ClaimToken != result.ClaimToken || command.OwnerEpoch != result.OwnerEpoch)
                    {
                        throw new CommandFenceException("重复命令结果的 claim token 或 owner epoch 已失效。");
                    }

                    if (string.Equals(command.ResultHash, result.ResultHash, StringComparison.Ordinal))
                    {
                        return new CommandResultAcceptance(Accepted: true, Duplicate: true);
                    }

                    throw new CommandResultConflictException("同一 command_id 收到了不同结果指纹。");
                }

                if (command.Status != CommandStatus.Processing ||
                    command.ClaimToken != result.ClaimToken ||
                    command.OwnerEpoch != result.OwnerEpoch)
                {
                    throw new CommandFenceException("命令结果的 claim token 或 owner epoch 已失效。");
                }

                command.Status = result.Status;
                command.ResultCode = result.ResultCode;
                command.ResultHash = result.ResultHash;
                command.ResultEvidenceJson = result.ResultEvidenceJson;
                command.CompletedAt = _timeProvider.GetUtcNow();
                command.LeaseExpiresAt = null;
                return new CommandResultAcceptance(Accepted: true, Duplicate: false);
            },
            cancellationToken);
    }

    private static string NormalizeCommand(string command)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(command);
        return command.Trim().ToUpperInvariant();
    }

    private static void ValidateTarget(CommandTargetKind targetKind, int targetId)
    {
        var valid = targetKind switch
        {
            CommandTargetKind.Display => targetId is >= 1 and <= 4,
            CommandTargetKind.Audio => targetId == 1,
            _ => false,
        };
        if (!valid)
        {
            throw new ArgumentOutOfRangeException(nameof(targetId), targetId, "命令目标无效。");
        }
    }
}
