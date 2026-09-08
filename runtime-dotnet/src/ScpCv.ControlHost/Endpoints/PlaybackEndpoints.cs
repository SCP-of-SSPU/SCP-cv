using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using ScpCv.Infrastructure.Persistence;
using ScpCv.Infrastructure.Playback;

namespace ScpCv.ControlHost.Endpoints;

public static class PlaybackEndpoints
{
    public static IEndpointRouteBuilder MapPlaybackEndpoints(this IEndpointRouteBuilder endpoints)
    {
        var api = endpoints.MapGroup("/api").RequireSessionAndCsrf();
        api.MapGet("/sessions/", GetSessionsAsync);
        api.MapGet("/sessions/{windowId:int}/", GetSessionAsync);
        api.MapGet("/runtime/", GetRuntimeAsync);
        api.MapPatch("/runtime/", SetRuntimeAsync);
        api.MapGet("/volume/", GetVolumeAsync);
        api.MapPatch("/volume/", SetVolumeAsync);
        api.MapGet("/displays/", ListDisplays);
        api.MapPost("/displays/select/", SelectDisplayAsync);
        api.MapPost("/playback/{windowId:int}/open/", OpenAsync);
        api.MapPost("/playback/{windowId:int}/control/", ControlAsync);
        api.MapPost("/playback/{windowId:int}/close/", CloseAsync);
        api.MapPatch("/playback/{windowId:int}/loop/", SetLoopAsync);
        api.MapPatch("/playback/{windowId:int}/volume/", SetWindowVolumeAsync);
        api.MapPatch("/playback/{windowId:int}/mute/", SetWindowMuteAsync);
        api.MapPost("/playback/show-ids/", ShowIdsAsync);
        api.MapPost("/playback/reset-all/", ResetAllAsync);
        return endpoints;
    }

    private static async Task<IResult> GetSessionsAsync(RuntimeStateService runtime, CancellationToken cancellationToken) =>
        Results.Ok(new { success = true, sessions = await runtime.GetSessionsAsync(cancellationToken).ConfigureAwait(false) });

    private static async Task<IResult> GetSessionAsync(
        int windowId,
        RuntimeStateService runtime,
        CancellationToken cancellationToken)
    {
        try
        {
            return Results.Ok(new { success = true, session = await runtime.GetSessionAsync(windowId, cancellationToken).ConfigureAwait(false) });
        }
        catch (PlaybackServiceException exception)
        {
            return Error(exception);
        }
    }

    private static async Task<IResult> GetRuntimeAsync(RuntimeStateService runtime, CancellationToken cancellationToken) =>
        Results.Ok(new { success = true, runtime = await runtime.GetRuntimeAsync(cancellationToken).ConfigureAwait(false) });

    private static async Task<IResult> SetRuntimeAsync(
        HttpRequest request,
        RuntimeStateService runtime,
        IDbContextFactory<ControlDbContext> contextFactory,
        CancellationToken cancellationToken)
    {
        var body = await ReadBodyAsync(request, cancellationToken).ConfigureAwait(false);
        if (body.Error is not null)
        {
            return body.Error;
        }

        try
        {
            var state = await runtime.SetRuntimeModeAsync(String(body.Value, "big_screen_mode"), cancellationToken).ConfigureAwait(false);
            return Results.Ok(new
            {
                success = true,
                runtime = state,
                sessions = await runtime.GetSessionsAsync(cancellationToken).ConfigureAwait(false),
                background_audio = await BackgroundAudioSnapshotAsync(contextFactory, cancellationToken).ConfigureAwait(false),
            });
        }
        catch (PlaybackServiceException exception)
        {
            return Error(exception);
        }
    }

    private static async Task<IResult> GetVolumeAsync(RuntimeStateService runtime, CancellationToken cancellationToken) =>
        Results.Ok(new { success = true, volume = await runtime.GetSystemVolumeAsync(cancellationToken).ConfigureAwait(false) });

    private static async Task<IResult> SetVolumeAsync(
        HttpRequest request,
        RuntimeStateService runtime,
        CancellationToken cancellationToken)
    {
        var body = await ReadBodyAsync(request, cancellationToken).ConfigureAwait(false);
        if (body.Error is not null)
        {
            return body.Error;
        }

        try
        {
            int? level = Has(body.Value, "level") ? Integer(body.Value, "level", -1) : null;
            bool? muted = Has(body.Value, "muted") ? Boolean(body.Value, "muted", false) : null;
            var volume = await runtime.SetSystemVolumeAsync(level, muted, cancellationToken).ConfigureAwait(false);
            return Results.Ok(new { success = true, volume });
        }
        catch (PlaybackServiceException exception)
        {
            return Error(exception);
        }
    }

    private static IResult ListDisplays() =>
        Results.Ok(new { success = true, targets = RuntimeStateService.ListDisplays() });

    private static async Task<IResult> SelectDisplayAsync(
        HttpRequest request,
        RuntimeStateService runtime,
        IDbContextFactory<ControlDbContext> contextFactory,
        CancellationToken cancellationToken) =>
        await MutateAsync(
            request,
            runtime,
            contextFactory,
            (body, token) => runtime.SelectDisplayAsync(
                Integer(body, "window_id", 1),
                String(body, "display_mode", "single"),
                String(body, "target_label"),
                token),
            cancellationToken).ConfigureAwait(false);

    private static async Task<IResult> OpenAsync(
        int windowId,
        HttpRequest request,
        RuntimeStateService runtime,
        IDbContextFactory<ControlDbContext> contextFactory,
        CancellationToken cancellationToken) =>
        await MutateAsync(
            request,
            runtime,
            contextFactory,
            (body, token) => runtime.OpenSourceAsync(
                windowId,
                Integer64(body, "source_id", Integer64(body, "media_source_id", 0)),
                Boolean(body, "autoplay", true),
                Integer(body, "target_slide", 0),
                token),
            cancellationToken).ConfigureAwait(false);

    private static async Task<IResult> ControlAsync(
        int windowId,
        HttpRequest request,
        RuntimeStateService runtime,
        IDbContextFactory<ControlDbContext> contextFactory,
        CancellationToken cancellationToken)
    {
        var body = await ReadBodyAsync(request, cancellationToken).ConfigureAwait(false);
        if (body.Error is not null)
        {
            return body.Error;
        }

        var action = String(body.Value, "action").Trim();
        if (action.Length == 0)
        {
            return ApiEndpointSupport.Error("缺少 action 字段", "missing_action");
        }

        return await MutateValueAsync(
            runtime.ControlAsync(windowId, action, cancellationToken),
            contextFactory,
            cancellationToken).ConfigureAwait(false);
    }

    private static async Task<IResult> CloseAsync(
        int windowId,
        RuntimeStateService runtime,
        IDbContextFactory<ControlDbContext> contextFactory,
        CancellationToken cancellationToken) =>
        await MutateValueAsync(runtime.CloseAsync(windowId, cancellationToken), contextFactory, cancellationToken).ConfigureAwait(false);

    private static async Task<IResult> SetLoopAsync(
        int windowId,
        HttpRequest request,
        RuntimeStateService runtime,
        IDbContextFactory<ControlDbContext> contextFactory,
        CancellationToken cancellationToken) =>
        await MutateAsync(
            request,
            runtime,
            contextFactory,
            (body, token) => runtime.SetLoopAsync(windowId, Boolean(body, "enabled", false), token),
            cancellationToken).ConfigureAwait(false);

    private static async Task<IResult> SetWindowVolumeAsync(
        int windowId,
        HttpRequest request,
        RuntimeStateService runtime,
        IDbContextFactory<ControlDbContext> contextFactory,
        CancellationToken cancellationToken) =>
        await MutateAsync(
            request,
            runtime,
            contextFactory,
            (body, token) => runtime.SetVolumeAsync(windowId, Integer(body, "volume", 100), token),
            cancellationToken).ConfigureAwait(false);

    private static async Task<IResult> SetWindowMuteAsync(
        int windowId,
        HttpRequest request,
        RuntimeStateService runtime,
        IDbContextFactory<ControlDbContext> contextFactory,
        CancellationToken cancellationToken) =>
        await MutateAsync(
            request,
            runtime,
            contextFactory,
            (body, token) => runtime.SetMuteAsync(windowId, Boolean(body, "muted", false), token),
            cancellationToken).ConfigureAwait(false);

    private static async Task<IResult> ShowIdsAsync(
        RuntimeStateService runtime,
        IDbContextFactory<ControlDbContext> contextFactory,
        CancellationToken cancellationToken) =>
        await MutateValueAsync(runtime.ShowIdsAsync(cancellationToken), contextFactory, cancellationToken).ConfigureAwait(false);

    private static async Task<IResult> ResetAllAsync(
        RuntimeStateService runtime,
        IDbContextFactory<ControlDbContext> contextFactory,
        CancellationToken cancellationToken) =>
        await MutateValueAsync(runtime.ResetAllAsync(cancellationToken), contextFactory, cancellationToken).ConfigureAwait(false);

    private static async Task<IResult> MutateAsync(
        HttpRequest request,
        RuntimeStateService runtime,
        IDbContextFactory<ControlDbContext> contextFactory,
        Func<JsonElement, CancellationToken, Task<IReadOnlyList<ScpCv.Contracts.Http.PlaybackSessionDto>>> operation,
        CancellationToken cancellationToken)
    {
        _ = runtime;
        var body = await ReadBodyAsync(request, cancellationToken).ConfigureAwait(false);
        return body.Error ?? await MutateValueAsync(operation(body.Value, cancellationToken), contextFactory, cancellationToken).ConfigureAwait(false);
    }

    private static async Task<IResult> MutateValueAsync(
        Task<IReadOnlyList<ScpCv.Contracts.Http.PlaybackSessionDto>> operation,
        IDbContextFactory<ControlDbContext> contextFactory,
        CancellationToken cancellationToken)
    {
        try
        {
            return Results.Ok(new
            {
                success = true,
                sessions = await operation.ConfigureAwait(false),
                background_audio = await BackgroundAudioSnapshotAsync(contextFactory, cancellationToken).ConfigureAwait(false),
            });
        }
        catch (PlaybackServiceException exception)
        {
            return Error(exception);
        }
    }

    private static async Task<object> BackgroundAudioSnapshotAsync(
        IDbContextFactory<ControlDbContext> contextFactory,
        CancellationToken cancellationToken)
    {
        await using var database = await contextFactory.CreateDbContextAsync(cancellationToken).ConfigureAwait(false);
        var state = await database.BackgroundAudioStates.AsNoTracking().Include(item => item.CurrentSource)
            .SingleAsync(cancellationToken).ConfigureAwait(false);
        return new
        {
            state = new
            {
                id = state.Id,
                source_id = state.CurrentSourceId,
                source_name = state.CurrentSource?.Name ?? string.Empty,
                source_uri = state.CurrentSource?.Uri ?? string.Empty,
                source = state.CurrentSource is null ? null : ScpCv.Infrastructure.Media.MediaSourceService.ToSourceDto(state.CurrentSource),
                current_item_id = (long?)null,
                playback_state = state.PlaybackState.ToString().ToLowerInvariant(),
                playback_state_label = state.PlaybackState == ScpCv.Domain.Model.PlaybackState.Idle ? "待机" : state.PlaybackState.ToString(),
                error_message = state.ErrorMessage,
                position_ms = state.PositionMs,
                duration_ms = state.DurationMs,
                volume = state.Volume,
                is_muted = state.IsMuted,
                loop_enabled = state.LoopEnabled,
                pending_command = state.PendingCommand,
                updated_at = state.UpdatedAt.ToString("O"),
            },
            playlist = Array.Empty<object>(),
        };
    }

    private static IResult Error(PlaybackServiceException exception) =>
        ApiEndpointSupport.Error(exception.Message, exception.Code);

    private static async Task<BodyResult> ReadBodyAsync(HttpRequest request, CancellationToken cancellationToken)
    {
        if (request.ContentLength is 0)
        {
            return new BodyResult(JsonDocument.Parse("{}").RootElement.Clone(), null);
        }

        try
        {
            var element = await JsonSerializer.DeserializeAsync<JsonElement>(request.Body, cancellationToken: cancellationToken).ConfigureAwait(false);
            return element.ValueKind == JsonValueKind.Object
                ? new BodyResult(element, null)
                : new BodyResult(default, ApiEndpointSupport.Error("请求体必须是 JSON 对象", "invalid_json"));
        }
        catch (JsonException)
        {
            return new BodyResult(default, ApiEndpointSupport.Error("请求体必须是合法 JSON", "invalid_json"));
        }
    }

    private static bool Has(JsonElement body, string name) => body.TryGetProperty(name, out _);
    private static string String(JsonElement body, string name, string defaultValue = "") =>
        body.TryGetProperty(name, out var value) && value.ValueKind == JsonValueKind.String ? value.GetString() ?? defaultValue : defaultValue;
    private static long Integer64(JsonElement body, string name, long defaultValue) =>
        body.TryGetProperty(name, out var value) && value.TryGetInt64(out var parsed) ? parsed : defaultValue;
    private static int Integer(JsonElement body, string name, int defaultValue) =>
        body.TryGetProperty(name, out var value) && value.TryGetInt32(out var parsed) ? parsed : defaultValue;
    private static bool Boolean(JsonElement body, string name, bool defaultValue) =>
        body.TryGetProperty(name, out var value) ? value.ValueKind == JsonValueKind.True || value.ValueKind == JsonValueKind.String && value.GetString()?.Trim().ToLowerInvariant() is "true" or "1" or "yes" or "on" : defaultValue;

    private readonly record struct BodyResult(JsonElement Value, IResult? Error);
}
