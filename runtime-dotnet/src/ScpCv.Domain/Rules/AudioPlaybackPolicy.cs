using ScpCv.Domain.Model;

namespace ScpCv.Domain.Rules;

public sealed record AudioFinishedEvent(Guid EventId, long SourceId, long SourceGeneration);

public static class AudioPlaybackPolicy
{
    public static bool ShouldAdvance(BackgroundAudioState state, AudioFinishedEvent finished, long currentGeneration) =>
        state.PlaybackState == PlaybackState.Playing && state.CurrentSourceId == finished.SourceId && finished.SourceGeneration == currentGeneration;

    public static bool TryAcceptFinished(Guid eventId, ISet<Guid> seen) => seen.Add(eventId);
}
