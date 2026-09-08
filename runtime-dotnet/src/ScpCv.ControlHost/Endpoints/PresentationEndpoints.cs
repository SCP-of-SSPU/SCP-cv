using System.Text.Json;
using ScpCv.Contracts.Http;
using ScpCv.Infrastructure.Media;
using ScpCv.Infrastructure.Playback;

namespace ScpCv.ControlHost.Endpoints;

public static class PresentationEndpoints
{
    public static IEndpointRouteBuilder MapPresentationEndpoints(this IEndpointRouteBuilder endpoints)
    {
        var api = endpoints.MapGroup("/api").RequireSessionAndCsrf();
        api.MapGet("/sources/{sourceId:long}/ppt-resources/", GetResourcesAsync);
        api.MapPut("/sources/{sourceId:long}/ppt-resources/", ReplaceResourcesAsync);
        api.MapPost("/playback/{windowId:int}/navigate/", NavigateAsync);
        api.MapPost("/playback/{windowId:int}/ppt-media/", ControlMediaAsync);
        api.MapPost("/playback/reset-ppt/", ResetPowerPointAsync);
        return endpoints;
    }

    private static async Task<IResult> GetResourcesAsync(
        long sourceId,
        MediaSourceService media,
        CancellationToken cancellationToken)
    {
        try
        {
            return Results.Ok(new { success = true, resources = await media.GetPptResourcesAsync(sourceId, cancellationToken).ConfigureAwait(false) });
        }
        catch (MediaServiceException exception)
        {
            return ApiEndpointSupport.Error(exception.Message, "media_error", exception.IsNotFound ? 404 : 400);
        }
    }

    private static async Task<IResult> ReplaceResourcesAsync(
        long sourceId,
        HttpRequest request,
        MediaSourceService media,
        CancellationToken cancellationToken)
    {
        try
        {
            using var document = await JsonDocument.ParseAsync(request.Body, cancellationToken: cancellationToken).ConfigureAwait(false);
            if (!document.RootElement.TryGetProperty("resources", out var resources) || resources.ValueKind != JsonValueKind.Array)
            {
                return ApiEndpointSupport.Error("resources 必须是数组", "invalid_resources");
            }

            var inputs = JsonSerializer.Deserialize<List<PptResourceInput>>(resources.GetRawText()) ?? [];
            return Results.Ok(new { success = true, resources = await media.ReplacePptResourcesAsync(sourceId, inputs, cancellationToken).ConfigureAwait(false) });
        }
        catch (JsonException)
        {
            return ApiEndpointSupport.Error("请求体必须是合法 JSON", "invalid_json");
        }
        catch (MediaServiceException exception)
        {
            return ApiEndpointSupport.Error(exception.Message, "media_error", exception.IsNotFound ? 404 : 400);
        }
    }

    private static async Task<IResult> NavigateAsync(
        int windowId,
        HttpRequest request,
        RuntimeStateService runtime,
        CancellationToken cancellationToken)
    {
        var body = await ReadObjectAsync(request, cancellationToken).ConfigureAwait(false);
        if (body.Error is not null) return body.Error;
        var action = String(body.Value, "action");
        if (action.Length == 0) return ApiEndpointSupport.Error("缺少 action 字段", "missing_action");
        try
        {
            var sessions = await runtime.NavigateAsync(windowId, action, Integer(body.Value, "target_index"), Long(body.Value, "position_ms"), cancellationToken).ConfigureAwait(false);
            return Results.Ok(new { success = true, sessions });
        }
        catch (PlaybackServiceException exception)
        {
            return ApiEndpointSupport.Error(exception.Message, exception.Code);
        }
    }

    private static async Task<IResult> ControlMediaAsync(
        int windowId,
        HttpRequest request,
        RuntimeStateService runtime,
        CancellationToken cancellationToken)
    {
        var body = await ReadObjectAsync(request, cancellationToken).ConfigureAwait(false);
        if (body.Error is not null) return body.Error;
        var action = String(body.Value, "action");
        if (action.Length == 0) return ApiEndpointSupport.Error("缺少 action 字段", "missing_action");
        try
        {
            var sessions = await runtime.ControlPptMediaAsync(windowId, action, String(body.Value, "media_id"), Integer(body.Value, "media_index"), cancellationToken).ConfigureAwait(false);
            return Results.Ok(new { success = true, sessions });
        }
        catch (PlaybackServiceException exception)
        {
            return ApiEndpointSupport.Error(exception.Message, exception.Code);
        }
    }

    private static async Task<IResult> ResetPowerPointAsync(RuntimeStateService runtime, CancellationToken cancellationToken)
    {
        try
        {
            return Results.Ok(new { success = true, sessions = await runtime.ResetPowerPointAsync(cancellationToken).ConfigureAwait(false) });
        }
        catch (PlaybackServiceException exception)
        {
            return ApiEndpointSupport.Error(exception.Message, exception.Code);
        }
    }

    private static async Task<BodyResult> ReadObjectAsync(HttpRequest request, CancellationToken cancellationToken)
    {
        try
        {
            var element = await JsonSerializer.DeserializeAsync<JsonElement>(request.Body, cancellationToken: cancellationToken).ConfigureAwait(false);
            return element.ValueKind == JsonValueKind.Object
                ? new(element, null)
                : new(default, ApiEndpointSupport.Error("请求体必须是 JSON 对象", "invalid_json"));
        }
        catch (JsonException)
        {
            return new(default, ApiEndpointSupport.Error("请求体必须是合法 JSON", "invalid_json"));
        }
    }

    private static string String(JsonElement body, string name) => body.TryGetProperty(name, out var value) && value.ValueKind == JsonValueKind.String ? value.GetString()?.Trim() ?? string.Empty : string.Empty;
    private static int? Integer(JsonElement body, string name) => body.TryGetProperty(name, out var value) && value.TryGetInt32(out var parsed) ? parsed : null;
    private static long? Long(JsonElement body, string name) => body.TryGetProperty(name, out var value) && value.TryGetInt64(out var parsed) ? parsed : null;
    private readonly record struct BodyResult(JsonElement Value, IResult? Error);
}
