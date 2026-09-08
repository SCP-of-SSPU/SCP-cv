using System.Text.Json;
using System.Text.Json.Serialization;

namespace ScpCv.Contracts.Http;

public sealed record MediaFolderDto
{
    [JsonPropertyName("id")]
    public long Id { get; init; }

    [JsonPropertyName("name")]
    public string Name { get; init; } = string.Empty;

    [JsonPropertyName("parent_id")]
    public long? ParentId { get; init; }

    [JsonPropertyName("created_at")]
    public string CreatedAt { get; init; } = string.Empty;

    [JsonPropertyName("updated_at")]
    public string UpdatedAt { get; init; } = string.Empty;
}

public sealed record MediaSourceDto
{
    [JsonPropertyName("id")]
    public long Id { get; init; }

    [JsonPropertyName("source_type")]
    public string SourceType { get; init; } = string.Empty;

    [JsonPropertyName("name")]
    public string Name { get; init; } = string.Empty;

    [JsonPropertyName("uri")]
    public string Uri { get; init; } = string.Empty;

    [JsonPropertyName("is_available")]
    public bool IsAvailable { get; init; }

    [JsonPropertyName("stream_identifier")]
    public string StreamIdentifier { get; init; } = string.Empty;

    [JsonPropertyName("folder_id")]
    public long? FolderId { get; init; }

    [JsonPropertyName("original_filename")]
    public string OriginalFilename { get; init; } = string.Empty;

    [JsonPropertyName("file_size")]
    public long FileSize { get; init; }

    [JsonPropertyName("mime_type")]
    public string MimeType { get; init; } = string.Empty;

    [JsonPropertyName("is_temporary")]
    public bool IsTemporary { get; init; }

    [JsonPropertyName("expires_at")]
    public string? ExpiresAt { get; init; }

    [JsonPropertyName("metadata")]
    public Dictionary<string, JsonElement> Metadata { get; init; } = [];

    [JsonPropertyName("preheat_enabled")]
    public bool PreheatEnabled { get; init; }

    [JsonPropertyName("keep_alive")]
    public bool KeepAlive { get; init; }

    [JsonPropertyName("playback_mode")]
    public string PlaybackMode { get; init; } = string.Empty;

    [JsonPropertyName("preview_url")]
    public string PreviewUrl { get; init; } = string.Empty;

    [JsonPropertyName("thumbnail_url")]
    public string ThumbnailUrl { get; init; } = string.Empty;

    [JsonPropertyName("preview_kind")]
    public string PreviewKind { get; init; } = "icon";

    [JsonPropertyName("preview_label")]
    public string PreviewLabel { get; init; } = string.Empty;

    [JsonPropertyName("created_at")]
    public string CreatedAt { get; init; } = string.Empty;
}

public sealed record PptMediaItemDto
{
    [JsonPropertyName("id")]
    public string Id { get; init; } = string.Empty;

    [JsonPropertyName("media_index")]
    public int MediaIndex { get; init; }

    [JsonPropertyName("media_type")]
    public string MediaType { get; init; } = string.Empty;

    [JsonPropertyName("name")]
    public string Name { get; init; } = string.Empty;

    [JsonPropertyName("target")]
    public string Target { get; init; } = string.Empty;

    [JsonPropertyName("shape_id")]
    public int ShapeId { get; init; }
}

public sealed record PptResourceDto
{
    [JsonPropertyName("id")]
    public long Id { get; init; }

    [JsonPropertyName("source_id")]
    public long SourceId { get; init; }

    [JsonPropertyName("page_index")]
    public int PageIndex { get; init; }

    [JsonPropertyName("slide_image")]
    public string SlideImage { get; init; } = string.Empty;

    [JsonPropertyName("next_slide_image")]
    public string NextSlideImage { get; init; } = string.Empty;

    [JsonPropertyName("speaker_notes")]
    public string SpeakerNotes { get; init; } = string.Empty;

    [JsonPropertyName("has_media")]
    public bool HasMedia { get; init; }

    [JsonPropertyName("media_items")]
    public IReadOnlyList<PptMediaItemDto> MediaItems { get; init; } = [];

    [JsonPropertyName("created_at")]
    public string CreatedAt { get; init; } = string.Empty;
}
