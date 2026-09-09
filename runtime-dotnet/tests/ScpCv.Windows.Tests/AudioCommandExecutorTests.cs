using System.Text.Json;
using ScpCv.AudioWorker.Audio;
using ScpCv.Contracts.Ipc;

namespace ScpCv.Windows.Tests;

public sealed class AudioCommandExecutorTests
{
    [Fact]
    public async Task OpenAppliesPlaybackSettingsAndReportsActualState()
    {
        var audio = new FakeAudioAdapter();
        var executor = new AudioCommandExecutor(audio);
        var lease = Lease("OPEN", 7, new
        {
            source_id = 42,
            uri = "file:///C:/media/test.mp3",
            volume = 35,
            muted = true,
            loop = true,
            autoplay = true,
        });

        var result = await executor.ExecuteAsync(lease);

        Assert.Equal("completed", result.Status);
        Assert.Equal(42, audio.SourceId);
        Assert.Equal(7, audio.Generation);
        Assert.Equal(35, audio.Volume);
        Assert.True(audio.IsMuted);
        Assert.True(audio.LoopEnabled);
        Assert.Equal(1, audio.PlayCalls);
        Assert.Equal(42, result.ActualState.GetProperty("source_id").GetInt64());
        Assert.Equal(7, result.ActualState.GetProperty("source_generation").GetInt64());
        Assert.Equal("playing", result.ActualState.GetProperty("playback_state").GetString());
    }

    [Theory]
    [InlineData("PLAY")]
    [InlineData("PAUSE")]
    [InlineData("STOP")]
    public async Task TransportCommandsExecuteExactlyOnce(string command)
    {
        var audio = new FakeAudioAdapter();
        var executor = new AudioCommandExecutor(audio);

        await executor.ExecuteAsync(Lease(command, 1, new { }));

        Assert.Equal(command == "PLAY" ? 1 : 0, audio.PlayCalls);
        Assert.Equal(command == "PAUSE" ? 1 : 0, audio.PauseCalls);
        Assert.Equal(command == "STOP" ? 1 : 0, audio.StopCalls);
    }

    [Fact]
    public async Task UnsupportedCommandFailsClosed()
    {
        var executor = new AudioCommandExecutor(new FakeAudioAdapter());
        await Assert.ThrowsAsync<InvalidOperationException>(() =>
            executor.ExecuteAsync(Lease("NEXT", 1, new { })));
    }

    private static CommandLeaseDto Lease(string command, long generation, object args)
    {
        var json = JsonSerializer.SerializeToElement(args);
        return new CommandLeaseDto
        {
            Command = command,
            SourceGeneration = generation,
            Args = json.EnumerateObject().ToDictionary(item => item.Name, item => item.Value.Clone()),
        };
    }

    private sealed class FakeAudioAdapter : IAudioPlaybackAdapter
    {
        public long SourceId { get; private set; }
        public long Generation { get; private set; }
        public int Volume { get; set; } = 70;
        public bool LoopEnabled { get; set; }
        public bool IsMuted { get; set; }
        public long PositionMs { get; private set; }
        public long DurationMs => 1000;
        public string PlaybackState { get; private set; } = "stopped";
        public int PlayCalls { get; private set; }
        public int PauseCalls { get; private set; }
        public int StopCalls { get; private set; }

        public Task OpenAsync(long sourceId, string uri, long generation, CancellationToken cancellationToken = default)
        {
            SourceId = sourceId;
            Generation = generation;
            PlaybackState = "loading";
            return Task.CompletedTask;
        }

        public Task PlayAsync(CancellationToken cancellationToken = default)
        {
            PlayCalls++;
            PlaybackState = "playing";
            return Task.CompletedTask;
        }

        public Task PauseAsync(CancellationToken cancellationToken = default)
        {
            PauseCalls++;
            PlaybackState = "paused";
            return Task.CompletedTask;
        }

        public Task StopAsync(CancellationToken cancellationToken = default)
        {
            StopCalls++;
            PlaybackState = "stopped";
            return Task.CompletedTask;
        }

        public Task SeekAsync(long positionMs, CancellationToken cancellationToken = default)
        {
            PositionMs = positionMs;
            return Task.CompletedTask;
        }
    }
}
