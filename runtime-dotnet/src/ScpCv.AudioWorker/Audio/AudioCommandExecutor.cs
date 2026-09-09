using System.Text.Json;
using ScpCv.Contracts.Ipc;
using ScpCv.Contracts.Runtime;

namespace ScpCv.AudioWorker.Audio;

public interface IAudioPlaybackAdapter
{
    long SourceId { get; }
    int Volume { get; set; }
    bool LoopEnabled { get; set; }
    bool IsMuted { get; set; }
    long PositionMs { get; }
    long DurationMs { get; }
    string PlaybackState { get; }
    Task OpenAsync(long sourceId, string uri, long generation, CancellationToken cancellationToken = default);
    Task PlayAsync(CancellationToken cancellationToken = default);
    Task PauseAsync(CancellationToken cancellationToken = default);
    Task StopAsync(CancellationToken cancellationToken = default);
    Task SeekAsync(long positionMs, CancellationToken cancellationToken = default);
}

public sealed class AudioCommandExecutor(IAudioPlaybackAdapter audio)
{
    public async Task<WorkerExecutionResult> ExecuteAsync(
        CommandLeaseDto lease,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(lease);
        switch (lease.Command.Trim().ToUpperInvariant())
        {
            case "OPEN":
                await audio.OpenAsync(
                    Long(lease.Args, "source_id"),
                    String(lease.Args, "uri"),
                    lease.SourceGeneration,
                    cancellationToken).ConfigureAwait(false);
                audio.Volume = Int(lease.Args, "volume", audio.Volume);
                audio.IsMuted = Bool(lease.Args, "muted", false);
                audio.LoopEnabled = Bool(lease.Args, "loop", audio.LoopEnabled);
                if (Bool(lease.Args, "autoplay", true)) await audio.PlayAsync(cancellationToken).ConfigureAwait(false);
                break;
            case "PLAY": await audio.PlayAsync(cancellationToken).ConfigureAwait(false); break;
            case "PAUSE": await audio.PauseAsync(cancellationToken).ConfigureAwait(false); break;
            case "STOP": await audio.StopAsync(cancellationToken).ConfigureAwait(false); break;
            case "SEEK": await audio.SeekAsync(Long(lease.Args, "position_ms"), cancellationToken).ConfigureAwait(false); break;
            case "SET_VOLUME": audio.Volume = Int(lease.Args, "volume", audio.Volume); break;
            case "SET_MUTE": audio.IsMuted = Bool(lease.Args, "muted", audio.IsMuted); break;
            case "SET_LOOP": audio.LoopEnabled = Bool(lease.Args, "enabled", audio.LoopEnabled); break;
            default: throw new InvalidOperationException($"AudioWorker 不支持命令 {lease.Command}。");
        }

        return new WorkerExecutionResult(
            "completed",
            "ok",
            JsonSerializer.SerializeToElement(new
            {
                source_generation = lease.SourceGeneration,
                source_id = audio.SourceId == 0 ? (long?)null : audio.SourceId,
                playback_state = audio.PlaybackState,
                position_ms = audio.PositionMs,
                duration_ms = audio.DurationMs,
                volume = audio.Volume,
                muted = audio.IsMuted,
                loop_enabled = audio.LoopEnabled,
            }));
    }

    private static string String(Dictionary<string, JsonElement> args, string key) =>
        args.TryGetValue(key, out var value) && value.ValueKind == JsonValueKind.String
            ? value.GetString() ?? string.Empty
            : throw new InvalidDataException($"缺少字符串参数 {key}。");

    private static long Long(Dictionary<string, JsonElement> args, string key, long fallback = 0) =>
        args.TryGetValue(key, out var value) && value.TryGetInt64(out var parsed) ? parsed : fallback;

    private static int Int(Dictionary<string, JsonElement> args, string key, int fallback) =>
        args.TryGetValue(key, out var value) && value.TryGetInt32(out var parsed) ? parsed : fallback;

    private static bool Bool(Dictionary<string, JsonElement> args, string key, bool fallback) =>
        args.TryGetValue(key, out var value) && value.ValueKind is JsonValueKind.True or JsonValueKind.False
            ? value.GetBoolean()
            : fallback;
}
