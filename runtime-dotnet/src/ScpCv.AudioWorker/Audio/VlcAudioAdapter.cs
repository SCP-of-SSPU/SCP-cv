using LibVLCSharp.Shared;

namespace ScpCv.AudioWorker.Audio;

/// <summary>AudioWorker 的单实例 LibVLC 播放器，结束事件携带 source_generation。</summary>
public sealed class VlcAudioAdapter : IAsyncDisposable
{
    private readonly LibVLC _libVlc = new();
    private readonly MediaPlayer _player;
    private Media? _media;
    private long _generation;
    private int _disposed;

    public VlcAudioAdapter()
    {
        Core.Initialize();
        _player = new MediaPlayer(_libVlc);
        _player.EndReached += (_, _) =>
        {
            if (LoopEnabled && _media is not null) _ = _player.Play(_media);
            else Finished?.Invoke(this, new AudioFinishedEventArgs(SourceId, _generation));
        };
    }

    public long SourceId { get; private set; }
    public long Generation => Volatile.Read(ref _generation);
    public int Volume { get => _player.Volume; set => _player.Volume = Math.Clamp(value, 0, 100); }
    public bool LoopEnabled { get; set; }
    public event EventHandler<AudioFinishedEventArgs>? Finished;

    public Task OpenAsync(long sourceId, string uri, long generation, CancellationToken cancellationToken = default)
    {
        ObjectDisposedException.ThrowIf(Volatile.Read(ref _disposed) != 0, this);
        _media?.Dispose();
        _media = new Media(_libVlc, uri, FromType.FromLocation);
        SourceId = sourceId;
        Interlocked.Exchange(ref _generation, generation);
        return Task.CompletedTask;
    }

    public Task PlayAsync(CancellationToken cancellationToken = default) { if (_media is not null) _ = _player.Play(_media); return Task.CompletedTask; }
    public Task PauseAsync(CancellationToken cancellationToken = default) { _player.Pause(); return Task.CompletedTask; }
    public Task StopAsync(CancellationToken cancellationToken = default) { _player.Stop(); return Task.CompletedTask; }
    public Task SeekAsync(long positionMs, CancellationToken cancellationToken = default) { _player.Time = Math.Max(0, positionMs); return Task.CompletedTask; }

    public ValueTask DisposeAsync()
    {
        if (Interlocked.Exchange(ref _disposed, 1) == 0)
        {
            _player.Stop();
            _media?.Dispose();
            _player.Dispose();
            _libVlc.Dispose();
        }
        GC.SuppressFinalize(this);
        return ValueTask.CompletedTask;
    }
}

public sealed class AudioFinishedEventArgs(long sourceId, long sourceGeneration) : EventArgs
{
    public long SourceId { get; } = sourceId;
    public long SourceGeneration { get; } = sourceGeneration;
}
