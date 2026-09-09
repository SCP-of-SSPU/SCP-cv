using Microsoft.EntityFrameworkCore;
using ScpCv.Domain.Model;
using ScpCv.Domain.Rules;
using ScpCv.Infrastructure.Audio;
using ScpCv.Infrastructure.Commands;
using ScpCv.Integration.Tests.Fixtures;

namespace ScpCv.Integration.Tests;

public sealed class BackgroundAudioPersistenceTests
{
    [Fact]
    public async Task GenerationAndFinishedEventDeduplicationSurviveServiceRestart()
    {
        await using var fixture = await ControlHostFixture.CreateAsync();
        var (firstSourceId, secondSourceId) = await SeedAudioSourcesAsync(fixture);
        var coordinator = new CommandCoordinator(fixture.Commands, new NullCommandWakeNotifier());

        var firstService = new BackgroundAudioService(
            fixture.Database,
            fixture.Writes,
            coordinator,
            fixture.TimeProvider);
        await firstService.SetPlaylistAsync([firstSourceId, secondSourceId]);
        await firstService.PlaySourceAsync(firstSourceId);
        await MarkAudioPlayingAsync(fixture);

        var eventId = Guid.NewGuid();
        var restartedService = new BackgroundAudioService(
            fixture.Database,
            fixture.Writes,
            coordinator,
            fixture.TimeProvider);
        var advanced = await restartedService.HandleFinishedAsync(
            new AudioFinishedEvent(eventId, firstSourceId, 1));
        Assert.Equal(secondSourceId, advanced.State.SourceId);

        var restartedAgain = new BackgroundAudioService(
            fixture.Database,
            fixture.Writes,
            coordinator,
            fixture.TimeProvider);
        await restartedAgain.HandleFinishedAsync(new AudioFinishedEvent(eventId, firstSourceId, 1));
        await restartedAgain.PlaySourceAsync(firstSourceId);

        await using var database = fixture.Database.CreateDbContext();
        var opens = await database.CommandRecords
            .Where(item => item.TargetKind == CommandTargetKind.Audio && item.Command == "OPEN")
            .OrderBy(item => item.TargetSequence)
            .ToArrayAsync();
        Assert.Equal([1L, 2L, 3L], opens.Select(item => item.SourceGeneration));
        Assert.Single(opens, item => item.TriggerEventId == eventId);
    }

    private static async Task<(long First, long Second)> SeedAudioSourcesAsync(ControlHostFixture fixture)
    {
        await using var database = fixture.Database.CreateDbContext();
        var first = Audio("first", fixture.TimeProvider.GetUtcNow());
        var second = Audio("second", fixture.TimeProvider.GetUtcNow());
        database.MediaSources.AddRange(first, second);
        await database.SaveChangesAsync();
        return (first.Id, second.Id);
    }

    private static MediaSource Audio(string name, DateTimeOffset createdAt) => new()
    {
        SourceType = MediaSourceType.Audio,
        Name = name,
        Uri = $"{name}.mp3",
        IsAvailable = true,
        SourceRevision = 1,
        CreatedAt = createdAt,
    };

    private static async Task MarkAudioPlayingAsync(ControlHostFixture fixture)
    {
        await fixture.Writes.ExecuteAsync(async (database, cancellationToken) =>
        {
            var state = await database.BackgroundAudioStates.SingleAsync(cancellationToken);
            state.PlaybackState = PlaybackState.Playing;
        });
    }
}
