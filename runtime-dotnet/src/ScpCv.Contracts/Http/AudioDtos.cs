using System.Text.Json.Serialization;

namespace ScpCv.Contracts.Http;

public sealed record BackgroundAudioStateDto
{
    [JsonPropertyName("id")]
    public long Id { get; init; }

    [JsonPropertyName("source_id")]
    public long? SourceId { get; init; }

    [JsonPropertyName("source_name")]
    public string SourceName { get; init; } = string.Empty;

    [JsonPropertyName("source_uri")]
    public string SourceUri { get; init; } = string.Empty;

    [JsonPropertyName("source")]
    public MediaSourceDto? Source { get; init; }

    [JsonPropertyName("current_item_id")]
    public long? CurrentItemId { get; init; }

    [JsonPropertyName("playback_state")]
    public string PlaybackState { get; init; } = "idle";

    [JsonPropertyName("playback_state_label")]
    public string PlaybackStateLabel { get; init; } = string.Empty;

    [JsonPropertyName("error_message")]
    public string ErrorMessage { get; init; } = string.Empty;

    [JsonPropertyName("position_ms")]
    public long PositionMs { get; init; }

    [JsonPropertyName("duration_ms")]
    public long DurationMs { get; init; }

    [JsonPropertyName("volume")]
    public int Volume { get; init; }

    [JsonPropertyName("is_muted")]
    public bool IsMuted { get; init; }

    [JsonPropertyName("loop_enabled")]
    public bool LoopEnabled { get; init; }

    [JsonPropertyName("pending_command")]
    public string PendingCommand { get; init; } = string.Empty;

    [JsonPropertyName("updated_at")]
    public string UpdatedAt { get; init; } = string.Empty;
}

public sealed record BackgroundAudioPlaylistItemDto
{
    [JsonPropertyName("id")]
    public long Id { get; init; }

    [JsonPropertyName("source_id")]
    public long SourceId { get; init; }

    [JsonPropertyName("source_name")]
    public string SourceName { get; init; } = string.Empty;

    [JsonPropertyName("sort_order")]
    public int SortOrder { get; init; }

    [JsonPropertyName("created_at")]
    public string CreatedAt { get; init; } = string.Empty;

    [JsonPropertyName("source")]
    public MediaSourceDto Source { get; init; } = new();
}

public sealed record BackgroundAudioDto
{
    [JsonPropertyName("state")]
    public BackgroundAudioStateDto State { get; init; } = new();

    [JsonPropertyName("playlist")]
    public IReadOnlyList<BackgroundAudioPlaylistItemDto> Playlist { get; init; } = [];
}
