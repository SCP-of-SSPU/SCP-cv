using Microsoft.EntityFrameworkCore;
using ScpCv.Domain.Model;
using ScpCv.Infrastructure.Commands;
using ScpCv.Integration.Tests.Fixtures;

namespace ScpCv.Integration.Tests;

public sealed class CommandCoordinatorTests
{
    [Fact]
    public async Task DurableCommandAndCompatibilityProjectionCommitBeforeWake()
    {
        await using var fixture = await ControlHostFixture.CreateAsync();
        var wake = new QueuedCommandWakeNotifier();
        var coordinator = new CommandCoordinator(fixture.Commands, wake);

        var record = await coordinator.EnqueueAsync(
            new EnqueueCommand(CommandTargetKind.Display, 1, "OPEN", "{\"source_id\":9}", 4, 2),
            async (database, command, token) =>
            {
                var session = await database.PlaybackSessions.SingleAsync(item => item.WindowId == 1, token);
                session.PendingCommand = command.Command;
                session.CommandArgsJson = command.ArgsJson;
            });

        var signal = await ReadOneAsync(wake);
        Assert.Equal(record.TargetSequence, signal.HighestSequence);
        await using var context = fixture.Database.CreateDbContext();
        var persisted = await context.PlaybackSessions.SingleAsync(item => item.WindowId == 1);
        Assert.Equal("OPEN", persisted.PendingCommand);
        Assert.Equal(record.CommandId, await context.CommandRecords.Select(item => item.CommandId).SingleAsync());
    }

    [Fact]
    public async Task ProjectionFailureRollsBackCommandAndDoesNotWakeWorker()
    {
        await using var fixture = await ControlHostFixture.CreateAsync();
        var wake = new QueuedCommandWakeNotifier();
        var coordinator = new CommandCoordinator(fixture.Commands, wake);

        await Assert.ThrowsAsync<InvalidOperationException>(() => coordinator.EnqueueAsync(
            new EnqueueCommand(CommandTargetKind.Display, 1, "PLAY", "{}", 1, 1),
            (_, _, _) => throw new InvalidOperationException("projection failed")));

        await using var context = fixture.Database.CreateDbContext();
        Assert.Equal(0, await context.CommandRecords.CountAsync());
        using var timeout = new CancellationTokenSource(TimeSpan.FromMilliseconds(100));
        await Assert.ThrowsAnyAsync<OperationCanceledException>(async () => await wake.ReadAllAsync(timeout.Token).FirstAsync(timeout.Token));
    }

    private static async Task<CommandWakeSignal> ReadOneAsync(QueuedCommandWakeNotifier wake)
    {
        await foreach (var signal in wake.ReadAllAsync())
        {
            return signal;
        }

        throw new InvalidOperationException("Wake queue unexpectedly completed.");
    }
}
