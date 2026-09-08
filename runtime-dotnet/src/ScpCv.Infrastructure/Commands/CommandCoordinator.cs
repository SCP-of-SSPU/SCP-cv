using ScpCv.Domain.Model;
using ScpCv.Infrastructure.Persistence;

namespace ScpCv.Infrastructure.Commands;

public sealed record CommandWakeSignal(
    CommandTargetKind TargetKind,
    int TargetId,
    long HighestSequence);

public interface ICommandWakeNotifier
{
    ValueTask WakeAsync(CommandWakeSignal signal, CancellationToken cancellationToken = default);
}

public sealed class NullCommandWakeNotifier : ICommandWakeNotifier
{
    public ValueTask WakeAsync(CommandWakeSignal signal, CancellationToken cancellationToken = default)
    {
        _ = signal;
        _ = cancellationToken;
        return ValueTask.CompletedTask;
    }
}

/// <summary>开发期本机唤醒队列；Supervisor/Named Pipe 层可消费而不影响 durable command。</summary>
public sealed class QueuedCommandWakeNotifier : ICommandWakeNotifier
{
    private readonly System.Threading.Channels.Channel<CommandWakeSignal> _signals =
        System.Threading.Channels.Channel.CreateUnbounded<CommandWakeSignal>();

    public ValueTask WakeAsync(CommandWakeSignal signal, CancellationToken cancellationToken = default) =>
        _signals.Writer.WriteAsync(signal, cancellationToken);

    public IAsyncEnumerable<CommandWakeSignal> ReadAllAsync(CancellationToken cancellationToken = default) =>
        _signals.Reader.ReadAllAsync(cancellationToken);
}

/// <summary>把命令持久化、兼容投影和提交后唤醒固定为一个入口。</summary>
public sealed class CommandCoordinator(
    CommandRepository repository,
    ICommandWakeNotifier wakeNotifier)
{
    public async Task<CommandRecord> EnqueueAsync(
        EnqueueCommand request,
        Func<ControlDbContext, CommandRecord, CancellationToken, Task>? projection = null,
        CancellationToken cancellationToken = default)
    {
        var record = await repository.EnqueueAsync(request, projection, cancellationToken).ConfigureAwait(false);

        // CommandRepository 已完成事务提交；Wake 失败只代表需要补偿 Claim，不能撤销已入库命令。
        await wakeNotifier.WakeAsync(
                new CommandWakeSignal(record.TargetKind, record.TargetId, record.TargetSequence),
                cancellationToken)
            .ConfigureAwait(false);
        return record;
    }
}
