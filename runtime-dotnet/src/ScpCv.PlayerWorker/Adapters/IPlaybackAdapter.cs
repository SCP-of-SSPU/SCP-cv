using ScpCv.Domain.Rules;

namespace ScpCv.PlayerWorker.Adapters;

public enum PlaybackResourceState { Empty, Preparing, Ready, Visible, Hidden, Faulted, Closing }

public interface IPlaybackAdapter : IAsyncDisposable
{
    string Kind { get; }
    PlaybackResourceState State { get; }
    Task PrepareAsync(ResourceKey key, string uri, CancellationToken cancellationToken = default);
    Task OpenAsync(CancellationToken cancellationToken = default);
    Task ControlAsync(string action, CancellationToken cancellationToken = default);
    Task HideAsync(CancellationToken cancellationToken = default);
    Task CloseAsync(CancellationToken cancellationToken = default);
    object Observe();
}
