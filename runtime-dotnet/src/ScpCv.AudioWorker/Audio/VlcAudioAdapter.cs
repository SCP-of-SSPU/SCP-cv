using LibVLCSharp.Shared;

namespace ScpCv.AudioWorker.Audio;

/// <summary>AudioWorker 的单实例 LibVLC 播放器，结束事件携带 source_generation。</summary>
public sealed class VlcAudioAdapter : IAudioPlaybackAdapter, IAsyncDisposable
{
    private readonly LibVLC _libVlc = new();
    private readonly MediaPlayer _player;
    private readonly AudioFinishedEventTracker _finishedEvents = new();
    private Media? _media;
    private long _generation;
    private int _disposed;

    public VlcAudioAdapter()
    {
        Core.Initialize();
        _player = new MediaPlayer(_libVlc);
        _player.EndReached += OnEndReached;
    }

    public long SourceId { get; private set; }
    public long Generation => Volatile.Read(ref _generation);
    public int Volume { get => _player.Volume; set => _player.Volume = Math.Clamp(value, 0, 100); }
    public bool LoopEnabled { get; set; }
    public bool IsMuted { get => _player.Mute; set => _player.Mute = value; }
    public long PositionMs => Math.Max(0, _player.Time);
    public long DurationMs => Math.Max(0, _player.Length);
    public string PlaybackState => _player.State switch
    {
        VLCState.Playing => "playing",
        VLCState.Paused => "paused",
        VLCState.Stopped or VLCState.Ended => "stopped",
        VLCState.Error => "error",
        _ => "loading",
    };
    public event EventHandler<AudioFinishedEventArgs>? Finished;

    public Task OpenAsync(long sourceId, string uri, long generation, CancellationToken cancellationToken = default)
    {
        ObjectDisposedException.ThrowIf(Volatile.Read(ref _disposed) != 0, this);
        _media?.Dispose();
        var localPath = uri.StartsWith("file://", StringComparison.OrdinalIgnoreCase) ? new Uri(uri).LocalPath : uri;
        _media = File.Exists(localPath)
            ? new Media(_libVlc, Path.GetFullPath(localPath), FromType.FromPath)
            : new Media(_libVlc, uri, FromType.FromLocation);
        SourceId = sourceId;
        Interlocked.Exchange(ref _generation, generation);
        _finishedEvents.Reset();
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

    private void OnEndReached(object? sender, EventArgs args)
    {
        var sourceId = SourceId;
        var generation = Generation;
        _ = Task.Run(() =>
        {
            if (Volatile.Read(ref _disposed) != 0 || sourceId != SourceId || generation != Generation) return;
            if (LoopEnabled && _media is not null)
            {
                _ = _player.Play(_media);
                return;
            }

            var eventId = _finishedEvents.GetOrCreate(sourceId, generation);
            Finished?.Invoke(this, new AudioFinishedEventArgs(eventId, sourceId, generation));
        });
    }
}

public sealed class AudioFinishedEventArgs(Guid eventId, long sourceId, long sourceGeneration) : EventArgs
{
    public Guid EventId { get; } = eventId;
    public long SourceId { get; } = sourceId;
    public long SourceGeneration { get; } = sourceGeneration;
}

public sealed class AudioFinishedEventTracker
{
    private readonly object _sync = new();
    private long _sourceId;
    private long _generation = long.MinValue;
    private Guid _eventId;

    public Guid GetOrCreate(long sourceId, long generation)
    {
        lock (_sync)
        {
            if (_eventId == Guid.Empty || _sourceId != sourceId || _generation != generation)
            {
                _sourceId = sourceId;
                _generation = generation;
                _eventId = Guid.NewGuid();
            }
            return _eventId;
        }
    }

    public void Reset()
    {
        lock (_sync)
        {
            _sourceId = 0;
            _generation = long.MinValue;
            _eventId = Guid.Empty;
        }
    }
}
