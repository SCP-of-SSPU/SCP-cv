using System.Text.Json;
using System.Text.Json.Serialization;

namespace ScpCv.Contracts.Ipc;

public static class IpcProtocol
{
    public const int Version = 1;
    public const int MaximumFrameBytes = 1_048_576;
    public static readonly TimeSpan HandshakeTimeout = TimeSpan.FromSeconds(5);
    public static readonly TimeSpan FrameReadTimeout = TimeSpan.FromSeconds(10);
}

public sealed record IpcTargetDto
{
    [JsonPropertyName("kind")]
    public string Kind { get; init; } = string.Empty;

    [JsonPropertyName("id")]
    public int Id { get; init; }
}

public sealed record IpcFrameDto
{
    [JsonPropertyName("protocol_version")]
    public int ProtocolVersion { get; init; } = IpcProtocol.Version;

    [JsonPropertyName("message_type")]
    public string MessageType { get; init; } = string.Empty;

    [JsonPropertyName("message_id")]
    public Guid MessageId { get; init; }

    [JsonPropertyName("correlation_id")]
    public Guid? CorrelationId { get; init; }

    [JsonPropertyName("instance_id")]
    public Guid InstanceId { get; init; }

    [JsonPropertyName("owner_epoch")]
    public long OwnerEpoch { get; init; }

    [JsonPropertyName("target")]
    public IpcTargetDto? Target { get; init; }

    [JsonPropertyName("payload")]
    public JsonElement Payload { get; init; }
}
