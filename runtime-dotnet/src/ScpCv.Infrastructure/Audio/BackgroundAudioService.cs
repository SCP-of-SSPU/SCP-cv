using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using ScpCv.Contracts.Http;
using ScpCv.Domain.Model;
using ScpCv.Infrastructure.Media;
using ScpCv.Infrastructure.Persistence;

namespace ScpCv.Infrastructure.Audio;

public sealed class BackgroundAudioService(
    IDbContextFactory<ControlDbContext> contextFactory,
    WriteCoordinator writes,
    TimeProvider? timeProvider = null)
{
    private readonly TimeProvider _timeProvider = timeProvider ?? TimeProvider.System;

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
