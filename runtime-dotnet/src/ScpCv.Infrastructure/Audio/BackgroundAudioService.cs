using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using ScpCv.Contracts.Http;
using ScpCv.Domain.Model;
using ScpCv.Infrastructure.Media;
using ScpCv.Infrastructure.Persistence;
using ScpCv.Domain.Rules;

namespace ScpCv.Infrastructure.Audio;

public sealed class BackgroundAudioService(
    IDbContextFactory<ControlDbContext> contextFactory,
    WriteCoordinator writes,
    TimeProvider? timeProvider = null)
{
    private readonly TimeProvider _timeProvider = timeProvider ?? TimeProvider.System;
    private long _sourceGeneration;
    private readonly HashSet<Guid> _finishedEvents = [];
    private readonly object _finishedGate = new();

    public async Task<BackgroundAudioDto> GetAsync(CancellationToken cancellationToken = default)
    {
        await using var database = await contextFactory.CreateDbContextAsync(cancellationToken).ConfigureAwait(false);
        return await LoadAsync(database, cancellationToken).ConfigureAwait(false);
    }

    public Task<BackgroundAudioDto> PlaySourceAsync(
        long sourceId,
        CancellationToken cancellationToken = default)
    {
        if (sourceId <= 0)
        {
            throw new BackgroundAudioServiceException("source_id 必须大于 0", "invalid_source");
        }

        return writes.ExecuteAsync(
            async (database, token) =>
            {
                var source = await database.MediaSources.SingleOrDefaultAsync(
                        item => item.Id == sourceId,
                        token).ConfigureAwait(false)
                    ?? throw new BackgroundAudioServiceException($"媒体源 id={sourceId} 不存在");
                if (source.SourceType != MediaSourceType.Audio)
                {
                    throw new BackgroundAudioServiceException("背景音频仅支持 audio 类型媒体源");
                }

                var existing = await database.BackgroundAudioPlaylistItems.SingleOrDefaultAsync(
                    item => item.SourceId == sourceId,
                    token).ConfigureAwait(false);
                if (existing is null)
                {
                    var nextOrder = checked((await database.BackgroundAudioPlaylistItems
                        .MaxAsync(item => (int?)item.SortOrder, token).ConfigureAwait(false) ?? 0) + 10);
                    database.BackgroundAudioPlaylistItems.Add(new BackgroundAudioPlaylistItem
                    {
                        SourceId = sourceId,
                        SortOrder = nextOrder,
                        CreatedAt = _timeProvider.GetUtcNow(),
                    });
                }

                var state = await database.BackgroundAudioStates.SingleAsync(token).ConfigureAwait(false);
                state.CurrentSourceId = sourceId;
                state.PlaybackState = PlaybackState.Loading;
                state.ErrorMessage = string.Empty;
                state.PositionMs = 0;
                state.DurationMs = 0;
                state.PendingCommand = "OPEN";
                Interlocked.Increment(ref _sourceGeneration);
                state.CommandArgsJson = JsonSerializer.Serialize(new
                {
                    source_id = sourceId,
                    uri = source.Uri,
                    autoplay = true,
                    volume = state.Volume,
                    muted = state.IsMuted,
                });
                state.UpdatedAt = NextTimestamp(state.UpdatedAt);
                await database.SaveChangesAsync(token).ConfigureAwait(false);
                return await LoadAsync(database, token).ConfigureAwait(false);
            },
            cancellationToken);
    }

    public Task<BackgroundAudioDto> AddToPlaylistAsync(
        long sourceId,
        CancellationToken cancellationToken = default) =>
        writes.ExecuteAsync(async (database, token) =>
        {
            var source = await database.MediaSources.SingleOrDefaultAsync(
                    item => item.Id == sourceId,
                    token).ConfigureAwait(false)
                ?? throw new BackgroundAudioServiceException($"媒体源 id={sourceId} 不存在");
            if (source.SourceType != MediaSourceType.Audio)
            {
                throw new BackgroundAudioServiceException("背景音频仅支持 audio 类型媒体源");
            }

            var existing = await database.BackgroundAudioPlaylistItems.SingleOrDefaultAsync(
                item => item.SourceId == sourceId,
                token).ConfigureAwait(false);
            if (existing is null)
            {
                var nextOrder = checked((await database.BackgroundAudioPlaylistItems
                    .MaxAsync(item => (int?)item.SortOrder, token).ConfigureAwait(false) ?? 0) + 10);
                database.BackgroundAudioPlaylistItems.Add(new BackgroundAudioPlaylistItem
                {
                    SourceId = sourceId,
                    SortOrder = nextOrder,
                    CreatedAt = _timeProvider.GetUtcNow(),
                });
                await database.SaveChangesAsync(token).ConfigureAwait(false);
            }

            return await LoadAsync(database, token).ConfigureAwait(false);
        }, cancellationToken);

    public Task<BackgroundAudioDto> ClearPlaylistAsync(CancellationToken cancellationToken = default) =>
        writes.ExecuteAsync(async (database, token) =>
        {
            database.BackgroundAudioPlaylistItems.RemoveRange(
                await database.BackgroundAudioPlaylistItems.ToListAsync(token).ConfigureAwait(false));
            var state = await database.BackgroundAudioStates.SingleAsync(token).ConfigureAwait(false);
            state.CurrentSourceId = null;
            state.PlaybackState = PlaybackState.Idle;
            state.PendingCommand = "STOP";
            state.UpdatedAt = NextTimestamp(state.UpdatedAt);
            await database.SaveChangesAsync(token).ConfigureAwait(false);
            return await LoadAsync(database, token).ConfigureAwait(false);
        }, cancellationToken);

    public async Task<BackgroundAudioDto> PlayPlaylistItemAsync(
        long itemId,
        CancellationToken cancellationToken = default)
    {
        await using var database = await contextFactory.CreateDbContextAsync(cancellationToken).ConfigureAwait(false);
        var sourceId = await database.BackgroundAudioPlaylistItems
            .Where(item => item.Id == itemId)
            .Select(item => (long?)item.SourceId)
            .SingleOrDefaultAsync(cancellationToken).ConfigureAwait(false)
            ?? throw new BackgroundAudioServiceException($"背景音乐列表项 id={itemId} 不存在", "not_found");
        return await PlaySourceAsync(sourceId, cancellationToken).ConfigureAwait(false);
    }

    public Task<BackgroundAudioDto> SetPlaylistAsync(IReadOnlyList<long> sourceIds, CancellationToken cancellationToken = default) =>
        writes.ExecuteAsync(async (database, token) =>
        {
            var valid = await database.MediaSources.Where(source => sourceIds.Contains(source.Id) && source.SourceType == MediaSourceType.Audio)
                .ToDictionaryAsync(source => source.Id, token).ConfigureAwait(false);
            if (valid.Count != sourceIds.Distinct().Count()) throw new BackgroundAudioServiceException("播放列表包含不存在或非音频源", "invalid_playlist");
            var state = await database.BackgroundAudioStates.SingleAsync(token).ConfigureAwait(false);
            database.BackgroundAudioPlaylistItems.RemoveRange(await database.BackgroundAudioPlaylistItems.ToListAsync(token).ConfigureAwait(false));
            var order = 10;
            foreach (var id in sourceIds.Distinct()) database.BackgroundAudioPlaylistItems.Add(new BackgroundAudioPlaylistItem { SourceId = id, SortOrder = order, CreatedAt = _timeProvider.GetUtcNow() });
            state.UpdatedAt = NextTimestamp(state.UpdatedAt);
            await database.SaveChangesAsync(token).ConfigureAwait(false);
            return await LoadAsync(database, token).ConfigureAwait(false);
        }, cancellationToken);

    public Task<BackgroundAudioDto> RemoveFromPlaylistAsync(long sourceId, CancellationToken cancellationToken = default) =>
        writes.ExecuteAsync(async (database, token) =>
        {
            var item = await database.BackgroundAudioPlaylistItems.SingleOrDefaultAsync(candidate => candidate.SourceId == sourceId, token).ConfigureAwait(false);
            if (item is not null) database.BackgroundAudioPlaylistItems.Remove(item);
            var state = await database.BackgroundAudioStates.SingleAsync(token).ConfigureAwait(false);
            if (state.CurrentSourceId == sourceId) { state.CurrentSourceId = null; state.PlaybackState = PlaybackState.Idle; state.PendingCommand = "STOP"; }
            state.UpdatedAt = NextTimestamp(state.UpdatedAt);
            await database.SaveChangesAsync(token).ConfigureAwait(false);
            return await LoadAsync(database, token).ConfigureAwait(false);
        }, cancellationToken);

    public Task<BackgroundAudioDto> RemovePlaylistItemAsync(long itemId, CancellationToken cancellationToken = default) =>
        writes.ExecuteAsync(async (database, token) =>
        {
            var item = await database.BackgroundAudioPlaylistItems.SingleOrDefaultAsync(
                candidate => candidate.Id == itemId,
                token).ConfigureAwait(false)
                ?? throw new BackgroundAudioServiceException($"背景音乐列表项 id={itemId} 不存在", "not_found");
            database.BackgroundAudioPlaylistItems.Remove(item);
            var state = await database.BackgroundAudioStates.SingleAsync(token).ConfigureAwait(false);
            if (state.CurrentSourceId == item.SourceId)
            {
                state.CurrentSourceId = null;
                state.PlaybackState = PlaybackState.Idle;
                state.PendingCommand = "STOP";
            }

            state.UpdatedAt = NextTimestamp(state.UpdatedAt);
            await database.SaveChangesAsync(token).ConfigureAwait(false);
            return await LoadAsync(database, token).ConfigureAwait(false);
        }, cancellationToken);

    public Task<BackgroundAudioDto> AdvanceAsync(bool previous = false, CancellationToken cancellationToken = default) =>
        writes.ExecuteAsync(async (database, token) =>
        {
            var items = await database.BackgroundAudioPlaylistItems.Include(item => item.Source).OrderBy(item => item.SortOrder).ThenBy(item => item.Id).ToListAsync(token).ConfigureAwait(false);
            var state = await database.BackgroundAudioStates.SingleAsync(token).ConfigureAwait(false);
            if (items.Count > 0)
            {
                var index = items.FindIndex(item => item.SourceId == state.CurrentSourceId);
                index = previous ? (index <= 0 ? items.Count - 1 : index - 1) : (index + 1) % items.Count;
                state.CurrentSourceId = items[index].SourceId;
                state.PlaybackState = PlaybackState.Loading;
                state.PendingCommand = "OPEN";
                state.CommandArgsJson = JsonSerializer.Serialize(new { source_id = state.CurrentSourceId, autoplay = true });
                Interlocked.Increment(ref _sourceGeneration);
            }
            state.UpdatedAt = NextTimestamp(state.UpdatedAt);
            await database.SaveChangesAsync(token).ConfigureAwait(false);
            return await LoadAsync(database, token).ConfigureAwait(false);
        }, cancellationToken);

    public long CurrentGeneration => Volatile.Read(ref _sourceGeneration);

    public Task<BackgroundAudioDto> ControlAsync(string action, CancellationToken cancellationToken = default) =>
        action.Trim().ToLowerInvariant() switch
        {
            "next" => AdvanceAsync(false, cancellationToken),
            "previous" or "prev" => AdvanceAsync(true, cancellationToken),
            "stop" => writes.ExecuteAsync(async (database, token) => { var state = await database.BackgroundAudioStates.SingleAsync(token).ConfigureAwait(false); state.PlaybackState = PlaybackState.Stopped; state.PendingCommand = "STOP"; await database.SaveChangesAsync(token).ConfigureAwait(false); return await LoadAsync(database, token).ConfigureAwait(false); }, cancellationToken),
            "play" or "pause" => SetPlaybackStateAsync(action.Trim().Equals("play", StringComparison.OrdinalIgnoreCase) ? PlaybackState.Playing : PlaybackState.Paused, cancellationToken),
            _ => throw new BackgroundAudioServiceException($"无效的背景音频动作：{action}", "invalid_action"),
        };

    public Task<BackgroundAudioDto> SetVolumeAsync(int volume, CancellationToken cancellationToken = default) =>
        volume is < 0 or > 100 ? throw new BackgroundAudioServiceException("音量必须在 0 到 100 之间", "invalid_volume") : writes.ExecuteAsync(async (database, token) => { var state = await database.BackgroundAudioStates.SingleAsync(token).ConfigureAwait(false); state.Volume = volume; state.PendingCommand = "SET_VOLUME"; await database.SaveChangesAsync(token).ConfigureAwait(false); return await LoadAsync(database, token).ConfigureAwait(false); }, cancellationToken);

    public Task<BackgroundAudioDto> SetMuteAsync(bool muted, CancellationToken cancellationToken = default) =>
        writes.ExecuteAsync(async (database, token) => { var state = await database.BackgroundAudioStates.SingleAsync(token).ConfigureAwait(false); state.IsMuted = muted; state.PendingCommand = "SET_MUTE"; await database.SaveChangesAsync(token).ConfigureAwait(false); return await LoadAsync(database, token).ConfigureAwait(false); }, cancellationToken);

    public Task<BackgroundAudioDto> SetLoopAsync(bool enabled, CancellationToken cancellationToken = default) =>
        writes.ExecuteAsync(async (database, token) => { var state = await database.BackgroundAudioStates.SingleAsync(token).ConfigureAwait(false); state.LoopEnabled = enabled; state.PendingCommand = "SET_LOOP"; await database.SaveChangesAsync(token).ConfigureAwait(false); return await LoadAsync(database, token).ConfigureAwait(false); }, cancellationToken);

    private Task<BackgroundAudioDto> SetPlaybackStateAsync(PlaybackState playbackState, CancellationToken cancellationToken) =>
        writes.ExecuteAsync(async (database, token) => { var state = await database.BackgroundAudioStates.SingleAsync(token).ConfigureAwait(false); state.PlaybackState = playbackState; state.PendingCommand = playbackState == PlaybackState.Playing ? "PLAY" : "PAUSE"; await database.SaveChangesAsync(token).ConfigureAwait(false); return await LoadAsync(database, token).ConfigureAwait(false); }, cancellationToken);

    public async Task<BackgroundAudioDto> HandleFinishedAsync(AudioFinishedEvent finished, CancellationToken cancellationToken = default)
    {
        bool duplicate;
        lock (_finishedGate)
        {
            duplicate = !AudioPlaybackPolicy.TryAcceptFinished(finished.EventId, _finishedEvents);
        }
        if (duplicate) return await GetAsync(cancellationToken).ConfigureAwait(false);
        await using var database = await contextFactory.CreateDbContextAsync(cancellationToken).ConfigureAwait(false);
        var state = await database.BackgroundAudioStates.AsNoTracking().SingleAsync(cancellationToken).ConfigureAwait(false);
        if (!AudioPlaybackPolicy.ShouldAdvance(state, finished, CurrentGeneration)) return await GetAsync(cancellationToken).ConfigureAwait(false);
        return await AdvanceAsync(false, cancellationToken).ConfigureAwait(false);
    }

    private static async Task<BackgroundAudioDto> LoadAsync(
        ControlDbContext database,
        CancellationToken cancellationToken)
    {
        var state = await database.BackgroundAudioStates.AsNoTracking()
            .Include(item => item.CurrentSource)
            .SingleAsync(cancellationToken).ConfigureAwait(false);
        var playlist = await database.BackgroundAudioPlaylistItems.AsNoTracking()
            .Include(item => item.Source)
            .OrderBy(item => item.SortOrder)
            .ThenBy(item => item.Id)
            .ToArrayAsync(cancellationToken).ConfigureAwait(false);
        var currentItemId = state.CurrentSourceId is { } sourceId
            ? playlist.FirstOrDefault(item => item.SourceId == sourceId)?.Id
            : null;
        return new BackgroundAudioDto
        {
            State = new BackgroundAudioStateDto
            {
                Id = state.Id,
                SourceId = state.CurrentSourceId,
                SourceName = state.CurrentSource?.Name ?? string.Empty,
                SourceUri = state.CurrentSource?.Uri ?? string.Empty,
                Source = state.CurrentSource is null ? null : MediaSourceService.ToSourceDto(state.CurrentSource),
                CurrentItemId = currentItemId,
                PlaybackState = EnumName(state.PlaybackState),
                PlaybackStateLabel = PlaybackStateLabel(state.PlaybackState),
                ErrorMessage = state.ErrorMessage,
                PositionMs = state.PositionMs,
                DurationMs = state.DurationMs,
                Volume = state.Volume,
                IsMuted = state.IsMuted,
                LoopEnabled = state.LoopEnabled,
                PendingCommand = state.PendingCommand,
                UpdatedAt = state.UpdatedAt.ToString("O"),
            },
            Playlist = playlist.Select(item => new BackgroundAudioPlaylistItemDto
            {
                Id = item.Id,
                SourceId = item.SourceId,
                SourceName = item.Source.Name,
                SortOrder = item.SortOrder,
                CreatedAt = item.CreatedAt.ToString("O"),
                Source = MediaSourceService.ToSourceDto(item.Source),
            }).ToArray(),
        };
    }

    private DateTimeOffset NextTimestamp(DateTimeOffset previous)
    {
        var now = _timeProvider.GetUtcNow();
        return now.ToUnixTimeMilliseconds() > previous.ToUnixTimeMilliseconds()
            ? now
            : previous.AddMilliseconds(1);
    }

    private static string EnumName<T>(T value) where T : struct, Enum =>
        value.ToString().ToLowerInvariant();

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
}

public sealed class BackgroundAudioServiceException(string message, string code = "background_audio_error")
    : Exception(message)
{
    public string Code { get; } = code;
}
