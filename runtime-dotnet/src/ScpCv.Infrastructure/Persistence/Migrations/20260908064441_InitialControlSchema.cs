using System;
using Microsoft.EntityFrameworkCore.Migrations;

#pragma warning disable CA1861 // EF Core 迁移生成器会为每个复合索引生成常量数组。

#nullable disable

namespace ScpCv.Infrastructure.Persistence.Migrations
{
    /// <inheritdoc />
    public partial class InitialControlSchema : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "command_records",
                columns: table => new
                {
                    Id = table.Column<long>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    CommandId = table.Column<Guid>(type: "TEXT", nullable: false),
                    TargetKind = table.Column<string>(type: "TEXT", nullable: false),
                    TargetId = table.Column<int>(type: "INTEGER", nullable: false),
                    TargetSequence = table.Column<long>(type: "INTEGER", nullable: false),
                    Command = table.Column<string>(type: "TEXT", maxLength: 80, nullable: false),
                    ArgsJson = table.Column<string>(type: "TEXT", nullable: false),
                    SchemaVersion = table.Column<int>(type: "INTEGER", nullable: false),
                    SourceGeneration = table.Column<long>(type: "INTEGER", nullable: false),
                    SourceRevision = table.Column<long>(type: "INTEGER", nullable: false),
                    Status = table.Column<string>(type: "TEXT", nullable: false),
                    ConsumerInstanceId = table.Column<Guid>(type: "TEXT", nullable: true),
                    OwnerEpoch = table.Column<long>(type: "INTEGER", nullable: false),
                    ClaimToken = table.Column<Guid>(type: "TEXT", nullable: true),
                    LeaseExpiresAt = table.Column<long>(type: "INTEGER", nullable: true),
                    AttemptCount = table.Column<int>(type: "INTEGER", nullable: false),
                    Deadline = table.Column<long>(type: "INTEGER", nullable: true),
                    CreatedAt = table.Column<long>(type: "INTEGER", nullable: false),
                    StartedAt = table.Column<long>(type: "INTEGER", nullable: true),
                    CompletedAt = table.Column<long>(type: "INTEGER", nullable: true),
                    ResultCode = table.Column<string>(type: "TEXT", maxLength: 100, nullable: false),
                    ResultEvidenceJson = table.Column<string>(type: "TEXT", nullable: false),
                    LastError = table.Column<string>(type: "TEXT", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_command_records", x => x.Id);
                    table.CheckConstraint("CK_command_records_target", "(TargetKind = 'Display' AND TargetId >= 1 AND TargetId <= 4) OR (TargetKind = 'Audio' AND TargetId = 1)");
                });

            migrationBuilder.CreateTable(
                name: "media_folders",
                columns: table => new
                {
                    Id = table.Column<long>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    Name = table.Column<string>(type: "TEXT", maxLength: 255, nullable: false),
                    ParentId = table.Column<long>(type: "INTEGER", nullable: true),
                    CreatedAt = table.Column<long>(type: "INTEGER", nullable: false),
                    UpdatedAt = table.Column<long>(type: "INTEGER", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_media_folders", x => x.Id);
                    table.ForeignKey(
                        name: "FK_media_folders_media_folders_ParentId",
                        column: x => x.ParentId,
                        principalTable: "media_folders",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "office_operations",
                columns: table => new
                {
                    Id = table.Column<long>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    OperationId = table.Column<Guid>(type: "TEXT", nullable: false),
                    ParentCommandId = table.Column<Guid>(type: "TEXT", nullable: true),
                    ParentJobId = table.Column<Guid>(type: "TEXT", nullable: true),
                    ClaimToken = table.Column<Guid>(type: "TEXT", nullable: true),
                    GroupEpoch = table.Column<long>(type: "INTEGER", nullable: false),
                    HostEpoch = table.Column<long>(type: "INTEGER", nullable: false),
                    SlotEpoch = table.Column<long>(type: "INTEGER", nullable: false),
                    Deadline = table.Column<long>(type: "INTEGER", nullable: false),
                    Status = table.Column<string>(type: "TEXT", nullable: false),
                    RequestJson = table.Column<string>(type: "TEXT", nullable: false),
                    ResultFingerprint = table.Column<string>(type: "TEXT", nullable: false),
                    ErrorMessage = table.Column<string>(type: "TEXT", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_office_operations", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "runtime_group_control",
                columns: table => new
                {
                    Id = table.Column<long>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    GroupEpoch = table.Column<long>(type: "INTEGER", nullable: false),
                    State = table.Column<string>(type: "TEXT", nullable: false),
                    StopReason = table.Column<string>(type: "TEXT", nullable: false),
                    ExplicitStartRequestId = table.Column<Guid>(type: "TEXT", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_runtime_group_control", x => x.Id);
                    table.CheckConstraint("CK_runtime_group_control_singleton", "Id = 1");
                });

            migrationBuilder.CreateTable(
                name: "runtime_state",
                columns: table => new
                {
                    Id = table.Column<long>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    BigScreenMode = table.Column<string>(type: "TEXT", nullable: false),
                    VolumeLevel = table.Column<int>(type: "INTEGER", nullable: false),
                    VolumeMuted = table.Column<bool>(type: "INTEGER", nullable: false),
                    UpdatedAt = table.Column<long>(type: "INTEGER", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_runtime_state", x => x.Id);
                    table.CheckConstraint("CK_runtime_state_singleton", "Id = 1");
                    table.CheckConstraint("CK_runtime_state_volume", "VolumeLevel >= 0 AND VolumeLevel <= 100");
                });

            migrationBuilder.CreateTable(
                name: "scenarios",
                columns: table => new
                {
                    Id = table.Column<long>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    Name = table.Column<string>(type: "TEXT", maxLength: 255, nullable: false),
                    Description = table.Column<string>(type: "TEXT", nullable: false),
                    SortOrder = table.Column<int>(type: "INTEGER", nullable: false),
                    BigScreenModeState = table.Column<string>(type: "TEXT", nullable: false),
                    BigScreenMode = table.Column<string>(type: "TEXT", nullable: false),
                    VolumeState = table.Column<string>(type: "TEXT", nullable: false),
                    VolumeLevel = table.Column<int>(type: "INTEGER", nullable: false),
                    TargetsJson = table.Column<string>(type: "TEXT", nullable: false),
                    CreatedAt = table.Column<long>(type: "INTEGER", nullable: false),
                    UpdatedAt = table.Column<long>(type: "INTEGER", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_scenarios", x => x.Id);
                    table.CheckConstraint("CK_scenarios_volume", "VolumeLevel >= 0 AND VolumeLevel <= 100");
                });

            migrationBuilder.CreateTable(
                name: "stream_sources",
                columns: table => new
                {
                    Id = table.Column<long>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    Name = table.Column<string>(type: "TEXT", nullable: false),
                    StreamIdentifier = table.Column<string>(type: "TEXT", maxLength: 255, nullable: false),
                    Url = table.Column<string>(type: "TEXT", nullable: false),
                    IsOnline = table.Column<bool>(type: "INTEGER", nullable: false),
                    IsActive = table.Column<bool>(type: "INTEGER", nullable: false),
                    State = table.Column<string>(type: "TEXT", nullable: false),
                    LastSeenAt = table.Column<long>(type: "INTEGER", nullable: true),
                    ErrorMessage = table.Column<string>(type: "TEXT", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_stream_sources", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "user_accounts",
                columns: table => new
                {
                    Id = table.Column<long>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    Username = table.Column<string>(type: "TEXT", maxLength: 150, nullable: false),
                    PasswordHash = table.Column<string>(type: "TEXT", maxLength: 512, nullable: false),
                    IsActive = table.Column<bool>(type: "INTEGER", nullable: false),
                    IsStaff = table.Column<bool>(type: "INTEGER", nullable: false),
                    IsSuperuser = table.Column<bool>(type: "INTEGER", nullable: false),
                    GroupsJson = table.Column<string>(type: "TEXT", nullable: false),
                    PermissionsJson = table.Column<string>(type: "TEXT", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_user_accounts", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "worker_ownerships",
                columns: table => new
                {
                    Id = table.Column<long>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    TargetKind = table.Column<string>(type: "TEXT", nullable: false),
                    TargetId = table.Column<int>(type: "INTEGER", nullable: false),
                    WorkerInstanceId = table.Column<Guid>(type: "TEXT", nullable: false),
                    ProcessId = table.Column<int>(type: "INTEGER", nullable: false),
                    ProcessStartTime = table.Column<long>(type: "INTEGER", nullable: false),
                    LogonSessionId = table.Column<int>(type: "INTEGER", nullable: false),
                    OwnerEpoch = table.Column<long>(type: "INTEGER", nullable: false),
                    LastTransportHeartbeat = table.Column<long>(type: "INTEGER", nullable: false),
                    LastUiProgress = table.Column<long>(type: "INTEGER", nullable: true),
                    CapabilitiesJson = table.Column<string>(type: "TEXT", nullable: false),
                    Status = table.Column<string>(type: "TEXT", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_worker_ownerships", x => x.Id);
                });

            migrationBuilder.CreateTable(
                name: "media_sources",
                columns: table => new
                {
                    Id = table.Column<long>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    SourceType = table.Column<string>(type: "TEXT", nullable: false),
                    Name = table.Column<string>(type: "TEXT", maxLength: 255, nullable: false),
                    Uri = table.Column<string>(type: "TEXT", nullable: false),
                    UploadedFile = table.Column<string>(type: "TEXT", nullable: false),
                    StreamIdentifier = table.Column<string>(type: "TEXT", nullable: false),
                    IsAvailable = table.Column<bool>(type: "INTEGER", nullable: false),
                    FolderId = table.Column<long>(type: "INTEGER", nullable: true),
                    OriginalFilename = table.Column<string>(type: "TEXT", nullable: false),
                    FileSize = table.Column<long>(type: "INTEGER", nullable: false),
                    MimeType = table.Column<string>(type: "TEXT", maxLength: 255, nullable: false),
                    IsTemporary = table.Column<bool>(type: "INTEGER", nullable: false),
                    ExpiresAt = table.Column<long>(type: "INTEGER", nullable: true),
                    MetadataJson = table.Column<string>(type: "TEXT", nullable: false),
                    KeepAlive = table.Column<bool>(type: "INTEGER", nullable: false),
                    SourceRevision = table.Column<long>(type: "INTEGER", nullable: false),
                    ContentDigest = table.Column<string>(type: "TEXT", maxLength: 128, nullable: false),
                    CreatedAt = table.Column<long>(type: "INTEGER", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_media_sources", x => x.Id);
                    table.ForeignKey(
                        name: "FK_media_sources_media_folders_FolderId",
                        column: x => x.FolderId,
                        principalTable: "media_folders",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.SetNull);
                });

            migrationBuilder.CreateTable(
                name: "artifact_manifests",
                columns: table => new
                {
                    Id = table.Column<long>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    SourceId = table.Column<long>(type: "INTEGER", nullable: false),
                    SourceDigest = table.Column<string>(type: "TEXT", nullable: false),
                    RecipeVersion = table.Column<string>(type: "TEXT", nullable: false),
                    RelativePath = table.Column<string>(type: "TEXT", nullable: false),
                    Sha256 = table.Column<string>(type: "TEXT", nullable: false),
                    FileSize = table.Column<long>(type: "INTEGER", nullable: false),
                    PageCount = table.Column<int>(type: "INTEGER", nullable: false),
                    Status = table.Column<string>(type: "TEXT", nullable: false),
                    ErrorMessage = table.Column<string>(type: "TEXT", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_artifact_manifests", x => x.Id);
                    table.ForeignKey(
                        name: "FK_artifact_manifests_media_sources_SourceId",
                        column: x => x.SourceId,
                        principalTable: "media_sources",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "background_audio_state",
                columns: table => new
                {
                    Id = table.Column<long>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    CurrentSourceId = table.Column<long>(type: "INTEGER", nullable: true),
                    PlaybackState = table.Column<string>(type: "TEXT", nullable: false),
                    ErrorMessage = table.Column<string>(type: "TEXT", nullable: false),
                    PositionMs = table.Column<long>(type: "INTEGER", nullable: false),
                    DurationMs = table.Column<long>(type: "INTEGER", nullable: false),
                    Volume = table.Column<int>(type: "INTEGER", nullable: false),
                    IsMuted = table.Column<bool>(type: "INTEGER", nullable: false),
                    LoopEnabled = table.Column<bool>(type: "INTEGER", nullable: false),
                    PendingCommand = table.Column<string>(type: "TEXT", nullable: false),
                    CommandArgsJson = table.Column<string>(type: "TEXT", nullable: false),
                    UpdatedAt = table.Column<long>(type: "INTEGER", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_background_audio_state", x => x.Id);
                    table.CheckConstraint("CK_background_audio_state_singleton", "Id = 1");
                    table.CheckConstraint("CK_background_audio_state_volume", "Volume >= 0 AND Volume <= 100");
                    table.ForeignKey(
                        name: "FK_background_audio_state_media_sources_CurrentSourceId",
                        column: x => x.CurrentSourceId,
                        principalTable: "media_sources",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.SetNull);
                });

            migrationBuilder.CreateTable(
                name: "media_preparation_jobs",
                columns: table => new
                {
                    Id = table.Column<long>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    JobId = table.Column<Guid>(type: "TEXT", nullable: false),
                    SourceId = table.Column<long>(type: "INTEGER", nullable: false),
                    SourceRevision = table.Column<long>(type: "INTEGER", nullable: false),
                    SourceDigest = table.Column<string>(type: "TEXT", nullable: false),
                    Kind = table.Column<string>(type: "TEXT", nullable: false),
                    Status = table.Column<string>(type: "TEXT", nullable: false),
                    Priority = table.Column<int>(type: "INTEGER", nullable: false),
                    Deadline = table.Column<long>(type: "INTEGER", nullable: true),
                    RecipeVersion = table.Column<string>(type: "TEXT", nullable: false),
                    ArtifactManifestJson = table.Column<string>(type: "TEXT", nullable: false),
                    ErrorMessage = table.Column<string>(type: "TEXT", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_media_preparation_jobs", x => x.Id);
                    table.ForeignKey(
                        name: "FK_media_preparation_jobs_media_sources_SourceId",
                        column: x => x.SourceId,
                        principalTable: "media_sources",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "playback_sessions",
                columns: table => new
                {
                    Id = table.Column<long>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    WindowId = table.Column<int>(type: "INTEGER", nullable: false),
                    MediaSourceId = table.Column<long>(type: "INTEGER", nullable: true),
                    PlaybackState = table.Column<string>(type: "TEXT", nullable: false),
                    ErrorMessage = table.Column<string>(type: "TEXT", nullable: false),
                    DisplayMode = table.Column<string>(type: "TEXT", nullable: false),
                    TargetDisplayLabel = table.Column<string>(type: "TEXT", nullable: false),
                    CurrentSlide = table.Column<int>(type: "INTEGER", nullable: false),
                    TotalSlides = table.Column<int>(type: "INTEGER", nullable: false),
                    PlaybackMode = table.Column<string>(type: "TEXT", nullable: false),
                    PositionMs = table.Column<long>(type: "INTEGER", nullable: false),
                    DurationMs = table.Column<long>(type: "INTEGER", nullable: false),
                    Volume = table.Column<int>(type: "INTEGER", nullable: false),
                    IsMuted = table.Column<bool>(type: "INTEGER", nullable: false),
                    LoopEnabled = table.Column<bool>(type: "INTEGER", nullable: false),
                    PendingCommand = table.Column<string>(type: "TEXT", nullable: false),
                    CommandArgsJson = table.Column<string>(type: "TEXT", nullable: false),
                    PlayerLastSeenAt = table.Column<long>(type: "INTEGER", nullable: true),
                    LastUpdatedAt = table.Column<long>(type: "INTEGER", nullable: false),
                    DesiredGeneration = table.Column<long>(type: "INTEGER", nullable: false),
                    ObservedGeneration = table.Column<long>(type: "INTEGER", nullable: false),
                    ActualSourceId = table.Column<long>(type: "INTEGER", nullable: true),
                    ActualAdapterKind = table.Column<string>(type: "TEXT", nullable: false),
                    CleanupPending = table.Column<bool>(type: "INTEGER", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_playback_sessions", x => x.Id);
                    table.CheckConstraint("CK_playback_sessions_volume", "Volume >= 0 AND Volume <= 100");
                    table.CheckConstraint("CK_playback_sessions_window", "WindowId >= 1 AND WindowId <= 4");
                    table.ForeignKey(
                        name: "FK_playback_sessions_media_sources_MediaSourceId",
                        column: x => x.MediaSourceId,
                        principalTable: "media_sources",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.SetNull);
                });

            migrationBuilder.CreateTable(
                name: "ppt_resources",
                columns: table => new
                {
                    Id = table.Column<long>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    SourceId = table.Column<long>(type: "INTEGER", nullable: false),
                    PageIndex = table.Column<int>(type: "INTEGER", nullable: false),
                    SlideImage = table.Column<string>(type: "TEXT", nullable: false),
                    SpeakerNotes = table.Column<string>(type: "TEXT", nullable: false),
                    MediaItemsJson = table.Column<string>(type: "TEXT", nullable: false),
                    CreatedAt = table.Column<long>(type: "INTEGER", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_ppt_resources", x => x.Id);
                    table.CheckConstraint("CK_ppt_resources_page_index", "PageIndex >= 1");
                    table.ForeignKey(
                        name: "FK_ppt_resources_media_sources_SourceId",
                        column: x => x.SourceId,
                        principalTable: "media_sources",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "background_audio_playlist_items",
                columns: table => new
                {
                    Id = table.Column<long>(type: "INTEGER", nullable: false)
                        .Annotation("Sqlite:Autoincrement", true),
                    StateId = table.Column<long>(type: "INTEGER", nullable: false),
                    SourceId = table.Column<long>(type: "INTEGER", nullable: false),
                    SortOrder = table.Column<int>(type: "INTEGER", nullable: false),
                    CreatedAt = table.Column<long>(type: "INTEGER", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_background_audio_playlist_items", x => x.Id);
                    table.ForeignKey(
                        name: "FK_background_audio_playlist_items_background_audio_state_StateId",
                        column: x => x.StateId,
                        principalTable: "background_audio_state",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                    table.ForeignKey(
                        name: "FK_background_audio_playlist_items_media_sources_SourceId",
                        column: x => x.SourceId,
                        principalTable: "media_sources",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateIndex(
                name: "IX_artifact_manifests_SourceId_SourceDigest_RecipeVersion_RelativePath",
                table: "artifact_manifests",
                columns: new[] { "SourceId", "SourceDigest", "RecipeVersion", "RelativePath" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_background_audio_playlist_items_SortOrder_Id",
                table: "background_audio_playlist_items",
                columns: new[] { "SortOrder", "Id" });

            migrationBuilder.CreateIndex(
                name: "IX_background_audio_playlist_items_SourceId",
                table: "background_audio_playlist_items",
                column: "SourceId");

            migrationBuilder.CreateIndex(
                name: "IX_background_audio_playlist_items_StateId",
                table: "background_audio_playlist_items",
                column: "StateId");

            migrationBuilder.CreateIndex(
                name: "IX_background_audio_state_CurrentSourceId",
                table: "background_audio_state",
                column: "CurrentSourceId");

            migrationBuilder.CreateIndex(
                name: "IX_command_records_CommandId",
                table: "command_records",
                column: "CommandId",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_command_records_Status_LeaseExpiresAt",
                table: "command_records",
                columns: new[] { "Status", "LeaseExpiresAt" });

            migrationBuilder.CreateIndex(
                name: "IX_command_records_TargetKind_TargetId",
                table: "command_records",
                columns: new[] { "TargetKind", "TargetId" },
                unique: true,
                filter: "Status = 'Processing'");

            migrationBuilder.CreateIndex(
                name: "IX_command_records_TargetKind_TargetId_Status_TargetSequence",
                table: "command_records",
                columns: new[] { "TargetKind", "TargetId", "Status", "TargetSequence" });

            migrationBuilder.CreateIndex(
                name: "IX_command_records_TargetKind_TargetId_TargetSequence",
                table: "command_records",
                columns: new[] { "TargetKind", "TargetId", "TargetSequence" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_media_folders_ParentId",
                table: "media_folders",
                column: "ParentId");

            migrationBuilder.CreateIndex(
                name: "IX_media_preparation_jobs_JobId",
                table: "media_preparation_jobs",
                column: "JobId",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_media_preparation_jobs_SourceId_SourceDigest_Kind_RecipeVersion",
                table: "media_preparation_jobs",
                columns: new[] { "SourceId", "SourceDigest", "Kind", "RecipeVersion" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_media_sources_ExpiresAt",
                table: "media_sources",
                column: "ExpiresAt");

            migrationBuilder.CreateIndex(
                name: "IX_media_sources_FolderId",
                table: "media_sources",
                column: "FolderId");

            migrationBuilder.CreateIndex(
                name: "IX_media_sources_StreamIdentifier",
                table: "media_sources",
                column: "StreamIdentifier");

            migrationBuilder.CreateIndex(
                name: "IX_office_operations_OperationId",
                table: "office_operations",
                column: "OperationId",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_office_operations_ParentCommandId",
                table: "office_operations",
                column: "ParentCommandId");

            migrationBuilder.CreateIndex(
                name: "IX_office_operations_ParentJobId",
                table: "office_operations",
                column: "ParentJobId");

            migrationBuilder.CreateIndex(
                name: "IX_office_operations_Status_Deadline",
                table: "office_operations",
                columns: new[] { "Status", "Deadline" });

            migrationBuilder.CreateIndex(
                name: "IX_playback_sessions_MediaSourceId",
                table: "playback_sessions",
                column: "MediaSourceId");

            migrationBuilder.CreateIndex(
                name: "IX_playback_sessions_WindowId",
                table: "playback_sessions",
                column: "WindowId",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_ppt_resources_SourceId_PageIndex",
                table: "ppt_resources",
                columns: new[] { "SourceId", "PageIndex" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_scenarios_SortOrder_UpdatedAt",
                table: "scenarios",
                columns: new[] { "SortOrder", "UpdatedAt" });

            migrationBuilder.CreateIndex(
                name: "IX_stream_sources_StreamIdentifier",
                table: "stream_sources",
                column: "StreamIdentifier",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_user_accounts_Username",
                table: "user_accounts",
                column: "Username",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_worker_ownerships_TargetKind_TargetId",
                table: "worker_ownerships",
                columns: new[] { "TargetKind", "TargetId" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_worker_ownerships_WorkerInstanceId",
                table: "worker_ownerships",
                column: "WorkerInstanceId",
                unique: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "artifact_manifests");

            migrationBuilder.DropTable(
                name: "background_audio_playlist_items");

            migrationBuilder.DropTable(
                name: "command_records");

            migrationBuilder.DropTable(
                name: "media_preparation_jobs");

            migrationBuilder.DropTable(
                name: "office_operations");

            migrationBuilder.DropTable(
                name: "playback_sessions");

            migrationBuilder.DropTable(
                name: "ppt_resources");

            migrationBuilder.DropTable(
                name: "runtime_group_control");

            migrationBuilder.DropTable(
                name: "runtime_state");

            migrationBuilder.DropTable(
                name: "scenarios");

            migrationBuilder.DropTable(
                name: "stream_sources");

            migrationBuilder.DropTable(
                name: "user_accounts");

            migrationBuilder.DropTable(
                name: "worker_ownerships");

            migrationBuilder.DropTable(
                name: "background_audio_state");

            migrationBuilder.DropTable(
                name: "media_sources");

            migrationBuilder.DropTable(
                name: "media_folders");
        }
    }
}

#pragma warning restore CA1861
