using System.Text.Json;
using System.Text.Json.Serialization;

namespace ScpCv.Contracts.Http;

public sealed record PlaybackSessionDto
{
    [JsonPropertyName("window_id")]
    public int WindowId { get; init; }

    [JsonPropertyName("session_id")]
    public long SessionId { get; init; }

    [JsonPropertyName("source_id")]
    public long? SourceId { get; init; }

    [JsonPropertyName("source_name")]
    public string SourceName { get; init; } = string.Empty;

    [JsonPropertyName("source_type")]
    public string SourceType { get; init; } = string.Empty;

    [JsonPropertyName("source_type_label")]
    public string SourceTypeLabel { get; init; } = string.Empty;

    [JsonPropertyName("source_uri")]
    public string SourceUri { get; init; } = string.Empty;

    [JsonPropertyName("playback_mode")]
    public string PlaybackMode { get; init; } = string.Empty;

    [JsonPropertyName("playback_state")]
    public string PlaybackState { get; init; } = string.Empty;

    [JsonPropertyName("playback_state_label")]
    public string PlaybackStateLabel { get; init; } = string.Empty;

    [JsonPropertyName("error_message")]
    public string ErrorMessage { get; init; } = string.Empty;

    [JsonPropertyName("display_mode")]
    public string DisplayMode { get; init; } = "single";

    [JsonPropertyName("display_mode_label")]
    public string DisplayModeLabel { get; init; } = string.Empty;

    [JsonPropertyName("target_display_label")]
    public string TargetDisplayLabel { get; init; } = string.Empty;

    [JsonPropertyName("current_slide")]
    public int CurrentSlide { get; init; }

    [JsonPropertyName("total_slides")]
    public int TotalSlides { get; init; }

    [JsonPropertyName("position_ms")]
    public long PositionMs { get; init; }

    [JsonPropertyName("duration_ms")]
    public long DurationMs { get; init; }

    [JsonPropertyName("pending_command")]
    public string PendingCommand { get; init; } = string.Empty;

    [JsonPropertyName("player_online")]
    public bool PlayerOnline { get; init; }

    [JsonPropertyName("player_last_seen_at")]
    public string PlayerLastSeenAt { get; init; } = string.Empty;

    [JsonPropertyName("last_updated_at")]
    public string LastUpdatedAt { get; init; } = string.Empty;

    [JsonPropertyName("volume")]
    public int Volume { get; init; }

    [JsonPropertyName("is_muted")]
    public bool IsMuted { get; init; }

    [JsonPropertyName("loop_enabled")]
    public bool LoopEnabled { get; init; }
}

public sealed record PlaybackCommandRequestDto
{
    [JsonPropertyName("command")]
    public string Command { get; init; } = string.Empty;

    [JsonPropertyName("args")]
    public Dictionary<string, JsonElement> Args { get; init; } = [];
}

public sealed record RuntimeStateDto
{
    [JsonPropertyName("big_screen_mode")]
    public string BigScreenMode { get; init; } = "single";

    [JsonPropertyName("volume_level")]
    public int VolumeLevel { get; init; }

    [JsonPropertyName("muted_windows")]
    public IReadOnlyList<int> MutedWindows { get; init; } = [];
}

public sealed record DisplayTargetDto
{
    [JsonPropertyName("index")]
    public int Index { get; init; }

    [JsonPropertyName("name")]
    public string Name { get; init; } = string.Empty;

    [JsonPropertyName("width")]
    public int Width { get; init; }

    [JsonPropertyName("height")]
    public int Height { get; init; }

    [JsonPropertyName("x")]
    public int X { get; init; }

    [JsonPropertyName("y")]
    public int Y { get; init; }

    [JsonPropertyName("is_primary")]
    public bool IsPrimary { get; init; }
}
