using System.Text.Json;
using System.Text.Json.Serialization;

namespace ScpCv.Contracts.Ipc;

public sealed record OfficeRequestDto
{
    [JsonPropertyName("office_operation_id")]
    public Guid OfficeOperationId { get; init; }

    [JsonPropertyName("parent_command_id")]
    public Guid? ParentCommandId { get; init; }

    [JsonPropertyName("parent_job_id")]
    public Guid? ParentJobId { get; init; }

    [JsonPropertyName("claim_token")]
    public Guid? ClaimToken { get; init; }

    [JsonPropertyName("source_generation")]
    public long SourceGeneration { get; init; }

    [JsonPropertyName("group_epoch")]
    public long GroupEpoch { get; init; }

    [JsonPropertyName("host_epoch")]
    public long HostEpoch { get; init; }

    [JsonPropertyName("slot_epoch")]
    public long SlotEpoch { get; init; }

    [JsonPropertyName("deadline")]
    public string Deadline { get; init; } = string.Empty;

    [JsonPropertyName("operation")]
    public string Operation { get; init; } = string.Empty;

    [JsonPropertyName("parameters")]
    public Dictionary<string, JsonElement> Parameters { get; init; } = [];
}

public sealed record OfficeResultDto
{
    [JsonPropertyName("office_operation_id")]
    public Guid OfficeOperationId { get; init; }

    [JsonPropertyName("status")]
    public string Status { get; init; } = string.Empty;

    [JsonPropertyName("result_fingerprint")]
    public string ResultFingerprint { get; init; } = string.Empty;

    [JsonPropertyName("result")]
    public JsonElement Result { get; init; }

    [JsonPropertyName("error_code")]
    public string ErrorCode { get; init; } = string.Empty;

    [JsonPropertyName("error_detail")]
    public string ErrorDetail { get; init; } = string.Empty;
}

public sealed record ShutdownRequestDto
{
    [JsonPropertyName("request_id")]
    public Guid RequestId { get; init; }

    [JsonPropertyName("reason")]
    public string Reason { get; init; } = string.Empty;

    [JsonPropertyName("deadline")]
    public string Deadline { get; init; } = string.Empty;
}

public sealed record ShutdownCompleteDto
{
    [JsonPropertyName("request_id")]
    public Guid RequestId { get; init; }

    [JsonPropertyName("status")]
    public string Status { get; init; } = string.Empty;

    [JsonPropertyName("cleanup_results")]
    public IReadOnlyDictionary<string, string> CleanupResults { get; init; } =
        new Dictionary<string, string>();
}

public sealed record ErrorMessageDto
{
    [JsonPropertyName("code")]
    public string Code { get; init; } = string.Empty;

    [JsonPropertyName("stage")]
    public string Stage { get; init; } = string.Empty;

    [JsonPropertyName("retryable")]
    public bool Retryable { get; init; }

    [JsonPropertyName("detail")]
    public string Detail { get; init; } = string.Empty;
}
