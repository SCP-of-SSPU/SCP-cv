using ScpCv.Domain.Model;

namespace ScpCv.Infrastructure.Runtime;

public sealed record RegisterWorker(
    CommandTargetKind TargetKind,
    int TargetId,
    Guid WorkerInstanceId,
    int ProcessId,
    DateTimeOffset ProcessStartTime,
    int LogonSessionId,
    long GroupEpoch,
    string CapabilitiesJson,
    bool PreviousOwnerExitConfirmed = false);

public sealed record RegisterOfficeOperation(
    Guid OperationId,
    Guid? ParentCommandId,
    Guid? ParentJobId,
    Guid? ClaimToken,
    long SourceGeneration,
    long GroupEpoch,
    long HostEpoch,
    long SlotEpoch,
    DateTimeOffset Deadline,
    string RequestJson);

public sealed record CompleteOfficeOperation(
    Guid OperationId,
    long HostEpoch,
    long SlotEpoch,
    OperationStatus Status,
    string ResultFingerprint,
    string ErrorMessage);

public sealed record OfficeResultAcceptance(bool Accepted, bool Duplicate);

public sealed class RuntimeAuthorityException(string message) : InvalidOperationException(message);

public sealed class OfficeOperationConflictException(string message) : InvalidOperationException(message);
