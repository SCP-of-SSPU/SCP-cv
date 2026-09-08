using ScpCv.Contracts.Http;
using ScpCv.Domain.Rules;
using ScpCv.Infrastructure.Audio;

namespace ScpCv.ControlHost.Ipc;

public sealed class AudioFinishedEventProcessor(BackgroundAudioService audio)
{
    public Task<BackgroundAudioDto> HandleFinishedAsync(
        Guid eventId,
        long sourceId,
        long sourceGeneration,
        CancellationToken cancellationToken = default) =>
        audio.HandleFinishedAsync(new AudioFinishedEvent(eventId, sourceId, sourceGeneration), cancellationToken);
}
