using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using ScpCv.Contracts.Ipc;
using ScpCv.Domain.Model;
using ScpCv.Infrastructure.Persistence;

namespace ScpCv.ControlHost.Events;

public sealed record StateReportAcceptance(bool Accepted, string Reason);

/// <summary>只把通过 instance/epoch/generation fencing 的实际状态写入兼容 SSE 投影。</summary>
public sealed class RuntimeProjectionPublisher(
    WriteCoordinator writes,
    SseEventHub events,
    TimeProvider? timeProvider = null)
{
    private readonly TimeProvider _timeProvider = timeProvider ?? TimeProvider.System;

    public async Task<StateReportAcceptance> ApplyStateReportAsync(
        CommandTargetKind targetKind,
        int targetId,
        Guid workerInstanceId,
        long ownerEpoch,
        StateReportDto report,
        CancellationToken cancellationToken = default)
    {
        var accepted = await writes.ExecuteAsync(
                async (database, token) =>
                {
                    var ownership = await database.WorkerOwnerships.SingleOrDefaultAsync(
                            item => item.TargetKind == targetKind && item.TargetId == targetId,
                            token)
                        .ConfigureAwait(false);
                    if (ownership is null ||
                        ownership.WorkerInstanceId != workerInstanceId ||
                        ownership.OwnerEpoch != ownerEpoch ||
                        ownership.Status != WorkerOwnershipState.Online)
                    {
                        return new StateReportAcceptance(false, "worker_fenced");
                    }

                    ownership.LastTransportHeartbeat = _timeProvider.GetUtcNow();
                    ownership.LastUiProgress = ownership.LastTransportHeartbeat;
                    if (targetKind == CommandTargetKind.Display)
                    {
                        return await ApplyDisplayAsync(database, targetId, report, token).ConfigureAwait(false);
                    }

                    return await ApplyAudioAsync(database, report, token).ConfigureAwait(false);
                },
                cancellationToken)
            .ConfigureAwait(false);

        if (accepted.Accepted)
        {
            events.PublishLatest();
        }

        return accepted;
    }

    public long PublishCommandResult() => events.PublishLatest();

    private async Task<StateReportAcceptance> ApplyDisplayAsync(
        ControlDbContext database,
        int targetId,
        StateReportDto report,
        CancellationToken cancellationToken)
    {
        var session = await database.PlaybackSessions.SingleAsync(
                item => item.WindowId == targetId,
                cancellationToken)
            .ConfigureAwait(false);
        if (report.SourceGeneration != session.DesiredGeneration ||
            report.SourceGeneration < session.ObservedGeneration)
        {
            return new StateReportAcceptance(false, "stale_generation");
        }

        var state = report.State;
        session.ObservedGeneration = report.SourceGeneration;
        session.PlayerLastSeenAt = _timeProvider.GetUtcNow();
        session.PlaybackState = ReadPlaybackState(state, session.PlaybackState);
        session.PlaybackMode = ReadPlaybackMode(state, session.PlaybackMode);
        session.ActualSourceId = ReadInt64(state, "source_id", session.ActualSourceId);
        session.ActualAdapterKind = ReadString(state, "adapter_kind", session.ActualAdapterKind);
        session.ErrorMessage = ReadString(state, "error_message", session.ErrorMessage);
        session.CurrentSlide = ReadInt32(state, "current_slide", session.CurrentSlide);
        session.TotalSlides = ReadInt32(state, "total_slides", session.TotalSlides);
        session.PositionMs = ReadInt64(state, "position_ms", session.PositionMs) ?? session.PositionMs;
        session.DurationMs = ReadInt64(state, "duration_ms", session.DurationMs) ?? session.DurationMs;
        session.PendingCommand = string.Empty;
        session.LastUpdatedAt = NextTimestamp(session.LastUpdatedAt);
        return new StateReportAcceptance(true, "accepted");
    }

    private async Task<StateReportAcceptance> ApplyAudioAsync(
        ControlDbContext database,
        StateReportDto report,
        CancellationToken cancellationToken)
    {
        var state = await database.BackgroundAudioStates.SingleAsync(cancellationToken).ConfigureAwait(false);
        state.PlaybackState = ReadPlaybackState(report.State, state.PlaybackState);
        state.ErrorMessage = ReadString(report.State, "error_message", state.ErrorMessage);
        state.PositionMs = ReadInt64(report.State, "position_ms", state.PositionMs) ?? state.PositionMs;
        state.DurationMs = ReadInt64(report.State, "duration_ms", state.DurationMs) ?? state.DurationMs;
        state.PendingCommand = string.Empty;
        state.UpdatedAt = NextTimestamp(state.UpdatedAt);
        return new StateReportAcceptance(true, "accepted");
    }

    private DateTimeOffset NextTimestamp(DateTimeOffset previous)
    {
        var now = _timeProvider.GetUtcNow();
        return now.ToUnixTimeMilliseconds() > previous.ToUnixTimeMilliseconds()
            ? now
            : previous.AddMilliseconds(1);
    }

    private static PlaybackState ReadPlaybackState(JsonElement state, PlaybackState fallback) =>
        Enum.TryParse<PlaybackState>(ReadString(state, "playback_state", string.Empty), true, out var parsed)
            ? parsed
            : fallback;

    private static PlaybackMode ReadPlaybackMode(JsonElement state, PlaybackMode fallback)
    {
        var value = ReadString(state, "playback_mode", string.Empty);
        return value.Equals("powerpoint", StringComparison.OrdinalIgnoreCase)
            ? PlaybackMode.PowerPoint
            : Enum.TryParse<PlaybackMode>(value, true, out var parsed) ? parsed : fallback;
    }

    private static string ReadString(JsonElement state, string name, string fallback) =>
        state.ValueKind == JsonValueKind.Object &&
        state.TryGetProperty(name, out var value) &&
        value.ValueKind == JsonValueKind.String
            ? value.GetString() ?? fallback
            : fallback;

    private static int ReadInt32(JsonElement state, string name, int fallback) =>
        state.ValueKind == JsonValueKind.Object &&
        state.TryGetProperty(name, out var value) &&
        value.TryGetInt32(out var parsed)
            ? parsed
            : fallback;

    private static long? ReadInt64(JsonElement state, string name, long? fallback) =>
        state.ValueKind == JsonValueKind.Object &&
        state.TryGetProperty(name, out var value) &&
        value.TryGetInt64(out var parsed)
            ? parsed
            : fallback;
}
