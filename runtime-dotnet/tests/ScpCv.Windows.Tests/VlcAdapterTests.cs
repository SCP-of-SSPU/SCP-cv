using ScpCv.PlayerWorker.Adapters;

namespace ScpCv.Windows.Tests;

public sealed class VlcAdapterTests
{
    [Theory]
    [InlineData("srt://127.0.0.1:9000")]
    [InlineData("rtsp://127.0.0.1/live")]
    [InlineData("https://example.test/video.mp4")]
    public async Task SupportedStreamingUrisOpenAndExposeControls(string uri)
    {
        var session = new FakeVlcSession();
        var adapter = new VlcPlaybackAdapter(_ => Task.FromResult<IVlcMediaSession>(session));
        await adapter.OpenAsync(uri);
        await adapter.SeekAsync(500);
        await adapter.SetVolumeAsync(42);
        await adapter.SetLoopAsync(true);
        Assert.Equal(500, adapter.PositionMs);
        Assert.Equal(42, adapter.Volume);
        Assert.True(adapter.LoopEnabled);
        await adapter.CloseAsync();
    }

    private sealed class FakeVlcSession : IVlcMediaSession
    {
        public long PositionMs { get; private set; }
        public int Volume { get; private set; } = 100;
        public bool LoopEnabled { get; private set; }
        public event EventHandler? Ended
        {
            add { }
            remove { }
        }
        public Task PlayAsync(CancellationToken cancellationToken) => Task.CompletedTask;
        public Task PauseAsync(CancellationToken cancellationToken) => Task.CompletedTask;
        public Task StopAsync(CancellationToken cancellationToken) => Task.CompletedTask;
        public Task SeekAsync(long positionMs, CancellationToken cancellationToken) { PositionMs = positionMs; return Task.CompletedTask; }
        public Task SetVolumeAsync(int volume, CancellationToken cancellationToken) { Volume = volume; return Task.CompletedTask; }
        public Task SetLoopAsync(bool enabled, CancellationToken cancellationToken) { LoopEnabled = enabled; return Task.CompletedTask; }
        public ValueTask DisposeAsync() => ValueTask.CompletedTask;
    }
}
