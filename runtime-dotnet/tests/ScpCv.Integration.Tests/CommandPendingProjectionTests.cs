using System.Diagnostics;
using Microsoft.EntityFrameworkCore;
using ScpCv.Domain.Model;
using ScpCv.Infrastructure.Audio;
using ScpCv.Infrastructure.Commands;
using ScpCv.Infrastructure.Playback;
using ScpCv.Infrastructure.Runtime;
using ScpCv.Integration.Tests.Fixtures;

namespace ScpCv.Integration.Tests;

public sealed class CommandPendingProjectionTests
{
    [Fact]
    public async Task CompletingCommandProjectsEarliestRemainingDisplayAndAudioIntent()
    {
        await using var fixture = await ControlHostFixture.CreateAsync();
        var coordinator = new CommandCoordinator(fixture.Commands, new NullCommandWakeNotifier());
        var runtime = new RuntimeStateService(fixture.Database, fixture.Writes, coordinator, fixture.TimeProvider);
        var audio = new BackgroundAudioService(fixture.Database, fixture.Writes, coordinator, fixture.TimeProvider);
        var sourceId = await SeedSourceAsync(fixture);

        await runtime.OpenSourceAsync(1, sourceId, autoplay: true, targetSlide: 0);
        await runtime.NavigateAsync(1, "next", targetIndex: null, positionMs: null);
        await audio.SetVolumeAsync(35);
        await audio.SetMuteAsync(true);

        var startRequest = Guid.NewGuid();
        var group = await fixture.RuntimeAuthority.BeginStartAsync(startRequest);
        await fixture.RuntimeAuthority.ArmAsync(startRequest, group.GroupEpoch);
        var displayOwner = await RegisterAsync(fixture, CommandTargetKind.Display, 1, group.GroupEpoch);
        var audioOwner = await RegisterAsync(fixture, CommandTargetKind.Audio, 1, group.GroupEpoch);
        var leases = new CommandLeaseService(
            fixture.Commands,
            fixture.RuntimeAuthority,
            fixture.Database,
            fixture.Writes,
            fixture.TimeProvider);
        var results = new CommandResultService(fixture.Commands);

        await CompleteFirstAsync(leases, results, displayOwner, group.GroupEpoch);
        await CompleteFirstAsync(leases, results, audioOwner, group.GroupEpoch);

        await using var database = fixture.Database.CreateDbContext();
        var session = await database.PlaybackSessions.SingleAsync(candidate => candidate.WindowId == 1);
        var audioState = await database.BackgroundAudioStates.SingleAsync();
        Assert.Equal("NEXT", session.PendingCommand);
        Assert.Equal("SET_MUTE", audioState.PendingCommand);
    }

    private static async Task<long> SeedSourceAsync(ControlHostFixture fixture)
    {
        await using var database = fixture.Database.CreateDbContext();
        var source = new MediaSource
        {
            SourceType = MediaSourceType.Image,
            Name = "pending-projection",
            Uri = "pending-projection.png",
            IsAvailable = true,
            SourceRevision = 1,
            CreatedAt = fixture.TimeProvider.GetUtcNow(),
        };
        database.MediaSources.Add(source);
        await database.SaveChangesAsync();
        return source.Id;
    }

    private static Task<WorkerOwnership> RegisterAsync(
        ControlHostFixture fixture,
        CommandTargetKind targetKind,
        int targetId,
        long groupEpoch) =>
        fixture.RuntimeAuthority.RegisterWorkerAsync(new RegisterWorker(
            targetKind,
            targetId,
            Guid.NewGuid(),
            Environment.ProcessId,
            fixture.TimeProvider.GetUtcNow(),
            Process.GetCurrentProcess().SessionId,
            groupEpoch,
            "[]",
            PreviousOwnerExitConfirmed: true));

    private static async Task CompleteFirstAsync(
        CommandLeaseService leases,
        CommandResultService results,
        WorkerOwnership owner,
        long groupEpoch)
    {
        var command = await leases.ClaimAsync(new LeaseClaimRequest(
            owner.TargetKind,
            owner.TargetId,
            owner.WorkerInstanceId,
            owner.OwnerEpoch,
            groupEpoch,
            TimeSpan.FromSeconds(30)));
        Assert.NotNull(command);
        await results.AcceptAsync(new CompleteCommand(
            command.CommandId,
            command.ClaimToken!.Value,
            command.OwnerEpoch,
            CommandStatus.Completed,
            "ok",
            string.Empty,
            "{}"));
    }
}
