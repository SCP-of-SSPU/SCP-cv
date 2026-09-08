using ScpCv.Domain.Rules;
using ScpCv.PlayerWorker.Adapters;

namespace ScpCv.PlayerWorker.Resources;

public sealed class WarmResource(ResourceKey key, IPlaybackAdapter adapter)
{
    public ResourceKey Key { get; } = key;
    public IPlaybackAdapter Adapter { get; } = adapter;
    public PlaybackResourceState State => Adapter.State;
    public DateTimeOffset LastUsedAt { get; private set; } = DateTimeOffset.UtcNow;

    public void Touch() => LastUsedAt = DateTimeOffset.UtcNow;
}
