using Microsoft.EntityFrameworkCore;
using System.Text.Json;
using System.Text.Json.Serialization;
using ScpCv.Contracts.Http;
using ScpCv.Domain.Model;
using ScpCv.Infrastructure.Media;
using ScpCv.Infrastructure.Persistence;
using ScpCv.Infrastructure.Commands;

namespace ScpCv.Infrastructure.Playback;

public sealed class RuntimeStateService(
    IDbContextFactory<ControlDbContext> contextFactory,
    WriteCoordinator writes,
    CommandCoordinator commands,
    TimeProvider? timeProvider = null)
{
    private static readonly int[] Windows = [1, 2, 3, 4];
    private readonly TimeProvider _timeProvider = timeProvider ?? TimeProvider.System;
    private readonly CommandCoordinator _commands = commands;

    public async Task<IReadOnlyList<PlaybackSessionDto>> GetSessionsAsync(CancellationToken cancellationToken = default)
    {
        await using var database = await contextFactory.CreateDbContextAsync(cancellationToken).ConfigureAwait(false);
        var sessions = await database.PlaybackSessions.AsNoTracking()
            .Include(session => session.MediaSource)
            .OrderBy(session => session.WindowId)
            .ToListAsync(cancellationToken).ConfigureAwait(false);
        return sessions.Select(session => ToSessionDto(session, _timeProvider.GetUtcNow())).ToArray();
    }

    public async Task<PlaybackSessionDto> GetSessionAsync(int windowId, CancellationToken cancellationToken = default)
    {
        ValidateWindow(windowId);
        await using var database = await contextFactory.CreateDbContextAsync(cancellationToken).ConfigureAwait(false);
        var session = await database.PlaybackSessions.AsNoTracking()
            .Include(item => item.MediaSource)
            .SingleAsync(item => item.WindowId == windowId, cancellationToken).ConfigureAwait(false);
        return ToSessionDto(session, _timeProvider.GetUtcNow());
    }

    public async Task<RuntimeStateDto> GetRuntimeAsync(CancellationToken cancellationToken = default)
    {
        await using var database = await contextFactory.CreateDbContextAsync(cancellationToken).ConfigureAwait(false);
        var runtime = await database.RuntimeStates.AsNoTracking().SingleAsync(cancellationToken).ConfigureAwait(false);
        return ToRuntimeDto(runtime);
    }

    public async Task<RuntimeStateDto> SetRuntimeModeAsync(string value, CancellationToken cancellationToken = default)
    {
        var mode = value.Trim().ToLowerInvariant() switch
        {
            "single" => BigScreenMode.Single,
            "double" => BigScreenMode.Double,
            _ => throw new PlaybackServiceException($"无效的大屏模式：{value}"),
        };
        var changedWindows = await writes.ExecuteAsync(
            async (database, token) =>
            {
                var runtime = await database.RuntimeStates.SingleAsync(token).ConfigureAwait(false);
                runtime.BigScreenMode = mode;
                runtime.UpdatedAt = _timeProvider.GetUtcNow();
                var sessions = await database.PlaybackSessions.ToListAsync(token).ConfigureAwait(false);
                var muted = MutedWindows(mode).ToHashSet();
                return sessions
                    .Where(session => session.IsMuted != muted.Contains(session.WindowId))
                    .Select(session => (session.WindowId, Muted: muted.Contains(session.WindowId)))
                    .ToArray();
            },
            cancellationToken).ConfigureAwait(false);
        foreach (var changed in changedWindows)
        {
            await SetMuteAsync(changed.WindowId, changed.Muted, cancellationToken).ConfigureAwait(false);
        }
        return await GetRuntimeAsync(cancellationToken).ConfigureAwait(false);
    }

    public async Task<SystemVolumeDto> GetSystemVolumeAsync(CancellationToken cancellationToken = default)
    {
        await using var database = await contextFactory.CreateDbContextAsync(cancellationToken).ConfigureAwait(false);
        var runtime = await database.RuntimeStates.AsNoTracking().SingleAsync(cancellationToken).ConfigureAwait(false);
        return ToVolumeDto(runtime);
    }

    public Task<SystemVolumeDto> SetSystemVolumeAsync(
        int? level,
        bool? muted,
        CancellationToken cancellationToken = default)
    {
        if (level is < 0 or > 100)
        {
            throw new PlaybackServiceException("系统音量必须在 0 到 100 之间", "volume_error");
        }

        return writes.ExecuteAsync(
            async (database, token) =>
            {
                var runtime = await database.RuntimeStates.SingleAsync(token).ConfigureAwait(false);
                if (level is not null)
                {
                    runtime.VolumeLevel = level.Value;
                }

                runtime.VolumeMuted = muted ?? (runtime.VolumeLevel == 0 || runtime.VolumeMuted);
                runtime.UpdatedAt = _timeProvider.GetUtcNow();
                return ToVolumeDto(runtime);
            },
            cancellationToken);
    }

    public Task<IReadOnlyList<PlaybackSessionDto>> SelectDisplayAsync(
        int windowId,
        string displayMode,
        string targetLabel,
        CancellationToken cancellationToken = default)
    {
        ValidateWindow(windowId);
        if (!string.Equals(displayMode, "single", StringComparison.OrdinalIgnoreCase))
        {
            throw new PlaybackServiceException($"无效的显示模式：{displayMode}");
        }

        return EnqueueDisplayAsync(
            windowId,
            "SELECT_DISPLAY",
            JsonSerializer.Serialize(new { display_mode = "single", target_label = targetLabel }),
            (session, command) =>
            {
                session.DisplayMode = DisplayMode.Single;
                session.TargetDisplayLabel = targetLabel;
                session.PendingCommand = command.Command;
            },
            cancellationToken);
    }

    public Task<IReadOnlyList<PlaybackSessionDto>> OpenSourceAsync(
        int windowId,
        long sourceId,
        bool autoplay,
        int targetSlide,
        CancellationToken cancellationToken = default)
    {
        ValidateWindow(windowId);
        if (sourceId <= 0)
        {
            throw new PlaybackServiceException("source_id 必须大于 0", "invalid_source");
        }

        return EnqueueDisplayAsync(
            windowId,
            "OPEN",
            "{}",
            async (database, session, command, token) =>
            {
                var source = await database.MediaSources.SingleOrDefaultAsync(item => item.Id == sourceId, token).ConfigureAwait(false)
                    ?? throw new PlaybackServiceException($"媒体源 id={sourceId} 不存在");
                session.MediaSourceId = source.Id;
                session.PlaybackMode = PlaybackMode.None;
                session.PlaybackState = PlaybackState.Loading;
                session.ErrorMessage = string.Empty;
                session.CurrentSlide = targetSlide;
                session.PendingCommand = command.Command;
                session.DesiredGeneration = checked(session.DesiredGeneration + 1);
                session.CommandArgsJson = JsonSerializer.Serialize(new
                {
                    source_id = source.Id,
                    source_type = SourceTypeName(source.SourceType),
                    uri = source.Uri,
                    autoplay,
                    target_slide = targetSlide,
                });
                command.ArgsJson = session.CommandArgsJson;
                command.SourceGeneration = session.DesiredGeneration;
                command.SourceRevision = source.SourceRevision;
            },
            cancellationToken);
    }

    public Task<IReadOnlyList<PlaybackSessionDto>> ControlAsync(
        int windowId,
        string command,
        CancellationToken cancellationToken = default)
    {
        var normalized = command.Trim().ToLowerInvariant();
        if (normalized is not ("play" or "pause" or "stop"))
        {
            throw new PlaybackServiceException($"无效的播放控制动作：{command}");
        }

        return EnqueueDisplayAsync(
            windowId,
            normalized.ToUpperInvariant(),
            "{}",
            async (database, session, command, token) =>
            {
                if (session.MediaSourceId is null)
                {
                    throw new PlaybackServiceException($"窗口 {windowId} 当前没有打开的媒体源");
                }

                session.PendingCommand = command.Command;
                command.SourceGeneration = session.DesiredGeneration;
                command.SourceRevision = await database.MediaSources
                    .Where(source => source.Id == session.MediaSourceId.Value)
                    .Select(source => source.SourceRevision)
                    .SingleAsync(token).ConfigureAwait(false);
            },
            cancellationToken);
    }

    public Task<IReadOnlyList<PlaybackSessionDto>> NavigateAsync(
        int windowId,
        string action,
        int? targetIndex,
        long? positionMs,
        CancellationToken cancellationToken = default)
    {
        ValidateWindow(windowId);
        var normalized = action.Trim().ToLowerInvariant();
        if (normalized is not ("next" or "previous" or "first" or "last" or "goto" or "seek"))
        {
            throw new PlaybackServiceException($"无效的导航动作：{action}", "invalid_navigation");
        }

        var commandName = normalized switch
        {
            "next" => "NEXT",
            "previous" => "PREV",
            "first" or "last" or "goto" => "GOTO",
            "seek" => "SEEK",
            _ => normalized.ToUpperInvariant(),
        };
        return EnqueueDisplayAsync(windowId, commandName, "{}", async (database, session, command, token) =>
        {
            if ((normalized is "goto" or "first" or "last") && targetIndex is < 1)
            {
                throw new PlaybackServiceException("target_index 必须大于 0", "invalid_navigation");
            }

            if (normalized == "seek" && positionMs is < 0)
            {
                throw new PlaybackServiceException("position_ms 不能为负数", "invalid_navigation");
            }

            if (session.MediaSourceId is null)
            {
                throw new PlaybackServiceException($"窗口 {windowId} 当前没有打开的媒体源");
            }

            var effectiveTarget = normalized switch
            {
                "first" => 1,
                "last" when session.TotalSlides > 0 => session.TotalSlides,
                _ => targetIndex,
            };
            session.PendingCommand = command.Command;
            session.CommandArgsJson = JsonSerializer.Serialize(new { action = normalized, target_index = targetIndex, position_ms = positionMs });
            command.ArgsJson = session.CommandArgsJson;
            if (normalized is "first" or "last")
            {
                session.CommandArgsJson = JsonSerializer.Serialize(new { action = "goto", target_index = effectiveTarget, position_ms = positionMs });
                command.ArgsJson = session.CommandArgsJson;
            }
            command.SourceGeneration = session.DesiredGeneration;
            command.SourceRevision = await database.MediaSources
                .Where(source => source.Id == session.MediaSourceId.Value)
                .Select(source => source.SourceRevision)
                .SingleAsync(token).ConfigureAwait(false);
        }, cancellationToken);
    }

    public Task<IReadOnlyList<PlaybackSessionDto>> ControlPptMediaAsync(
        int windowId,
        string action,
        string? mediaId,
        int? mediaIndex,
        CancellationToken cancellationToken = default)
    {
        ValidateWindow(windowId);
        var normalized = action.Trim().ToLowerInvariant();
        if (normalized is not ("play" or "pause" or "stop" or "toggle"))
        {
            throw new PlaybackServiceException($"无效的 PPT 媒体动作：{action}", "invalid_media_action");
        }

        return EnqueueDisplayAsync(windowId, "PPT_MEDIA", "{}", async (database, session, command, token) =>
        {
            if (session.MediaSourceId is null)
            {
                throw new PlaybackServiceException($"窗口 {windowId} 当前没有打开的媒体源");
            }

            session.PendingCommand = "PPT_MEDIA";
            session.CommandArgsJson = JsonSerializer.Serialize(new { action = normalized, media_id = mediaId ?? string.Empty, media_index = mediaIndex });
            command.ArgsJson = session.CommandArgsJson;
            command.SourceGeneration = session.DesiredGeneration;
            command.SourceRevision = await database.MediaSources
                .Where(source => source.Id == session.MediaSourceId.Value)
                .Select(source => source.SourceRevision)
                .SingleAsync(token).ConfigureAwait(false);
        }, cancellationToken);
    }

    public Task<IReadOnlyList<PlaybackSessionDto>> ResetPowerPointAsync(CancellationToken cancellationToken = default) =>
        ResetPowerPointQueuedAsync(cancellationToken);

    public Task<IReadOnlyList<PlaybackSessionDto>> CloseAsync(int windowId, CancellationToken cancellationToken = default) =>
        EnqueueDisplayAsync(
            windowId,
            "CLOSE",
            "{}",
            async (database, session, command, token) =>
            {
                var sourceId = session.MediaSourceId;
                var sourceRevision = sourceId is null
                    ? 0
                    : await database.MediaSources.Where(source => source.Id == sourceId.Value)
                        .Select(source => source.SourceRevision).SingleOrDefaultAsync(token).ConfigureAwait(false);
                session.MediaSourceId = null;
                session.PlaybackMode = PlaybackMode.None;
                session.PlaybackState = PlaybackState.Idle;
                session.ErrorMessage = string.Empty;
                session.PendingCommand = command.Command;
                session.CommandArgsJson = JsonSerializer.Serialize(new { source_id = sourceId });
                session.DesiredGeneration = checked(session.DesiredGeneration + 1);
                command.ArgsJson = session.CommandArgsJson;
                command.SourceGeneration = session.DesiredGeneration;
                command.SourceRevision = sourceRevision;
            },
            cancellationToken);

    public Task<IReadOnlyList<PlaybackSessionDto>> SetLoopAsync(
        int windowId,
        bool enabled,
        CancellationToken cancellationToken = default) =>
        EnqueueDisplayAsync(
            windowId,
            "SET_LOOP",
            JsonSerializer.Serialize(new { enabled }),
            (session, command) =>
            {
                session.LoopEnabled = enabled;
                session.PendingCommand = command.Command;
            },
            cancellationToken);

    public Task<IReadOnlyList<PlaybackSessionDto>> SetVolumeAsync(
        int windowId,
        int volume,
        CancellationToken cancellationToken = default)
    {
        if (volume is < 0 or > 100)
        {
            throw new PlaybackServiceException("窗口音量必须在 0 到 100 之间");
        }

        return EnqueueDisplayAsync(
            windowId,
            "SET_VOLUME",
            JsonSerializer.Serialize(new { volume }),
            (session, command) =>
            {
                session.Volume = volume;
                session.PendingCommand = command.Command;
            },
            cancellationToken);
    }

    public Task<IReadOnlyList<PlaybackSessionDto>> SetMuteAsync(
        int windowId,
        bool muted,
        CancellationToken cancellationToken = default) =>
        EnqueueDisplayAsync(
            windowId,
            "SET_MUTE",
            JsonSerializer.Serialize(new { muted }),
            (session, command) =>
            {
                session.IsMuted = muted;
                session.PendingCommand = "SET_MUTE";
            },
            cancellationToken);

    public Task<IReadOnlyList<PlaybackSessionDto>> ResetAllAsync(CancellationToken cancellationToken = default) =>
        ResetAllQueuedAsync(cancellationToken);

    public Task<IReadOnlyList<PlaybackSessionDto>> ShowIdsAsync(CancellationToken cancellationToken = default) =>
        ShowIdsQueuedAsync(cancellationToken);

    public static IReadOnlyList<DisplayTargetDto> ListDisplays() =>
    [
        new DisplayTargetDto
        {
            Index = 0,
            Name = "模拟显示器",
            Width = 1920,
            Height = 1080,
            X = 0,
            Y = 0,
            IsPrimary = true,
        },
    ];

    private Task<IReadOnlyList<PlaybackSessionDto>> EnqueueDisplayAsync(
        int windowId,
        string commandName,
        string initialArgsJson,
        Action<PlaybackSession, CommandRecord> mutation,
        CancellationToken cancellationToken) =>
        EnqueueDisplayAsync(
            windowId,
            commandName,
            initialArgsJson,
            (database, session, command, _) =>
            {
                mutation(session, command);
                return Task.CompletedTask;
            },
            cancellationToken);

    internal async Task<IReadOnlyList<PlaybackSessionDto>> EnqueueDisplayAsync(
        int windowId,
        string commandName,
        string initialArgsJson,
        Func<ControlDbContext, PlaybackSession, CommandRecord, CancellationToken, Task> mutation,
        CancellationToken cancellationToken)
    {
        ValidateWindow(windowId);
        await _commands.EnqueueAsync(
            new EnqueueCommand(CommandTargetKind.Display, windowId, commandName, initialArgsJson, 0, 0),
            async (database, command, token) =>
            {
                var session = await database.PlaybackSessions.SingleAsync(item => item.WindowId == windowId, token).ConfigureAwait(false);
                await mutation(database, session, command, token).ConfigureAwait(false);
                var earlierPending = await database.CommandRecords
                    .Where(item => item.TargetKind == CommandTargetKind.Display && item.TargetId == windowId && item.Status == CommandStatus.Pending)
                    .OrderBy(item => item.TargetSequence)
                    .FirstOrDefaultAsync(token).ConfigureAwait(false);
                if (earlierPending is not null && earlierPending.TargetSequence < command.TargetSequence)
                {
                    session.PendingCommand = earlierPending.Command;
                    session.CommandArgsJson = earlierPending.ArgsJson;
                }
                else
                {
                    session.PendingCommand = command.Command;
                    session.CommandArgsJson = command.ArgsJson;
                }
                session.LastUpdatedAt = NextTimestamp(session.LastUpdatedAt);
            },
            cancellationToken).ConfigureAwait(false);
        return await GetSessionsAsync(cancellationToken).ConfigureAwait(false);
    }

    private async Task<IReadOnlyList<PlaybackSessionDto>> ResetPowerPointQueuedAsync(CancellationToken cancellationToken)
    {
        int[] windows;
        await using (var database = await contextFactory.CreateDbContextAsync(cancellationToken).ConfigureAwait(false))
        {
            windows = await database.PlaybackSessions
                .Where(session => session.PlaybackMode == PlaybackMode.PowerPoint)
                .Select(session => session.WindowId)
                .ToArrayAsync(cancellationToken).ConfigureAwait(false);
        }

        foreach (var windowId in windows)
        {
            await EnqueueDisplayAsync(windowId, "RESET_PPT", "{}", async (database, session, command, token) =>
            {
                var sourceId = session.MediaSourceId;
                var sourceRevision = sourceId is null ? 0 : await database.MediaSources
                    .Where(source => source.Id == sourceId.Value)
                    .Select(source => source.SourceRevision).SingleOrDefaultAsync(token).ConfigureAwait(false);
                session.MediaSourceId = null;
                session.PlaybackMode = PlaybackMode.None;
                session.PlaybackState = PlaybackState.Idle;
                session.ErrorMessage = string.Empty;
                session.PendingCommand = command.Command;
                session.DesiredGeneration = checked(session.DesiredGeneration + 1);
                session.CommandArgsJson = JsonSerializer.Serialize(new { source_id = sourceId });
                command.ArgsJson = session.CommandArgsJson;
                command.SourceGeneration = session.DesiredGeneration;
                command.SourceRevision = sourceRevision;
            }, cancellationToken).ConfigureAwait(false);
        }

        return await GetSessionsAsync(cancellationToken).ConfigureAwait(false);
    }

    private async Task<IReadOnlyList<PlaybackSessionDto>> ResetAllQueuedAsync(CancellationToken cancellationToken)
    {
        for (var windowId = 1; windowId <= 4; windowId++)
        {
            await CloseAsync(windowId, cancellationToken).ConfigureAwait(false);
        }

        return await GetSessionsAsync(cancellationToken).ConfigureAwait(false);
    }

    private async Task<IReadOnlyList<PlaybackSessionDto>> ShowIdsQueuedAsync(CancellationToken cancellationToken)
    {
        for (var windowId = 1; windowId <= 4; windowId++)
        {
            await EnqueueDisplayAsync(windowId, "SHOW_ID", "{}", (session, command) =>
            {
                session.PendingCommand = command.Command;
            }, cancellationToken).ConfigureAwait(false);
        }

        return await GetSessionsAsync(cancellationToken).ConfigureAwait(false);
    }

    private Task<IReadOnlyList<PlaybackSessionDto>> MutateSessionAsync(
        int windowId,
        Action<PlaybackSession> mutation,
        CancellationToken cancellationToken)
    {
        ValidateWindow(windowId);
        return writes.ExecuteAsync(
            async (database, token) =>
            {
                var session = await database.PlaybackSessions.SingleAsync(
                    item => item.WindowId == windowId,
                    token).ConfigureAwait(false);
                mutation(session);
                session.LastUpdatedAt = NextTimestamp(session.LastUpdatedAt);
                return await LoadSessionsAsync(database, token).ConfigureAwait(false);
            },
            cancellationToken);
    }

    private async Task<IReadOnlyList<PlaybackSessionDto>> LoadSessionsAsync(
        ControlDbContext database,
        CancellationToken cancellationToken)
    {
        await database.SaveChangesAsync(cancellationToken).ConfigureAwait(false);
        var sessions = await database.PlaybackSessions.Include(session => session.MediaSource)
            .OrderBy(session => session.WindowId)
            .ToListAsync(cancellationToken).ConfigureAwait(false);
        return sessions.Select(session => ToSessionDto(session, _timeProvider.GetUtcNow())).ToArray();
    }

    private DateTimeOffset NextTimestamp(DateTimeOffset previous)
    {
        var now = _timeProvider.GetUtcNow();
        return now.ToUnixTimeMilliseconds() > previous.ToUnixTimeMilliseconds()
            ? now
            : previous.AddMilliseconds(1);
    }

    public static PlaybackSessionDto ToSessionDto(PlaybackSession session, DateTimeOffset now)
    {
        var source = session.MediaSource;
        var sourceType = source is null ? string.Empty : MediaSourceService.SourceTypeName(source.SourceType);
        return new PlaybackSessionDto
        {
            WindowId = session.WindowId,
            SessionId = session.Id,
            SourceId = session.MediaSourceId,
            SourceName = source?.Name ?? "无",
            SourceType = sourceType,
            SourceTypeLabel = source is null ? "无" : SourceTypeLabel(source.SourceType),
            SourceUri = source?.Uri ?? string.Empty,
            PlaybackMode = sourceType == "ppt" ? PlaybackModeName(session.PlaybackMode) : string.Empty,
            PlaybackState = EnumName(session.PlaybackState),
            PlaybackStateLabel = PlaybackStateLabel(session.PlaybackState),
            ErrorMessage = session.ErrorMessage,
            DisplayMode = "single",
            DisplayModeLabel = "单屏",
            TargetDisplayLabel = session.TargetDisplayLabel.Length == 0 ? "未选择" : session.TargetDisplayLabel,
            CurrentSlide = session.CurrentSlide,
            TotalSlides = session.TotalSlides,
            PositionMs = session.PositionMs,
            DurationMs = session.DurationMs,
            PendingCommand = session.PendingCommand,
            PlayerOnline = session.PlayerLastSeenAt is not null && now - session.PlayerLastSeenAt.Value <= TimeSpan.FromSeconds(5),
            PlayerLastSeenAt = session.PlayerLastSeenAt?.ToString("O") ?? string.Empty,
            LastUpdatedAt = session.LastUpdatedAt.ToString("O"),
            Volume = session.Volume,
            IsMuted = session.IsMuted,
            LoopEnabled = session.LoopEnabled,
        };
    }

    private static RuntimeStateDto ToRuntimeDto(RuntimeState runtime) => new()
    {
        BigScreenMode = EnumName(runtime.BigScreenMode),
        VolumeLevel = runtime.VolumeLevel,
        MutedWindows = MutedWindows(runtime.BigScreenMode),
    };

    private static SystemVolumeDto ToVolumeDto(RuntimeState runtime) => new()
    {
        Level = runtime.VolumeLevel,
        Muted = runtime.VolumeMuted,
        SystemSynced = false,
        Backend = "runtime_state",
    };

    private static IReadOnlyList<int> MutedWindows(BigScreenMode mode) =>
        mode == BigScreenMode.Single ? [2, 3, 4] : [3, 4];

    private static void ValidateWindow(int windowId)
    {
        if (!Windows.Contains(windowId))
        {
            throw new PlaybackServiceException($"无效的窗口编号：{windowId}，有效范围 1-4", "invalid_window");
        }
    }

    private static string EnumName<T>(T value) where T : struct, Enum => value.ToString().ToLowerInvariant();

    private static string PlaybackModeName(PlaybackMode mode) => mode switch
    {
        PlaybackMode.PowerPoint => "powerpoint",
        PlaybackMode.Pdf => "pdf",
        _ => string.Empty,
    };

    private static string SourceTypeName(MediaSourceType type) => type switch
    {
        MediaSourceType.Presentation => "ppt",
        MediaSourceType.CustomStream => "custom_stream",
        MediaSourceType.RtspStream => "rtsp",
        MediaSourceType.SrtStream => "srt",
        _ => type.ToString().ToLowerInvariant(),
    };

    private static string PlaybackStateLabel(PlaybackState state) => state switch
    {
        PlaybackState.Idle => "待机",
        PlaybackState.Loading => "加载中",
        PlaybackState.Playing => "播放中",
        PlaybackState.Paused => "已暂停",
        PlaybackState.Stopped => "已停止",
        PlaybackState.Error => "错误",
        _ => string.Empty,
    };

    private static string SourceTypeLabel(MediaSourceType type) => type switch
    {
        MediaSourceType.Presentation => "演示文稿",
        MediaSourceType.Video => "视频",
        MediaSourceType.Audio => "音频",
        MediaSourceType.Image => "图片",
        MediaSourceType.Web => "网页",
        MediaSourceType.CustomStream => "自定义流",
        MediaSourceType.RtspStream => "RTSP 流",
        MediaSourceType.SrtStream => "SRT 流",
        _ => string.Empty,
    };
}

public sealed record SystemVolumeDto
{
    [JsonPropertyName("level")]
    public int Level { get; init; }

    [JsonPropertyName("muted")]
    public bool Muted { get; init; }

    [JsonPropertyName("system_synced")]
    public bool SystemSynced { get; init; }

    [JsonPropertyName("backend")]
    public string Backend { get; init; } = string.Empty;
}

public sealed class PlaybackServiceException(string message, string code = "playback_error") : Exception(message)
{
    public string Code { get; } = code;
}
