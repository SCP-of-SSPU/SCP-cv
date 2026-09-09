using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using ScpCv.Contracts.Http;
using ScpCv.Domain.Model;
using ScpCv.Infrastructure.Persistence;
using ScpCv.Infrastructure.Playback;
using ScpCv.Infrastructure.Commands;

namespace ScpCv.Infrastructure.Scenarios;

public sealed class ScenarioService(
    IDbContextFactory<ControlDbContext> contextFactory,
    WriteCoordinator writes,
    CommandCoordinator commands,
    TimeProvider? timeProvider = null)
{
    private readonly TimeProvider _timeProvider = timeProvider ?? TimeProvider.System;
    private readonly CommandCoordinator _commands = commands;

    public async Task<IReadOnlyList<ScenarioDto>> ListAsync(CancellationToken cancellationToken = default)
    {
        await using var database = await contextFactory.CreateDbContextAsync(cancellationToken).ConfigureAwait(false);
        var scenarios = await database.Scenarios.AsNoTracking()
            .OrderByDescending(scenario => scenario.SortOrder)
            .ThenByDescending(scenario => scenario.UpdatedAt)
            .ToListAsync(cancellationToken).ConfigureAwait(false);
        return await MapAsync(database, scenarios, cancellationToken).ConfigureAwait(false);
    }

    public async Task<ScenarioDto> GetAsync(long scenarioId, CancellationToken cancellationToken = default)
    {
        await using var database = await contextFactory.CreateDbContextAsync(cancellationToken).ConfigureAwait(false);
        var scenario = await database.Scenarios.AsNoTracking().SingleOrDefaultAsync(
                item => item.Id == scenarioId,
                cancellationToken).ConfigureAwait(false)
            ?? throw new ScenarioServiceException($"预案 id={scenarioId} 不存在", isNotFound: true);
        return (await MapAsync(database, [scenario], cancellationToken).ConfigureAwait(false))[0];
    }

    public Task<ScenarioDto> CreateAsync(
        ScenarioWriteModel model,
        CancellationToken cancellationToken = default) =>
        writes.ExecuteAsync(
            async (database, token) =>
            {
                var now = _timeProvider.GetUtcNow();
                var scenario = new Scenario
                {
                    Name = ValidateName(model.Name),
                    Description = model.Description.Trim(),
                    BigScreenModeState = ParseValueState(model.BigScreenModeState),
                    BigScreenMode = ParseBigScreenMode(model.BigScreenMode),
                    VolumeState = ParseValueState(model.VolumeState),
                    VolumeLevel = ValidateVolume(model.VolumeLevel),
                    TargetsJson = await NormalizeTargetsJsonAsync(database, model.Targets, token).ConfigureAwait(false),
                    CreatedAt = now,
                    UpdatedAt = now,
                };
                database.Scenarios.Add(scenario);
                await database.SaveChangesAsync(token).ConfigureAwait(false);
                return (await MapAsync(database, [scenario], token).ConfigureAwait(false))[0];
            },
            cancellationToken);

    public Task<ScenarioDto> UpdateAsync(
        long scenarioId,
        ScenarioPatchModel model,
        CancellationToken cancellationToken = default) =>
        writes.ExecuteAsync(
            async (database, token) =>
            {
                var scenario = await database.Scenarios.SingleOrDefaultAsync(
                        item => item.Id == scenarioId,
                        token).ConfigureAwait(false)
                    ?? throw new ScenarioServiceException($"预案 id={scenarioId} 不存在", isNotFound: true);
                if (model.Name is not null) scenario.Name = ValidateName(model.Name);
                if (model.Description is not null) scenario.Description = model.Description.Trim();
                if (model.BigScreenModeState is not null) scenario.BigScreenModeState = ParseValueState(model.BigScreenModeState);
                if (model.BigScreenMode is not null) scenario.BigScreenMode = ParseBigScreenMode(model.BigScreenMode);
                if (model.VolumeState is not null) scenario.VolumeState = ParseValueState(model.VolumeState);
                if (model.VolumeLevel is not null) scenario.VolumeLevel = ValidateVolume(model.VolumeLevel.Value);
                if (model.Targets is not null)
                {
                    scenario.TargetsJson = await NormalizeTargetsJsonAsync(database, model.Targets, token).ConfigureAwait(false);
                }

                scenario.UpdatedAt = NextTimestamp(scenario.UpdatedAt);
                await database.SaveChangesAsync(token).ConfigureAwait(false);
                return (await MapAsync(database, [scenario], token).ConfigureAwait(false))[0];
            },
            cancellationToken);

    public Task DeleteAsync(long scenarioId, CancellationToken cancellationToken = default) =>
        writes.ExecuteAsync(
            async (database, token) =>
            {
                var scenario = await database.Scenarios.SingleOrDefaultAsync(
                        item => item.Id == scenarioId,
                        token).ConfigureAwait(false)
                    ?? throw new ScenarioServiceException($"预案 id={scenarioId} 不存在", isNotFound: true);
                database.Scenarios.Remove(scenario);
            },
            cancellationToken);

    public Task<ScenarioDto> TogglePinAsync(long scenarioId, CancellationToken cancellationToken = default) =>
        writes.ExecuteAsync(
            async (database, token) =>
            {
                var scenario = await database.Scenarios.SingleOrDefaultAsync(
                        item => item.Id == scenarioId,
                        token).ConfigureAwait(false)
                    ?? throw new ScenarioServiceException($"预案 id={scenarioId} 不存在", isNotFound: true);
                scenario.SortOrder = scenario.SortOrder > 0
                    ? 0
                    : checked((await database.Scenarios.MaxAsync(item => (int?)item.SortOrder, token).ConfigureAwait(false) ?? 0) + 1);
                scenario.UpdatedAt = NextTimestamp(scenario.UpdatedAt);
                await database.SaveChangesAsync(token).ConfigureAwait(false);
                return (await MapAsync(database, [scenario], token).ConfigureAwait(false))[0];
            },
            cancellationToken);

    public Task<ScenarioDto> CaptureAsync(
        string name,
        string description,
        long? scenarioId,
        CancellationToken cancellationToken = default) =>
        writes.ExecuteAsync(
            async (database, token) =>
            {
                var runtime = await database.RuntimeStates.SingleAsync(token).ConfigureAwait(false);
                var sessions = await database.PlaybackSessions.OrderBy(item => item.WindowId).ToListAsync(token).ConfigureAwait(false);
                var targets = sessions.Select(session => new ScenarioTargetDto
                {
                    WindowId = session.WindowId,
                    SourceState = session.MediaSourceId is null ? "empty" : "set",
                    SourceId = session.MediaSourceId,
                    Autoplay = session.PlaybackState is PlaybackState.Loading or PlaybackState.Playing,
                    Resume = true,
                }).ToArray();
                Scenario scenario;
                if (scenarioId is > 0)
                {
                    scenario = await database.Scenarios.SingleOrDefaultAsync(
                            item => item.Id == scenarioId.Value,
                            token).ConfigureAwait(false)
                        ?? throw new ScenarioServiceException($"预案 id={scenarioId.Value} 不存在", isNotFound: true);
                }
                else
                {
                    scenario = new Scenario { CreatedAt = _timeProvider.GetUtcNow() };
                    database.Scenarios.Add(scenario);
                }

                scenario.Name = ValidateName(name);
                scenario.Description = description.Trim();
                scenario.BigScreenModeState = ScenarioValueState.Set;
                scenario.BigScreenMode = runtime.BigScreenMode;
                scenario.VolumeState = ScenarioValueState.Set;
                scenario.VolumeLevel = runtime.VolumeLevel;
                scenario.TargetsJson = JsonSerializer.Serialize(targets);
                scenario.UpdatedAt = NextTimestamp(scenario.UpdatedAt);
                await database.SaveChangesAsync(token).ConfigureAwait(false);
                return (await MapAsync(database, [scenario], token).ConfigureAwait(false))[0];
            },
            cancellationToken);

    public async Task<IReadOnlyList<PlaybackSessionDto>> ActivateAsync(
        long scenarioId,
        CancellationToken cancellationToken = default)
    {
        Scenario scenario;
        await using (var database = await contextFactory.CreateDbContextAsync(cancellationToken).ConfigureAwait(false))
        {
            scenario = await database.Scenarios.AsNoTracking().SingleOrDefaultAsync(item => item.Id == scenarioId, cancellationToken).ConfigureAwait(false)
                ?? throw new ScenarioServiceException($"预案 id={scenarioId} 不存在", isNotFound: true);
        }

        await writes.ExecuteAsync(async (database, token) =>
        {
            var runtime = await database.RuntimeStates.SingleAsync(token).ConfigureAwait(false);
            var sessions = await database.PlaybackSessions.ToListAsync(token).ConfigureAwait(false);
            var runtimeChanged = false;
            if (scenario.BigScreenModeState == ScenarioValueState.Set)
            {
                runtime.BigScreenMode = scenario.BigScreenMode;
                var mutedWindows = scenario.BigScreenMode == BigScreenMode.Single ? new HashSet<int> { 2, 3, 4 } : new HashSet<int> { 3, 4 };
                foreach (var session in sessions) session.IsMuted = mutedWindows.Contains(session.WindowId);
                runtimeChanged = true;
            }
            if (scenario.VolumeState == ScenarioValueState.Set)
            {
                runtime.VolumeLevel = scenario.VolumeLevel;
                runtimeChanged = true;
            }
            if (runtimeChanged) runtime.UpdatedAt = _timeProvider.GetUtcNow();
        }, cancellationToken).ConfigureAwait(false);

        var targets = DeserializeTargets(scenario.TargetsJson);
        await using var snapshotDb = await contextFactory.CreateDbContextAsync(cancellationToken).ConfigureAwait(false);
        var snapshot = await snapshotDb.PlaybackSessions.AsNoTracking().ToDictionaryAsync(item => item.WindowId, cancellationToken).ConfigureAwait(false);
        foreach (var target in targets)
        {
            if (target.WindowId is < 1 or > 4 || target.SourceState == "unset" || !snapshot.TryGetValue(target.WindowId, out var session)) continue;
            if (target.SourceState == "empty")
            {
                await EnqueueDisplayCommandAsync(target.WindowId, "CLOSE", "{}", async (database, current, command, token) =>
                {
                    var sourceId = current.MediaSourceId;
                    var revision = sourceId is null ? 0 : await database.MediaSources.Where(source => source.Id == sourceId.Value).Select(source => source.SourceRevision).SingleOrDefaultAsync(token).ConfigureAwait(false);
                    current.MediaSourceId = null;
                    current.PlaybackMode = PlaybackMode.None;
                    current.PlaybackState = PlaybackState.Idle;
                    current.ErrorMessage = string.Empty;
                    current.DesiredGeneration = checked(current.DesiredGeneration + 1);
                    current.CommandArgsJson = JsonSerializer.Serialize(new { source_id = sourceId });
                    command.ArgsJson = current.CommandArgsJson;
                    command.SourceGeneration = current.DesiredGeneration;
                    command.SourceRevision = revision;
                }, cancellationToken).ConfigureAwait(false);
            }
            else if (target.SourceState == "set" && target.SourceId is > 0)
            {
                if (target.Resume && session.MediaSourceId == target.SourceId && session.PlaybackState is PlaybackState.Loading or PlaybackState.Playing or PlaybackState.Paused) continue;
                var sourceId = target.SourceId.Value;
                await EnqueueDisplayCommandAsync(target.WindowId, "OPEN", "{}", async (database, current, command, token) =>
                {
                    var source = await database.MediaSources.SingleOrDefaultAsync(item => item.Id == sourceId, token).ConfigureAwait(false)
                        ?? throw new ScenarioServiceException($"媒体源 id={sourceId} 不存在");
                    current.MediaSourceId = sourceId;
                    current.PlaybackMode = PlaybackMode.None;
                    current.PlaybackState = PlaybackState.Loading;
                    current.ErrorMessage = string.Empty;
                    current.CurrentSlide = 0;
                    current.DesiredGeneration = checked(current.DesiredGeneration + 1);
                    current.CommandArgsJson = JsonSerializer.Serialize(new
                    {
                        source_id = sourceId,
                        source_type = SourceTypeName(source.SourceType),
                        uri = source.Uri,
                        autoplay = target.Autoplay,
                        target_slide = 0,
                    });
                    command.ArgsJson = current.CommandArgsJson;
                    command.SourceGeneration = current.DesiredGeneration;
                    command.SourceRevision = source.SourceRevision;
                }, cancellationToken).ConfigureAwait(false);
            }
        }

        return await LoadSessionsAsync(cancellationToken).ConfigureAwait(false);
    }

    private async Task EnqueueDisplayCommandAsync(
        int windowId,
        string commandName,
        string argsJson,
        Func<ControlDbContext, PlaybackSession, CommandRecord, CancellationToken, Task> mutation,
        CancellationToken cancellationToken)
    {
        await _commands.EnqueueAsync(
            new EnqueueCommand(CommandTargetKind.Display, windowId, commandName, argsJson, 0, 0),
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
    }

    private async Task<IReadOnlyList<PlaybackSessionDto>> LoadSessionsAsync(CancellationToken cancellationToken)
    {
        await using var database = await contextFactory.CreateDbContextAsync(cancellationToken).ConfigureAwait(false);
        var sessions = await database.PlaybackSessions.AsNoTracking().Include(session => session.MediaSource)
            .OrderBy(session => session.WindowId).ToListAsync(cancellationToken).ConfigureAwait(false);
        return sessions.Select(item => RuntimeStateService.ToSessionDto(item, _timeProvider.GetUtcNow())).ToArray();
    }

    private static string SourceTypeName(MediaSourceType type) => type switch
    {
        MediaSourceType.Presentation => "ppt",
        MediaSourceType.CustomStream => "custom_stream",
        MediaSourceType.RtspStream => "rtsp",
        MediaSourceType.SrtStream => "srt",
        _ => type.ToString().ToLowerInvariant(),
    };

    private static async Task<IReadOnlyList<ScenarioDto>> MapAsync(
        ControlDbContext database,
        IReadOnlyList<Scenario> scenarios,
        CancellationToken cancellationToken)
    {
        var sourceNames = await database.MediaSources.AsNoTracking().ToDictionaryAsync(
            source => source.Id,
            source => source.Name,
            cancellationToken).ConfigureAwait(false);
        return scenarios.Select(scenario => ToDto(scenario, sourceNames)).ToArray();
    }

    private static ScenarioDto ToDto(Scenario scenario, Dictionary<long, string> sourceNames)
    {
        var targets = DeserializeTargets(scenario.TargetsJson).Select(target => target with
        {
            SourceName = target.SourceId is { } id && sourceNames.TryGetValue(id, out var name) ? name : string.Empty,
        }).ToArray();
        var first = targets.FirstOrDefault(target => target.WindowId == 1) ?? new ScenarioTargetDto { WindowId = 1 };
        var second = targets.FirstOrDefault(target => target.WindowId == 2) ?? new ScenarioTargetDto { WindowId = 2 };
        return new ScenarioDto
        {
            Id = scenario.Id,
            Name = scenario.Name,
            Description = scenario.Description,
            SortOrder = scenario.SortOrder,
            BigScreenModeState = EnumName(scenario.BigScreenModeState),
            BigScreenMode = EnumName(scenario.BigScreenMode),
            BigScreenModeLabel = scenario.BigScreenModeState == ScenarioValueState.Set ? (scenario.BigScreenMode == BigScreenMode.Single ? "单屏" : "双屏") : string.Empty,
            VolumeState = EnumName(scenario.VolumeState),
            VolumeLevel = scenario.VolumeLevel,
            Targets = targets,
            Window1SourceId = first.SourceId,
            Window1SourceName = first.SourceName,
            Window1Autoplay = first.Autoplay,
            Window1Resume = first.Resume,
            Window2SourceId = second.SourceId,
            Window2SourceName = second.SourceName,
            Window2Autoplay = second.Autoplay,
            Window2Resume = second.Resume,
            CreatedAt = scenario.CreatedAt.ToString("O"),
            UpdatedAt = scenario.UpdatedAt.ToString("O"),
        };
    }

    private static async Task<string> NormalizeTargetsJsonAsync(
        ControlDbContext database,
        IReadOnlyList<ScenarioTargetDto> targets,
        CancellationToken cancellationToken)
    {
        var normalized = new List<ScenarioTargetDto>();
        var seen = new HashSet<int>();
        foreach (var target in targets)
        {
            if (target.WindowId is < 1 or > 4 || !seen.Add(target.WindowId)) continue;
            var state = target.SourceState.Trim().ToLowerInvariant();
            if (state is not ("unset" or "empty" or "set")) throw new ScenarioServiceException($"无效的目标状态：{state}");
            long? sourceId = null;
            if (state == "set" && target.SourceId is > 0)
            {
                if (!await database.MediaSources.AnyAsync(source => source.Id == target.SourceId.Value, cancellationToken).ConfigureAwait(false))
                    throw new ScenarioServiceException($"媒体源 id={target.SourceId.Value} 不存在");
                sourceId = target.SourceId;
            }
            normalized.Add(target with { SourceState = state, SourceId = sourceId, SourceName = string.Empty });
        }
        return JsonSerializer.Serialize(normalized);
    }

    private static ScenarioTargetDto[] DeserializeTargets(string json)
    {
        try { return JsonSerializer.Deserialize<ScenarioTargetDto[]>(json) ?? []; }
        catch (JsonException) { return []; }
    }

    private DateTimeOffset NextTimestamp(DateTimeOffset previous)
    {
        var now = _timeProvider.GetUtcNow();
        return now.ToUnixTimeMilliseconds() > previous.ToUnixTimeMilliseconds() ? now : previous.AddMilliseconds(1);
    }
    private static string ValidateName(string value) => value.Trim().Length > 0 ? value.Trim() : throw new ScenarioServiceException("预案名称不能为空");
    private static int ValidateVolume(int value) => value is >= 0 and <= 100 ? value : throw new ScenarioServiceException("音量必须在 0 到 100 之间");
    private static ScenarioValueState ParseValueState(string value) => value.Trim().ToLowerInvariant() switch { "unset" => ScenarioValueState.Unset, "empty" => ScenarioValueState.Empty, "set" => ScenarioValueState.Set, _ => throw new ScenarioServiceException($"无效的三态值：{value}") };
    private static BigScreenMode ParseBigScreenMode(string value) => value.Trim().ToLowerInvariant() switch { "single" => BigScreenMode.Single, "double" => BigScreenMode.Double, _ => throw new ScenarioServiceException($"无效的大屏模式：{value}") };
    private static string EnumName<T>(T value) where T : struct, Enum => value.ToString().ToLowerInvariant();
}

public sealed record ScenarioWriteModel(string Name, string Description, string BigScreenModeState, string BigScreenMode, string VolumeState, int VolumeLevel, IReadOnlyList<ScenarioTargetDto> Targets);
public sealed record ScenarioPatchModel(string? Name, string? Description, string? BigScreenModeState, string? BigScreenMode, string? VolumeState, int? VolumeLevel, IReadOnlyList<ScenarioTargetDto>? Targets);
public sealed class ScenarioServiceException(string message, bool isNotFound = false) : Exception(message) { public bool IsNotFound { get; } = isNotFound; }
