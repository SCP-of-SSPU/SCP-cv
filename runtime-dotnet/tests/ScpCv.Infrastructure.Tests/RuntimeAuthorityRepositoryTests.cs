using Microsoft.Data.Sqlite;
using ScpCv.Domain.Model;
using ScpCv.Infrastructure.Configuration;
using ScpCv.Infrastructure.Persistence;
using ScpCv.Infrastructure.Runtime;

namespace ScpCv.Infrastructure.Tests;

public sealed class RuntimeAuthorityRepositoryTests
{
    [Fact]
    public async Task GroupLatchRequiresExplicitStartAndFencesOnDrain()
    {
        var root = CreateTemporaryRoot();
        try
        {
            var factory = await CreateInitializedFactoryAsync(root);
            using var writes = new WriteCoordinator(factory);
            var repository = new RuntimeAuthorityRepository(factory, writes);
            var requestId = Guid.NewGuid();

            var starting = await repository.BeginStartAsync(requestId);
            Assert.Equal(RuntimeGroupState.Starting, starting.State);
            await Assert.ThrowsAsync<RuntimeAuthorityException>(() =>
                repository.ArmAsync(Guid.NewGuid(), starting.GroupEpoch));

            var armed = await repository.ArmAsync(requestId, starting.GroupEpoch);
            Assert.Equal(RuntimeGroupState.Armed, armed.State);
            var draining = await repository.BeginDrainAsync("player exited");
            Assert.Equal(RuntimeGroupState.Draining, draining.State);
            Assert.Equal(armed.GroupEpoch + 1, draining.GroupEpoch);
            var stopped = await repository.CompleteStopAsync(draining.GroupEpoch);
            Assert.Equal(RuntimeGroupState.Stopped, stopped.State);

            var persisted = await repository.GetGroupAsync();
            Assert.Equal(RuntimeGroupState.Stopped, persisted.State);
            Assert.Null(persisted.ExplicitStartRequestId);
        }
        finally
        {
            DeleteTemporaryRoot(root);
        }
    }

    [Fact]
    public async Task WorkerOwnershipOnlyTransfersAfterConfirmedExit()
    {
        var root = CreateTemporaryRoot();
        try
        {
            var factory = await CreateInitializedFactoryAsync(root);
            using var writes = new WriteCoordinator(factory);
            var repository = new RuntimeAuthorityRepository(factory, writes);
            var startId = Guid.NewGuid();
            var starting = await repository.BeginStartAsync(startId);
            await repository.ArmAsync(startId, starting.GroupEpoch);
            var processStart = DateTimeOffset.UtcNow;
            var firstRequest = new RegisterWorker(
                CommandTargetKind.Display,
                1,
                Guid.NewGuid(),
                ProcessId: 101,
                processStart,
                LogonSessionId: 3,
                starting.GroupEpoch,
                "[\"video\"]");

            var first = await repository.RegisterWorkerAsync(firstRequest);
            var same = await repository.RegisterWorkerAsync(firstRequest);
            Assert.Equal(first.OwnerEpoch, same.OwnerEpoch);
            var replacementRequest = firstRequest with
            {
                WorkerInstanceId = Guid.NewGuid(),
                ProcessId = 202,
                ProcessStartTime = processStart.AddSeconds(1),
            };
            await Assert.ThrowsAsync<RuntimeAuthorityException>(() =>
                repository.RegisterWorkerAsync(replacementRequest));

            var replacement = await repository.RegisterWorkerAsync(
                replacementRequest with { PreviousOwnerExitConfirmed = true });

            Assert.Equal(first.OwnerEpoch + 1, replacement.OwnerEpoch);
            Assert.False(await repository.RecordHeartbeatAsync(
                CommandTargetKind.Display,
                1,
                first.WorkerInstanceId,
                first.OwnerEpoch,
                uiProgress: true));
            Assert.True(await repository.RecordHeartbeatAsync(
                CommandTargetKind.Display,
                1,
                replacement.WorkerInstanceId,
                replacement.OwnerEpoch,
                uiProgress: true));
        }
        finally
        {
            DeleteTemporaryRoot(root);
        }
    }

    [Fact]
    public async Task OfficeOperationKeepsStableIdentityAndDeduplicatesResult()
    {
        var root = CreateTemporaryRoot();
        try
        {
            var factory = await CreateInitializedFactoryAsync(root);
            using var writes = new WriteCoordinator(factory);
            var repository = new RuntimeAuthorityRepository(factory, writes);
            var startId = Guid.NewGuid();
            var starting = await repository.BeginStartAsync(startId);
            await repository.ArmAsync(startId, starting.GroupEpoch);
            var request = new RegisterOfficeOperation(
                Guid.NewGuid(),
                ParentCommandId: Guid.NewGuid(),
                ParentJobId: null,
                ClaimToken: Guid.NewGuid(),
                SourceGeneration: 9,
                starting.GroupEpoch,
                HostEpoch: 4,
                SlotEpoch: 6,
                DateTimeOffset.UtcNow.AddMinutes(1),
                "{\"operation\":\"next\"}");

            var registered = await repository.RegisterOfficeOperationAsync(request);
            var duplicateRegistration = await repository.RegisterOfficeOperationAsync(request);
            Assert.Equal(registered.Id, duplicateRegistration.Id);
            await Assert.ThrowsAsync<OfficeOperationConflictException>(() =>
                repository.RegisterOfficeOperationAsync(request with { RequestJson = "{\"operation\":\"previous\"}" }));

            var completion = new CompleteOfficeOperation(
                request.OperationId,
                request.HostEpoch,
                request.SlotEpoch,
                OperationStatus.Succeeded,
                "sha256:result",
                string.Empty);
            Assert.False((await repository.CompleteOfficeOperationAsync(completion)).Duplicate);
            Assert.True((await repository.CompleteOfficeOperationAsync(completion)).Duplicate);
            await Assert.ThrowsAsync<OfficeOperationConflictException>(() =>
                repository.CompleteOfficeOperationAsync(completion with { ResultFingerprint = "sha256:different" }));
        }
        finally
        {
            DeleteTemporaryRoot(root);
        }
    }

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
}
