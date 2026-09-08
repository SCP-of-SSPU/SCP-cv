using ScpCv.Domain.Rules;
using ScpCv.PlayerWorker.Adapters;

namespace ScpCv.PlayerWorker.Playback;

public sealed class SourceSwitchCoordinator(IPlaybackAdapter currentAdapter)
{
    private readonly object _gate = new();
    private long _generation;
    private ResourceKey? _currentKey;

    public async Task<bool> SwitchAsync(
        ResourceKey key,
        long generation,
        IPlaybackAdapter nextAdapter,
        string uri,
        CancellationToken cancellationToken = default)
    {
        lock (_gate)
        {
            if (generation < _generation) return false;
            _generation = generation;
        }

        await nextAdapter.PrepareAsync(key, uri, cancellationToken).ConfigureAwait(false);
        lock (_gate)
        {
            if (generation != _generation) return false;
            _currentKey = key;
        }

        try
        {
            await nextAdapter.OpenAsync(cancellationToken).ConfigureAwait(false);
            await currentAdapter.HideAsync(cancellationToken).ConfigureAwait(false);
            return true;
        }
        catch
        {
            // 新资源失败时保留旧画面可见，避免黑屏；调用方可在下一代重试。
            await nextAdapter.CloseAsync(CancellationToken.None).ConfigureAwait(false);
            return false;
        }
    }

    public ResourceKey? CurrentKey { get { lock (_gate) return _currentKey; } }
}
