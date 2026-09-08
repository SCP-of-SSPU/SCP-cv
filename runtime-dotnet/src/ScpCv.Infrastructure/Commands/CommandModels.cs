using ScpCv.Domain.Model;

namespace ScpCv.Infrastructure.Commands;

public sealed record EnqueueCommand(
    CommandTargetKind TargetKind,
    int TargetId,
    string Command,
    string ArgsJson,
    long SourceGeneration,
    long SourceRevision,
    DateTimeOffset? Deadline = null,
    int SchemaVersion = 1);

public sealed record ClaimCommand(
    CommandTargetKind TargetKind,
    int TargetId,
    Guid WorkerInstanceId,
    long OwnerEpoch,
    long GroupEpoch,
    TimeSpan LeaseDuration);

public sealed record CompleteCommand(
    Guid CommandId,
    Guid ClaimToken,
    long OwnerEpoch,
    CommandStatus Status,
    string ResultCode,
    string ResultHash,
    string ResultEvidenceJson);

public sealed record CommandResultAcceptance(bool Accepted, bool Duplicate);

public sealed class CommandFenceException(string message) : InvalidOperationException(message);

public sealed class CommandResultConflictException(string message) : InvalidOperationException(message);
