using System.Text.Json.Serialization;

namespace ScpCv.Contracts.Ipc;

public sealed record HelloDto
{
    [JsonPropertyName("role")]
    public string Role { get; init; } = string.Empty;

    [JsonPropertyName("process_id")]
    public int ProcessId { get; init; }

    [JsonPropertyName("process_start_time")]
    public string ProcessStartTime { get; init; } = string.Empty;

    [JsonPropertyName("logon_session_id")]
    public int LogonSessionId { get; init; }

    [JsonPropertyName("capabilities")]
    public IReadOnlyList<string> Capabilities { get; init; } = [];
}

public sealed record WelcomeDto
{
    [JsonPropertyName("service_epoch")]
    public long ServiceEpoch { get; init; }

    [JsonPropertyName("group_epoch")]
    public long GroupEpoch { get; init; }

    [JsonPropertyName("group_state")]
    public string GroupState { get; init; } = "stopped";

    [JsonPropertyName("accepted_capabilities")]
    public IReadOnlyList<string> AcceptedCapabilities { get; init; } = [];
}

public sealed record WorkerReadyDto
{
    [JsonPropertyName("dependencies")]
    public IReadOnlyDictionary<string, string> Dependencies { get; init; } =
        new Dictionary<string, string>();

    [JsonPropertyName("ui_ready")]
    public bool UiReady { get; init; }

    [JsonPropertyName("detail")]
    public string Detail { get; init; } = string.Empty;
}

public sealed record HealthReportDto
{
    [JsonPropertyName("transport_healthy")]
    public bool TransportHealthy { get; init; }

    [JsonPropertyName("ui_healthy")]
    public bool UiHealthy { get; init; }

    [JsonPropertyName("report_sequence")]
    public long ReportSequence { get; init; }

    [JsonPropertyName("observed_at")]
    public string ObservedAt { get; init; } = string.Empty;
}
