namespace ScpCv.Domain.Model;

public sealed class UserAccount
{
    public long Id { get; set; }
    public string Username { get; set; } = string.Empty;
    public string PasswordHash { get; set; } = string.Empty;
    public bool IsActive { get; set; } = true;
    public bool IsStaff { get; set; }
    public bool IsSuperuser { get; set; }
    public string GroupsJson { get; set; } = "[]";
    public string PermissionsJson { get; set; } = "[]";
}

public sealed class MediaFolder
{
    public long Id { get; set; }
    public string Name { get; set; } = string.Empty;
    public long? ParentId { get; set; }
    public MediaFolder? Parent { get; set; }
    public ICollection<MediaFolder> Children { get; } = new List<MediaFolder>();
    public ICollection<MediaSource> Sources { get; } = new List<MediaSource>();
    public DateTimeOffset CreatedAt { get; set; }
    public DateTimeOffset UpdatedAt { get; set; }
}

public sealed class MediaSource
{
    public long Id { get; set; }
    public MediaSourceType SourceType { get; set; }
    public string Name { get; set; } = string.Empty;
    public string Uri { get; set; } = string.Empty;
    public string UploadedFile { get; set; } = string.Empty;
    public string StreamIdentifier { get; set; } = string.Empty;
    public bool IsAvailable { get; set; } = true;
    public long? FolderId { get; set; }
    public MediaFolder? Folder { get; set; }
    public string OriginalFilename { get; set; } = string.Empty;
    public long FileSize { get; set; }
    public string MimeType { get; set; } = string.Empty;
    public bool IsTemporary { get; set; }
    public DateTimeOffset? ExpiresAt { get; set; }
    public string MetadataJson { get; set; } = "{}";
    public bool KeepAlive { get; set; } = true;
    public long SourceRevision { get; set; }
    public string ContentDigest { get; set; } = string.Empty;
    public DateTimeOffset CreatedAt { get; set; }
    public ICollection<PptResource> PptResources { get; } = new List<PptResource>();
}

public sealed class PptResource
{
    public long Id { get; set; }
    public long SourceId { get; set; }
    public MediaSource Source { get; set; } = null!;
    public int PageIndex { get; set; }
    public string SlideImage { get; set; } = string.Empty;
    public string SpeakerNotes { get; set; } = string.Empty;
    public string MediaItemsJson { get; set; } = "[]";
    public DateTimeOffset CreatedAt { get; set; }
}

public sealed class PlaybackSession
{
    public long Id { get; set; }
    public int WindowId { get; set; }
    public long? MediaSourceId { get; set; }
    public MediaSource? MediaSource { get; set; }
    public PlaybackState PlaybackState { get; set; } = PlaybackState.Idle;
    public string ErrorMessage { get; set; } = string.Empty;
    public DisplayMode DisplayMode { get; set; } = DisplayMode.Single;
    public string TargetDisplayLabel { get; set; } = string.Empty;
    public int CurrentSlide { get; set; }
    public int TotalSlides { get; set; }
    public PlaybackMode PlaybackMode { get; set; }
    public long PositionMs { get; set; }
    public long DurationMs { get; set; }
    public int Volume { get; set; } = 100;
    public bool IsMuted { get; set; }
    public bool LoopEnabled { get; set; }
    public string PendingCommand { get; set; } = string.Empty;
    public string CommandArgsJson { get; set; } = "{}";
    public DateTimeOffset? PlayerLastSeenAt { get; set; }
    public DateTimeOffset LastUpdatedAt { get; set; }
    public long DesiredGeneration { get; set; }
    public long ObservedGeneration { get; set; }
    public long? ActualSourceId { get; set; }
    public string ActualAdapterKind { get; set; } = string.Empty;
    public bool CleanupPending { get; set; }
}

public sealed class RuntimeState
{
    public const long SingletonId = 1;

    public long Id { get; set; } = SingletonId;
    public BigScreenMode BigScreenMode { get; set; } = BigScreenMode.Single;
    public int VolumeLevel { get; set; } = 100;
    public bool VolumeMuted { get; set; }
    public DateTimeOffset UpdatedAt { get; set; }
}

public sealed class Scenario
{
    public long Id { get; set; }
    public string Name { get; set; } = string.Empty;
    public string Description { get; set; } = string.Empty;
    public int SortOrder { get; set; }
    public ScenarioValueState BigScreenModeState { get; set; }
    public BigScreenMode BigScreenMode { get; set; } = BigScreenMode.Single;
    public ScenarioValueState VolumeState { get; set; }
    public int VolumeLevel { get; set; } = 100;
    public string TargetsJson { get; set; } = "[]";
    public DateTimeOffset CreatedAt { get; set; }
    public DateTimeOffset UpdatedAt { get; set; }
}

public sealed class BackgroundAudioState
{
    public const long SingletonId = 1;

    public long Id { get; set; } = SingletonId;
    public long? CurrentSourceId { get; set; }
    public MediaSource? CurrentSource { get; set; }
    public PlaybackState PlaybackState { get; set; } = PlaybackState.Idle;
    public string ErrorMessage { get; set; } = string.Empty;
    public long PositionMs { get; set; }
    public long DurationMs { get; set; }
    public int Volume { get; set; } = 70;
    public bool IsMuted { get; set; }
    public bool LoopEnabled { get; set; } = true;
    public string PendingCommand { get; set; } = string.Empty;
    public string CommandArgsJson { get; set; } = "{}";
    public DateTimeOffset UpdatedAt { get; set; }
    public ICollection<BackgroundAudioPlaylistItem> Playlist { get; } = new List<BackgroundAudioPlaylistItem>();
}

public sealed class BackgroundAudioPlaylistItem
{
    public long Id { get; set; }
    public long StateId { get; set; } = BackgroundAudioState.SingletonId;
    public BackgroundAudioState State { get; set; } = null!;
    public long SourceId { get; set; }
    public MediaSource Source { get; set; } = null!;
    public int SortOrder { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
}

public sealed class StreamSource
{
    public long Id { get; set; }
    public string Name { get; set; } = string.Empty;
    public string StreamIdentifier { get; set; } = string.Empty;
    public string Url { get; set; } = string.Empty;
    public bool IsOnline { get; set; }
    public bool IsActive { get; set; }
    public string State { get; set; } = string.Empty;
    public DateTimeOffset? LastSeenAt { get; set; }
    public string ErrorMessage { get; set; } = string.Empty;
}

public sealed class CommandRecord
{
    public long Id { get; set; }
    public Guid CommandId { get; set; }
    public CommandTargetKind TargetKind { get; set; }
    public int TargetId { get; set; }
    public long TargetSequence { get; set; }
    public string Command { get; set; } = string.Empty;
    public string ArgsJson { get; set; } = "{}";
    public int SchemaVersion { get; set; } = 1;
    public long SourceGeneration { get; set; }
    public long SourceRevision { get; set; }
    public Guid? TriggerEventId { get; set; }
    public CommandStatus Status { get; set; } = CommandStatus.Pending;
    public Guid? ConsumerInstanceId { get; set; }
    public long OwnerEpoch { get; set; }
    public Guid? ClaimToken { get; set; }
    public DateTimeOffset? LeaseExpiresAt { get; set; }
    public int AttemptCount { get; set; }
    public DateTimeOffset? Deadline { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
    public DateTimeOffset? StartedAt { get; set; }
    public DateTimeOffset? CompletedAt { get; set; }
    public string ResultCode { get; set; } = string.Empty;
    public string ResultHash { get; set; } = string.Empty;
    public string ResultEvidenceJson { get; set; } = "{}";
    public string LastError { get; set; } = string.Empty;
}

public sealed class WorkerOwnership
{
    public long Id { get; set; }
    public CommandTargetKind TargetKind { get; set; }
    public int TargetId { get; set; }
    public Guid WorkerInstanceId { get; set; }
    public int ProcessId { get; set; }
    public DateTimeOffset ProcessStartTime { get; set; }
    public int LogonSessionId { get; set; }
    public long OwnerEpoch { get; set; }
    public DateTimeOffset LastTransportHeartbeat { get; set; }
    public DateTimeOffset? LastUiProgress { get; set; }
    public string CapabilitiesJson { get; set; } = "[]";
    public WorkerOwnershipState Status { get; set; }
}

public sealed class RuntimeGroupControl
{
    public const long SingletonId = 1;

    public long Id { get; set; } = SingletonId;
    public long GroupEpoch { get; set; }
    public RuntimeGroupState State { get; set; } = RuntimeGroupState.Stopped;
    public string StopReason { get; set; } = string.Empty;
    public Guid? ExplicitStartRequestId { get; set; }
}

public sealed class OfficeOperation
{
    public long Id { get; set; }
    public Guid OperationId { get; set; }
    public Guid? ParentCommandId { get; set; }
    public Guid? ParentJobId { get; set; }
    public Guid? ClaimToken { get; set; }
    public long SourceGeneration { get; set; }
    public long GroupEpoch { get; set; }
    public long HostEpoch { get; set; }
    public long SlotEpoch { get; set; }
    public DateTimeOffset Deadline { get; set; }
    public OperationStatus Status { get; set; } = OperationStatus.Queued;
    public string RequestJson { get; set; } = "{}";
    public string ResultFingerprint { get; set; } = string.Empty;
    public string ErrorMessage { get; set; } = string.Empty;
}

public sealed class MediaPreparationJob
{
    public long Id { get; set; }
    public Guid JobId { get; set; }
    public long SourceId { get; set; }
    public MediaSource Source { get; set; } = null!;
    public long SourceRevision { get; set; }
    public string SourceDigest { get; set; } = string.Empty;
    public PreparationJobKind Kind { get; set; }
    public OperationStatus Status { get; set; } = OperationStatus.Queued;
    public int Priority { get; set; }
    public DateTimeOffset? Deadline { get; set; }
    public string RecipeVersion { get; set; } = string.Empty;
    public string ArtifactManifestJson { get; set; } = "{}";
    public string ErrorMessage { get; set; } = string.Empty;
}

public sealed class ArtifactManifest
{
    public long Id { get; set; }
    public long SourceId { get; set; }
    public MediaSource Source { get; set; } = null!;
    public string SourceDigest { get; set; } = string.Empty;
    public string RecipeVersion { get; set; } = string.Empty;
    public string RelativePath { get; set; } = string.Empty;
    public string Sha256 { get; set; } = string.Empty;
    public long FileSize { get; set; }
    public int PageCount { get; set; }
    public OperationStatus Status { get; set; }
    public string ErrorMessage { get; set; } = string.Empty;
}
