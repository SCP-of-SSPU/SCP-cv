using System.Text.Json.Serialization;

namespace ScpCv.Contracts.Http;

public sealed record DeviceDto
{
    [JsonPropertyName("name")]
    public string Name { get; init; } = string.Empty;

    [JsonPropertyName("device_type")]
    public string DeviceType { get; init; } = string.Empty;

    [JsonPropertyName("device_type_label")]
    public string DeviceTypeLabel { get; init; } = string.Empty;

    [JsonPropertyName("host")]
    public string Host { get; init; } = string.Empty;

    [JsonPropertyName("port")]
    public int? Port { get; init; }

    [JsonPropertyName("action")]
    public string Action { get; init; } = string.Empty;

    [JsonPropertyName("detail")]
    public string Detail { get; init; } = string.Empty;
}

public sealed record DeviceControlRequestDto
{
    [JsonPropertyName("action")]
    public string Action { get; init; } = string.Empty;
}
