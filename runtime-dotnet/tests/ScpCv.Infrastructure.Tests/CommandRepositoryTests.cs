using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using ScpCv.Domain.Model;
using ScpCv.Infrastructure.Commands;
using ScpCv.Infrastructure.Configuration;
using ScpCv.Infrastructure.Persistence;

namespace ScpCv.Infrastructure.Tests;

public sealed class CommandRepositoryTests
{
    [Fact]
    public async Task WriteCoordinatorSerializesConcurrentTransactions()
    {
        var root = CreateTemporaryRoot();
        try
        {
            var factory = await CreateInitializedFactoryAsync(root);
            using var writes = new WriteCoordinator(factory);
            var active = 0;
            var maximumActive = 0;
            var tasks = Enumerable.Range(1, 12).Select(index => writes.ExecuteAsync(
                async (context, token) =>
                {
                    var current = Interlocked.Increment(ref active);
                    InterlockedExtensions.Max(ref maximumActive, current);
                    await Task.Delay(5, token);
                    context.UserAccounts.Add(new UserAccount
                    {
                        Username = $"writer-{index}",
                        PasswordHash = "hash",
                    });
                    Interlocked.Decrement(ref active);
                }));

            await Task.WhenAll(tasks);

            Assert.Equal(1, maximumActive);
            await using var verification = factory.CreateDbContext();
            Assert.Equal(12, await verification.UserAccounts.CountAsync());
        }
        finally
        {
            DeleteTemporaryRoot(root);
        }
    }

    [Fact]
    public async Task EnqueueAllocatesSequenceAndOnlyMergesPendingIntent()
    {
        var root = CreateTemporaryRoot();
        try
        {
            var factory = await CreateInitializedFactoryAsync(root);
            using var writes = new WriteCoordinator(factory);
            var repository = new CommandRepository(writes);

            var first = await repository.EnqueueAsync(NewCommand(CommandTargetKind.Display, 1, "SET_VOLUME"));
            var second = await repository.EnqueueAsync(NewCommand(CommandTargetKind.Display, 1, "SET_VOLUME"));
            var relative = await repository.EnqueueAsync(NewCommand(CommandTargetKind.Display, 1, "NEXT"));
            var replacement = await repository.EnqueueAsync(NewCommand(CommandTargetKind.Display, 1, "OPEN"));

            Assert.Equal(1, first.TargetSequence);
            Assert.Equal(2, second.TargetSequence);
            Assert.Equal(3, relative.TargetSequence);
            Assert.Equal(4, replacement.TargetSequence);
            await using var context = factory.CreateDbContext();
            var records = await context.CommandRecords.OrderBy(command => command.TargetSequence).ToListAsync();
            Assert.Equal(
                [CommandStatus.Superseded, CommandStatus.Superseded, CommandStatus.Superseded, CommandStatus.Pending],
                records.Select(command => command.Status));
        }
        finally
        {
            DeleteTemporaryRoot(root);
        }
    }

    [Fact]
    public async Task AudioOpenDoesNotClearEarlierPendingCommands()
    {
        var root = CreateTemporaryRoot();
        try
        {
            var factory = await CreateInitializedFactoryAsync(root);
            using var writes = new WriteCoordinator(factory);
            var repository = new CommandRepository(writes);

            await repository.EnqueueAsync(NewCommand(CommandTargetKind.Audio, 1, "NEXT"));
            await repository.EnqueueAsync(NewCommand(CommandTargetKind.Audio, 1, "OPEN"));

            await using var context = factory.CreateDbContext();
            Assert.Equal(2, await context.CommandRecords.CountAsync(command => command.Status == CommandStatus.Pending));
        }
        finally
        {
            DeleteTemporaryRoot(root);
        }
    }

    [Fact]
    public async Task ClaimRequiresArmedMatchingGroupAndAllowsOneProcessingCommand()
    {
        var root = CreateTemporaryRoot();
        try
        {
            var factory = await CreateInitializedFactoryAsync(root);
            using var writes = new WriteCoordinator(factory);
            var repository = new CommandRepository(writes);
            await repository.EnqueueAsync(NewCommand(CommandTargetKind.Display, 1, "PLAY"));
            var claim = NewClaim(groupEpoch: 4);

            Assert.Null(await repository.ClaimAsync(claim));
            await ArmGroupAsync(writes, groupEpoch: 4);
            Assert.Null(await repository.ClaimAsync(claim with { GroupEpoch = 3 }));

            var leased = await repository.ClaimAsync(claim);

            Assert.NotNull(leased);
            Assert.NotEqual(Guid.Empty, leased.ClaimToken);
            Assert.Equal(CommandStatus.Processing, leased.Status);
            Assert.Null(await repository.ClaimAsync(claim));
        }
        finally
        {
            DeleteTemporaryRoot(root);
        }
    }

    [Fact]
    public async Task CompletionIsIdempotentForSameFencedResultAndRejectsConflicts()
    {
        var root = CreateTemporaryRoot();
        try
        {
            var factory = await CreateInitializedFactoryAsync(root);
            using var writes = new WriteCoordinator(factory);
            var repository = new CommandRepository(writes);
            await ArmGroupAsync(writes, groupEpoch: 2);
            await repository.EnqueueAsync(NewCommand(CommandTargetKind.Display, 1, "PLAY"));
            var leased = await repository.ClaimAsync(NewClaim(groupEpoch: 2));
            Assert.NotNull(leased);
            var result = new CompleteCommand(
                leased.CommandId,
                leased.ClaimToken!.Value,
                leased.OwnerEpoch,
                CommandStatus.Completed,
                "ok",
                "sha256:same",
                "{\"visible\":true}");

            Assert.False((await repository.CompleteAsync(result)).Duplicate);
            Assert.True((await repository.CompleteAsync(result)).Duplicate);
            await Assert.ThrowsAsync<CommandFenceException>(() =>
                repository.CompleteAsync(result with { ClaimToken = Guid.NewGuid() }));
            await Assert.ThrowsAsync<CommandResultConflictException>(() =>
                repository.CompleteAsync(result with { ResultHash = "sha256:different" }));
        }
        finally
        {
            DeleteTemporaryRoot(root);
        }
    }

    private static EnqueueCommand NewCommand(CommandTargetKind kind, int id, string command) =>
        new(kind, id, command, "{}", SourceGeneration: 1, SourceRevision: 1);

    private static ClaimCommand NewClaim(long groupEpoch) =>
        new(CommandTargetKind.Display, 1, Guid.NewGuid(), OwnerEpoch: 7, groupEpoch, TimeSpan.FromSeconds(30));

    private static Task ArmGroupAsync(WriteCoordinator writes, long groupEpoch) =>
        writes.ExecuteAsync(
            async (context, token) =>
            {
                var group = await context.RuntimeGroupControls.SingleAsync(token);
                group.State = RuntimeGroupState.Armed;
                group.GroupEpoch = groupEpoch;
            });

    private static async Task<ControlDbContextFactory> CreateInitializedFactoryAsync(string root)
    {
        var factory = new ControlDbContextFactory(new DataRootOptions { RootPath = root }, root);
        await new DatabaseInitializer(factory).InitializeAsync();
        return factory;
    }

    private static string CreateTemporaryRoot() =>
        Path.Combine(Path.GetTempPath(), "scp-cv-tests", Guid.NewGuid().ToString("N"));

    private static void DeleteTemporaryRoot(string root)
    {
        SqliteConnection.ClearAllPools();
        if (Directory.Exists(root))
        {
            Directory.Delete(root, recursive: true);
        }
    }

    private static class InterlockedExtensions
    {
        public static void Max(ref int location, int value)
        {
            var current = Volatile.Read(ref location);
            while (value > current)
            {
                var observed = Interlocked.CompareExchange(ref location, value, current);
                if (observed == current)
                {
                    return;
                }

                current = observed;
            }
        }
    }
}
