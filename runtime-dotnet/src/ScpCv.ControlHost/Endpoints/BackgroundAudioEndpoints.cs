using System.Text.Json;
using ScpCv.Infrastructure.Audio;

namespace ScpCv.ControlHost.Endpoints;

public static class BackgroundAudioEndpoints
{
    public static IEndpointRouteBuilder MapBackgroundAudioEndpoints(this IEndpointRouteBuilder endpoints)
    {
        var api = endpoints.MapGroup("/api").RequireSessionAndCsrf();
        api.MapGet("/background-audio/", GetAsync);
        api.MapPost("/background-audio/play-source/", PlaySourceAsync);
        api.MapPost("/background-audio/control/", ControlAsync);
        api.MapPatch("/background-audio/volume/", SetVolumeAsync);
        api.MapPatch("/background-audio/mute/", SetMuteAsync);
        api.MapPatch("/background-audio/loop/", SetLoopAsync);
        api.MapPost("/background-audio/playlist/", AddToPlaylistAsync);
        api.MapDelete("/background-audio/playlist/", ClearPlaylistAsync);
        api.MapDelete("/background-audio/playlist/{itemId:long}/", RemoveAsync);
        api.MapPost("/background-audio/playlist/{itemId:long}/play/", PlayItemAsync);
        return endpoints;
    }

    private static async Task<IResult> ControlAsync(HttpRequest request, BackgroundAudioService audio, CancellationToken cancellationToken)
    {
        var body = await ReadBodyAsync(request, cancellationToken).ConfigureAwait(false); if (body.Error is not null) return body.Error;
        try { return Results.Ok(new { success = true, background_audio = await audio.ControlAsync(String(body.Value, "action"), cancellationToken).ConfigureAwait(false) }); }
        catch (BackgroundAudioServiceException exception) { return ApiEndpointSupport.Error(exception.Message, exception.Code); }
    }

    private static async Task<IResult> SetVolumeAsync(HttpRequest request, BackgroundAudioService audio, CancellationToken cancellationToken)
    {
        var body = await ReadBodyAsync(request, cancellationToken).ConfigureAwait(false); if (body.Error is not null) return body.Error;
        try { return Results.Ok(new { success = true, background_audio = await audio.SetVolumeAsync(Integer(body.Value, "volume"), cancellationToken).ConfigureAwait(false) }); }
        catch (BackgroundAudioServiceException exception) { return ApiEndpointSupport.Error(exception.Message, exception.Code); }
    }

    private static async Task<IResult> SetMuteAsync(HttpRequest request, BackgroundAudioService audio, CancellationToken cancellationToken)
    {
        var body = await ReadBodyAsync(request, cancellationToken).ConfigureAwait(false); if (body.Error is not null) return body.Error;
        try { return Results.Ok(new { success = true, background_audio = await audio.SetMuteAsync(Boolean(body.Value, "muted"), cancellationToken).ConfigureAwait(false) }); }
        catch (BackgroundAudioServiceException exception) { return ApiEndpointSupport.Error(exception.Message, exception.Code); }
    }

    private static async Task<IResult> SetLoopAsync(HttpRequest request, BackgroundAudioService audio, CancellationToken cancellationToken)
    {
        var body = await ReadBodyAsync(request, cancellationToken).ConfigureAwait(false); if (body.Error is not null) return body.Error;
        try { return Results.Ok(new { success = true, background_audio = await audio.SetLoopAsync(Boolean(body.Value, "enabled"), cancellationToken).ConfigureAwait(false) }); }
        catch (BackgroundAudioServiceException exception) { return ApiEndpointSupport.Error(exception.Message, exception.Code); }
    }

    private static async Task<IResult> AddToPlaylistAsync(HttpRequest request, BackgroundAudioService audio, CancellationToken cancellationToken)
    {
        var body = await ReadBodyAsync(request, cancellationToken).ConfigureAwait(false); if (body.Error is not null) return body.Error;
        var sourceId = Integer64(body.Value, "source_id");
        if (sourceId <= 0) return ApiEndpointSupport.Error("source_id 必须大于 0", "invalid_source");
        try { return Results.Ok(new { success = true, background_audio = await audio.AddToPlaylistAsync(sourceId, cancellationToken).ConfigureAwait(false) }); }
        catch (BackgroundAudioServiceException exception) { return ApiEndpointSupport.Error(exception.Message, exception.Code); }
    }

    private static async Task<IResult> ClearPlaylistAsync(BackgroundAudioService audio, CancellationToken cancellationToken) =>
        Results.Ok(new { success = true, background_audio = await audio.ClearPlaylistAsync(cancellationToken).ConfigureAwait(false) });

    private static async Task<IResult> RemoveAsync(long itemId, BackgroundAudioService audio, CancellationToken cancellationToken)
    {
        try { return Results.Ok(new { success = true, background_audio = await audio.RemovePlaylistItemAsync(itemId, cancellationToken).ConfigureAwait(false) }); }
        catch (BackgroundAudioServiceException exception) { return ApiEndpointSupport.Error(exception.Message, exception.Code, StatusCodes.Status404NotFound); }
    }

    private static async Task<IResult> PlayItemAsync(long itemId, BackgroundAudioService audio, CancellationToken cancellationToken)
    {
        try { return Results.Ok(new { success = true, background_audio = await audio.PlayPlaylistItemAsync(itemId, cancellationToken).ConfigureAwait(false) }); }
        catch (BackgroundAudioServiceException exception) { return ApiEndpointSupport.Error(exception.Message, exception.Code, StatusCodes.Status404NotFound); }
    }

    private static async Task<IResult> GetAsync(
        BackgroundAudioService audio,
        CancellationToken cancellationToken) =>
        Results.Ok(new
        {
            success = true,
            background_audio = await audio.GetAsync(cancellationToken).ConfigureAwait(false),
        });

    private static async Task<IResult> PlaySourceAsync(
        HttpRequest request,
        BackgroundAudioService audio,
        CancellationToken cancellationToken)
    {
        var body = await ReadBodyAsync(request, cancellationToken).ConfigureAwait(false);
        if (body.Error is not null) return body.Error;
        var sourceId = Integer64(body.Value, "source_id");
        if (sourceId <= 0)
        {
            return ApiEndpointSupport.Error("source_id 必须大于 0", "invalid_source");
        }

        try
        {
            var snapshot = await audio.PlaySourceAsync(sourceId, cancellationToken).ConfigureAwait(false);
            return Results.Ok(new { success = true, background_audio = snapshot });
        }
        catch (BackgroundAudioServiceException exception)
        {
            return ApiEndpointSupport.Error(exception.Message, exception.Code);
        }
    }

    private static async Task<BodyResult> ReadBodyAsync(
        HttpRequest request,
        CancellationToken cancellationToken)
    {
        if (request.ContentLength is 0)
        {
            return new BodyResult(JsonDocument.Parse("{}").RootElement.Clone(), null);
        }

        try
        {
            var body = await JsonSerializer.DeserializeAsync<JsonElement>(
                request.Body,
                cancellationToken: cancellationToken).ConfigureAwait(false);
            return body.ValueKind == JsonValueKind.Object
                ? new BodyResult(body, null)
                : new BodyResult(default, ApiEndpointSupport.Error("请求体必须是 JSON 对象", "invalid_json"));
        }
        catch (JsonException)
        {
            return new BodyResult(default, ApiEndpointSupport.Error("请求体必须是合法 JSON", "invalid_json"));
        }
    }

    private static long Integer64(JsonElement body, string name) =>
        body.TryGetProperty(name, out var value) && value.TryGetInt64(out var parsed) ? parsed : 0;

    private static int Integer(JsonElement body, string name) => body.TryGetProperty(name, out var value) && value.TryGetInt32(out var parsed) ? parsed : 0;
    private static bool Boolean(JsonElement body, string name) => body.TryGetProperty(name, out var value) && (value.ValueKind == JsonValueKind.True || value.ValueKind == JsonValueKind.String && value.GetString()?.Equals("true", StringComparison.OrdinalIgnoreCase) == true);
    private static string String(JsonElement body, string name) => body.TryGetProperty(name, out var value) && value.ValueKind == JsonValueKind.String ? value.GetString()?.Trim() ?? string.Empty : string.Empty;

    private readonly record struct BodyResult(JsonElement Value, IResult? Error);
}
