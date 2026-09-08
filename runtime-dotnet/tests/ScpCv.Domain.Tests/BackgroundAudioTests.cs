using ScpCv.Domain.Model;
using ScpCv.Domain.Rules;

namespace ScpCv.Domain.Tests;

public sealed class BackgroundAudioTests
{
    [Fact]
    public void NaturalEndAdvancesOnlyForCurrentGeneration()
    {
        var state = new BackgroundAudioState { CurrentSourceId = 2, PlaybackState = PlaybackState.Playing };
        var current = new AudioFinishedEvent(Guid.NewGuid(), 2, 7);
        var stale = new AudioFinishedEvent(Guid.NewGuid(), 2, 6);

        Assert.True(AudioPlaybackPolicy.ShouldAdvance(state, current, 7));
        Assert.False(AudioPlaybackPolicy.ShouldAdvance(state, stale, 7));
    }

    [Fact]
    public void FinishedEventIsIdempotent()
    {
        var eventId = Guid.NewGuid();
        Assert.True(AudioPlaybackPolicy.TryAcceptFinished(eventId, new HashSet<Guid>()));
        var seen = new HashSet<Guid> { eventId };
        Assert.False(AudioPlaybackPolicy.TryAcceptFinished(eventId, seen));
    }
}
