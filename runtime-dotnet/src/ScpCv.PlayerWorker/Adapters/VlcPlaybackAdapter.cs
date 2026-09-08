namespace ScpCv.PlayerWorker.Adapters;

public interface IVlcMediaSession : IAsyncDisposable
{
    long PositionMs { get; }
    int Volume { get; }
    bool LoopEnabled { get; }
    Task PlayAsync(CancellationToken cancellationToken);
    Task PauseAsync(CancellationToken cancellationToken);
    Task StopAsync(CancellationToken cancellationToken);
    Task SeekAsync(long positionMs, CancellationToken cancellationToken);
    Task SetVolumeAsync(int volume, CancellationToken cancellationToken);
    Task SetLoopAsync(bool enabled, CancellationToken cancellationToken);
    event EventHandler? Ended;
}

/// <summary>LibVLC 生命周期适配边界；原生对象只在单个 PlayerWorker 内使用。</summary>
public sealed class VlcPlaybackAdapter(Func<Uri, Task<IVlcMediaSession>> sessionFactory)
{
    private IVlcMediaSession? _session;
    private Uri? _uri;

    public event EventHandler? Ended;
    public bool IsOpen => _session is not null;
    public long PositionMs => _session?.PositionMs ?? 0;
    public int Volume => _session?.Volume ?? 100;
    public bool LoopEnabled => _session?.LoopEnabled ?? false;

    public async Task OpenAsync(string uri, CancellationToken cancellationToken = default)
    {
        if (!Uri.TryCreate(uri, UriKind.Absolute, out var parsed) || parsed.Scheme is not ("file" or "http" or "https" or "rtsp" or "srt"))
            throw new ArgumentException("仅支持 file/http/https/rtsp/srt 媒体 URI。", nameof(uri));
        await CloseAsync(cancellationToken).ConfigureAwait(false);
        _session = await sessionFactory(parsed).ConfigureAwait(false);
        _uri = parsed;
        _session.Ended += OnEnded;
    }

    public Task PlayAsync(CancellationToken cancellationToken = default) => RequireSession().PlayAsync(cancellationToken);
    public Task PauseAsync(CancellationToken cancellationToken = default) => RequireSession().PauseAsync(cancellationToken);
    public Task StopAsync(CancellationToken cancellationToken = default) => RequireSession().StopAsync(cancellationToken);
    public Task SeekAsync(long positionMs, CancellationToken cancellationToken = default) =>
        positionMs < 0 ? throw new ArgumentOutOfRangeException(nameof(positionMs)) : RequireSession().SeekAsync(positionMs, cancellationToken);
    public Task SetVolumeAsync(int volume, CancellationToken cancellationToken = default) =>
        volume is < 0 or > 100 ? throw new ArgumentOutOfRangeException(nameof(volume)) : RequireSession().SetVolumeAsync(volume, cancellationToken);
    public Task SetLoopAsync(bool enabled, CancellationToken cancellationToken = default) => RequireSession().SetLoopAsync(enabled, cancellationToken);

    public async Task CloseAsync(CancellationToken cancellationToken = default)
    {
        if (_session is null) return;
        _session.Ended -= OnEnded;
        await _session.StopAsync(cancellationToken).ConfigureAwait(false);
        await _session.DisposeAsync().ConfigureAwait(false);
        _session = null;
        _uri = null;
    }

    private IVlcMediaSession RequireSession() => _session ?? throw new InvalidOperationException("尚未打开 VLC 媒体。");
    private void OnEnded(object? sender, EventArgs args) => Ended?.Invoke(this, args);
}
