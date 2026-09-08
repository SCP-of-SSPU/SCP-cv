using System.Text.Json.Serialization;

namespace ScpCv.Contracts.Http;

public sealed record ScenarioTargetDto
{
    [JsonPropertyName("window_id")]
    public int WindowId { get; init; }

    [JsonPropertyName("source_state")]
    public string SourceState { get; init; } = "unset";

    [JsonPropertyName("source_id")]
    public long? SourceId { get; init; }

    [JsonPropertyName("source_name")]
    public string SourceName { get; init; } = string.Empty;

    [JsonPropertyName("autoplay")]
    public bool Autoplay { get; init; } = true;

    [JsonPropertyName("resume")]
    public bool Resume { get; init; } = true;
}

public sealed record ScenarioDto
{
    [JsonPropertyName("id")]
    public long Id { get; init; }

    [JsonPropertyName("name")]
    public string Name { get; init; } = string.Empty;

    [JsonPropertyName("description")]
    public string Description { get; init; } = string.Empty;

    [JsonPropertyName("sort_order")]
    public int SortOrder { get; init; }

    [JsonPropertyName("big_screen_mode_state")]
    public string BigScreenModeState { get; init; } = "unset";

    [JsonPropertyName("big_screen_mode")]
    public string BigScreenMode { get; init; } = "single";

    [JsonPropertyName("big_screen_mode_label")]
    public string BigScreenModeLabel { get; init; } = string.Empty;

    [JsonPropertyName("volume_state")]
    public string VolumeState { get; init; } = "unset";

    [JsonPropertyName("volume_level")]
    public int VolumeLevel { get; init; }

    [JsonPropertyName("targets")]
    public IReadOnlyList<ScenarioTargetDto> Targets { get; init; } = [];

    [JsonPropertyName("created_at")]
    public string CreatedAt { get; init; } = string.Empty;

    [JsonPropertyName("updated_at")]
    public string UpdatedAt { get; init; } = string.Empty;
}

public sealed record ScenarioWriteDto
{
    [JsonPropertyName("name")]
    public string Name { get; init; } = string.Empty;

    [JsonPropertyName("description")]
    public string Description { get; init; } = string.Empty;

    [JsonPropertyName("big_screen_mode_state")]
    public string BigScreenModeState { get; init; } = "unset";

    [JsonPropertyName("big_screen_mode")]
    public string BigScreenMode { get; init; } = "single";

    [JsonPropertyName("volume_state")]
    public string VolumeState { get; init; } = "unset";

    [JsonPropertyName("volume_level")]
    public int VolumeLevel { get; init; } = 100;

    [JsonPropertyName("targets")]
    public IReadOnlyList<ScenarioTargetDto> Targets { get; init; } = [];
}
