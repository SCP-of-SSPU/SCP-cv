using System.Diagnostics;
using Microsoft.EntityFrameworkCore;
using ScpCv.Contracts.Ipc;
using ScpCv.ControlHost.Events;
using ScpCv.Domain.Model;
using ScpCv.Infrastructure.Audio;
using ScpCv.Infrastructure.Commands;
using ScpCv.Infrastructure.Playback;
using ScpCv.Infrastructure.Runtime;
using ScpCv.Integration.Tests.Fixtures;

namespace ScpCv.Integration.Tests;

public sealed class RuntimeProjectionTests
{
    [Fact]
    public async Task AudioStateReportCannotOverwriteNewerSourceGeneration()
    {
        await using var fixture = await ControlHostFixture.CreateAsync();
        var startRequest = Guid.NewGuid();
        var group = await fixture.RuntimeAuthority.BeginStartAsync(startRequest);
        await fixture.RuntimeAuthority.ArmAsync(startRequest, group.GroupEpoch);
        using var process = Process.GetCurrentProcess();
        var worker = Guid.NewGuid();
        var ownership = await fixture.RuntimeAuthority.RegisterWorkerAsync(new RegisterWorker(
            CommandTargetKind.Audio,
            1,
            worker,
            process.Id,
            new DateTimeOffset(process.StartTime.ToUniversalTime(), TimeSpan.Zero),
            process.SessionId,
            group.GroupEpoch,
            "[\"libvlc\"]",
            PreviousOwnerExitConfirmed: true));

        await fixture.Writes.ExecuteAsync(async (database, cancellationToken) =>
        {
            var state = await database.BackgroundAudioStates.SingleAsync(cancellationToken);
            state.DesiredGeneration = 2;
            state.ObservedGeneration = 0;
            state.PlaybackState = PlaybackState.Loading;
        });
        var runtime = new RuntimeStateService(
            fixture.Database,
            fixture.Writes,
            new CommandCoordinator(fixture.Commands, new NullCommandWakeNotifier()),
            fixture.TimeProvider);
        var audio = new BackgroundAudioService(
            fixture.Database,
            fixture.Writes,
            new CommandCoordinator(fixture.Commands, new NullCommandWakeNotifier()),
            fixture.TimeProvider);
        var publisher = new RuntimeProjectionPublisher(
            fixture.Writes,
            new SseEventHub(runtime, audio, new SseEventStreamOptions()),
            fixture.TimeProvider);

        var stale = await publisher.ApplyStateReportAsync(
            CommandTargetKind.Audio,
            1,
            worker,
            ownership.OwnerEpoch,
            new StateReportDto
            {
                SourceGeneration = 1,
                State = System.Text.Json.JsonSerializer.SerializeToElement(new { playback_state = "playing" }),
            });
        Assert.False(stale.Accepted);
        Assert.Equal("stale_generation", stale.Reason);

        await using (var check = fixture.Database.CreateDbContext())
        {
            Assert.Equal(PlaybackState.Loading, (await check.BackgroundAudioStates.SingleAsync()).PlaybackState);
        }

        var current = await publisher.ApplyStateReportAsync(
            CommandTargetKind.Audio,
            1,
            worker,
            ownership.OwnerEpoch,
            new StateReportDto
            {
                SourceGeneration = 2,
                State = System.Text.Json.JsonSerializer.SerializeToElement(new { playback_state = "playing" }),
            });
        Assert.True(current.Accepted);
        await using var final = fixture.Database.CreateDbContext();
        var stateAfter = await final.BackgroundAudioStates.SingleAsync();
        Assert.Equal(PlaybackState.Playing, stateAfter.PlaybackState);
        Assert.Equal(2, stateAfter.ObservedGeneration);
    }
}
