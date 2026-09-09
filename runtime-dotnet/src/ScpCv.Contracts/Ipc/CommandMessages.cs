using System.Text.Json;
using System.Text.Json.Serialization;

namespace ScpCv.Contracts.Ipc;

public sealed record WakeDto
{
    [JsonPropertyName("highest_sequence")]
    public long HighestSequence { get; init; }
}

public sealed record ClaimRequestDto
{
    [JsonPropertyName("group_epoch")]
    public long GroupEpoch { get; init; }
}

public sealed record CommandLeaseDto
{
    [JsonPropertyName("command_id")]
    public Guid CommandId { get; init; }

    [JsonPropertyName("target_sequence")]
    public long TargetSequence { get; init; }

    [JsonPropertyName("command")]
    public string Command { get; init; } = string.Empty;

    [JsonPropertyName("args")]
    public Dictionary<string, JsonElement> Args { get; init; } = [];

    [JsonPropertyName("claim_token")]
    public Guid ClaimToken { get; init; }

    [JsonPropertyName("owner_epoch")]
    public long OwnerEpoch { get; init; }

    [JsonPropertyName("group_epoch")]
    public long GroupEpoch { get; init; }

    [JsonPropertyName("source_generation")]
    public long SourceGeneration { get; init; }

    [JsonPropertyName("source_revision")]
    public long SourceRevision { get; init; }

    [JsonPropertyName("lease_expires_at")]
    public string LeaseExpiresAt { get; init; } = string.Empty;

    [JsonPropertyName("deadline")]
    public string? Deadline { get; init; }
}

public sealed record NoWorkDto
{
    [JsonPropertyName("reason")]
    public string Reason { get; init; } = string.Empty;

    [JsonPropertyName("retry_after_ms")]
    public int RetryAfterMs { get; init; }
}

public sealed record LeaseRenewDto
{
    [JsonPropertyName("command_id")]
    public Guid CommandId { get; init; }

    [JsonPropertyName("claim_token")]
    public Guid ClaimToken { get; init; }

    [JsonPropertyName("owner_epoch")]
    public long OwnerEpoch { get; init; }

    [JsonPropertyName("stage")]
    public string Stage { get; init; } = string.Empty;

    [JsonPropertyName("ui_healthy")]
    public bool UiHealthy { get; init; }
}

public sealed record RenewResultDto
{
    [JsonPropertyName("accepted")]
    public bool Accepted { get; init; }

    [JsonPropertyName("lease_expires_at")]
    public string? LeaseExpiresAt { get; init; }

    [JsonPropertyName("reason")]
    public string Reason { get; init; } = string.Empty;
}

public sealed record CommandResultDto
{
    [JsonPropertyName("command_id")]
    public Guid CommandId { get; init; }

    [JsonPropertyName("claim_token")]
    public Guid ClaimToken { get; init; }

    [JsonPropertyName("owner_epoch")]
    public long OwnerEpoch { get; init; }

    [JsonPropertyName("status")]
    public string Status { get; init; } = string.Empty;

    [JsonPropertyName("result_code")]
    public string ResultCode { get; init; } = string.Empty;

    [JsonPropertyName("evidence")]
    public Dictionary<string, JsonElement> Evidence { get; init; } = [];

    [JsonPropertyName("actual_state")]
    public JsonElement ActualState { get; init; }

    [JsonPropertyName("result_hash")]
    public string ResultHash { get; init; } = string.Empty;
}

public sealed record ResultAcceptedDto
{
    [JsonPropertyName("command_id")]
    public Guid CommandId { get; init; }

    [JsonPropertyName("accepted")]
    public bool Accepted { get; init; }

    [JsonPropertyName("duplicate")]
    public bool Duplicate { get; init; }
}

public sealed record StateReportDto
{
    [JsonPropertyName("source_generation")]
    public long SourceGeneration { get; init; }

    [JsonPropertyName("report_sequence")]
    public long ReportSequence { get; init; }

    [JsonPropertyName("observed_at")]
    public string ObservedAt { get; init; } = string.Empty;

    [JsonPropertyName("state")]
    public JsonElement State { get; init; }
}

public sealed record AudioFinishedDto
{
    [JsonPropertyName("event_id")]
    public Guid EventId { get; init; }

    [JsonPropertyName("source_id")]
    public long SourceId { get; init; }

    [JsonPropertyName("source_generation")]
    public long SourceGeneration { get; init; }
}
