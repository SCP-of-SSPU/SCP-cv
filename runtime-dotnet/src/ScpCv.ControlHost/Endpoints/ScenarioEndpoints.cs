using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using ScpCv.Contracts.Http;
using ScpCv.Infrastructure.Persistence;
using ScpCv.Infrastructure.Scenarios;

namespace ScpCv.ControlHost.Endpoints;

public static class ScenarioEndpoints
{
    public static IEndpointRouteBuilder MapScenarioEndpoints(this IEndpointRouteBuilder endpoints)
    {
        var api = endpoints.MapGroup("/api").RequireSessionAndCsrf();
        api.MapGet("/scenarios/", ListAsync);
        api.MapPost("/scenarios/", CreateAsync);
        api.MapPost("/scenarios/create/", CreateAsync);
        api.MapPost("/scenarios/capture/", CaptureAsync);
        api.MapGet("/scenarios/{scenarioId:long}/", GetAsync);
        api.MapPatch("/scenarios/{scenarioId:long}/", UpdateAsync);
        api.MapDelete("/scenarios/{scenarioId:long}/", DeleteAsync);
        api.MapPost("/scenarios/{scenarioId:long}/pin/", PinAsync);
        api.MapPost("/scenarios/{scenarioId:long}/activate/", ActivateAsync);
        return endpoints;
    }

    private static async Task<IResult> ListAsync(ScenarioService scenarios, CancellationToken cancellationToken) =>
        Results.Ok(new { success = true, scenarios = await scenarios.ListAsync(cancellationToken).ConfigureAwait(false) });

    private static async Task<IResult> GetAsync(long scenarioId, ScenarioService scenarios, CancellationToken cancellationToken)
    {
        try { return Results.Ok(new { success = true, scenario = await scenarios.GetAsync(scenarioId, cancellationToken).ConfigureAwait(false) }); }
        catch (ScenarioServiceException exception) { return Error(exception, notFoundAs404: true); }
    }

    private static async Task<IResult> CreateAsync(HttpRequest request, ScenarioService scenarios, CancellationToken cancellationToken)
    {
        var body = await ReadBodyAsync(request, cancellationToken).ConfigureAwait(false);
        if (body.Error is not null) return body.Error;
        var name = String(body.Value, "name").Trim();
        if (name.Length == 0) return ApiEndpointSupport.Error("缺少 name 字段", "missing_name");
        try
        {
            var scenario = await scenarios.CreateAsync(new ScenarioWriteModel(
                name,
                String(body.Value, "description"),
                String(body.Value, "big_screen_mode_state", "unset"),
                String(body.Value, "big_screen_mode", "single"),
                String(body.Value, "volume_state", "unset"),
                Integer(body.Value, "volume_level", 100),
                Targets(body.Value) ?? []), cancellationToken).ConfigureAwait(false);
            return Results.Json(new { success = true, scenario }, statusCode: StatusCodes.Status201Created);
        }
        catch (ScenarioServiceException exception) { return Error(exception); }
    }

    private static async Task<IResult> UpdateAsync(long scenarioId, HttpRequest request, ScenarioService scenarios, CancellationToken cancellationToken)
    {
        var body = await ReadBodyAsync(request, cancellationToken).ConfigureAwait(false);
        if (body.Error is not null) return body.Error;
        try
        {
            var scenario = await scenarios.UpdateAsync(scenarioId, new ScenarioPatchModel(
                Has(body.Value, "name") ? String(body.Value, "name") : null,
                Has(body.Value, "description") ? String(body.Value, "description") : null,
                Has(body.Value, "big_screen_mode_state") ? String(body.Value, "big_screen_mode_state") : null,
                Has(body.Value, "big_screen_mode") ? String(body.Value, "big_screen_mode") : null,
                Has(body.Value, "volume_state") ? String(body.Value, "volume_state") : null,
                Has(body.Value, "volume_level") ? Integer(body.Value, "volume_level", 100) : null,
                Has(body.Value, "targets") ? Targets(body.Value) : null), cancellationToken).ConfigureAwait(false);
            return Results.Ok(new { success = true, scenario });
        }
        catch (ScenarioServiceException exception) { return Error(exception); }
    }

    private static async Task<IResult> DeleteAsync(long scenarioId, ScenarioService scenarios, CancellationToken cancellationToken)
    {
        try
        {
            await scenarios.DeleteAsync(scenarioId, cancellationToken).ConfigureAwait(false);
            return Results.Ok(new { success = true });
        }
        catch (ScenarioServiceException exception) { return Error(exception, notFoundAs404: true); }
    }

    private static async Task<IResult> PinAsync(long scenarioId, ScenarioService scenarios, CancellationToken cancellationToken)
    {
        try { return Results.Ok(new { success = true, scenario = await scenarios.TogglePinAsync(scenarioId, cancellationToken).ConfigureAwait(false) }); }
        catch (ScenarioServiceException exception) { return Error(exception, notFoundAs404: true); }
    }

    private static async Task<IResult> CaptureAsync(HttpRequest request, ScenarioService scenarios, CancellationToken cancellationToken)
    {
        var body = await ReadBodyAsync(request, cancellationToken).ConfigureAwait(false);
        if (body.Error is not null) return body.Error;
        var name = String(body.Value, "name").Trim();
        if (name.Length == 0) return ApiEndpointSupport.Error("缺少 name 字段", "missing_name");
        try
        {
            var scenario = await scenarios.CaptureAsync(
                name,
                String(body.Value, "description"),
                Has(body.Value, "scenario_id") ? Integer64(body.Value, "scenario_id", 0) : null,
                cancellationToken).ConfigureAwait(false);
            return Results.Ok(new { success = true, scenario });
        }
        catch (ScenarioServiceException exception) { return Error(exception); }
    }

    private static async Task<IResult> ActivateAsync(
        long scenarioId,
        ScenarioService scenarios,
        IDbContextFactory<ControlDbContext> contextFactory,
        CancellationToken cancellationToken)
    {
        try
        {
            var sessions = await scenarios.ActivateAsync(scenarioId, cancellationToken).ConfigureAwait(false);
            await using var database = await contextFactory.CreateDbContextAsync(cancellationToken).ConfigureAwait(false);
            var audio = await database.BackgroundAudioStates.AsNoTracking().SingleAsync(cancellationToken).ConfigureAwait(false);
            return Results.Ok(new
            {
                success = true,
                sessions,
                background_audio = new
                {
                    state = new
                    {
                        id = audio.Id,
                        source_id = audio.CurrentSourceId,
                        source_name = string.Empty,
                        source_uri = string.Empty,
                        source = (object?)null,
                        current_item_id = (long?)null,
                        playback_state = audio.PlaybackState.ToString().ToLowerInvariant(),
                        playback_state_label = audio.PlaybackState.ToString(),
                        error_message = audio.ErrorMessage,
                        position_ms = audio.PositionMs,
                        duration_ms = audio.DurationMs,
                        volume = audio.Volume,
                        is_muted = audio.IsMuted,
                        loop_enabled = audio.LoopEnabled,
                        pending_command = audio.PendingCommand,
                        updated_at = audio.UpdatedAt.ToString("O"),
                    },
                    playlist = Array.Empty<object>(),
                },
            });
        }
        catch (ScenarioServiceException exception) { return Error(exception); }
    }

    private static IResult Error(ScenarioServiceException exception, bool notFoundAs404 = false) => ApiEndpointSupport.Error(
        exception.Message,
        "scenario_error",
        exception.IsNotFound && notFoundAs404 ? StatusCodes.Status404NotFound : StatusCodes.Status400BadRequest);

    private static async Task<BodyResult> ReadBodyAsync(HttpRequest request, CancellationToken cancellationToken)
    {
        if (request.ContentLength is 0) return new BodyResult(JsonDocument.Parse("{}").RootElement.Clone(), null);
        try
        {
            var body = await JsonSerializer.DeserializeAsync<JsonElement>(request.Body, cancellationToken: cancellationToken).ConfigureAwait(false);
            return body.ValueKind == JsonValueKind.Object
                ? new BodyResult(body, null)
                : new BodyResult(default, ApiEndpointSupport.Error("请求体必须是 JSON 对象", "invalid_json"));
        }
        catch (JsonException) { return new BodyResult(default, ApiEndpointSupport.Error("请求体必须是合法 JSON", "invalid_json")); }
    }

    private static ScenarioTargetDto[]? Targets(JsonElement body)
    {
        if (!body.TryGetProperty("targets", out var value)) return null;
        if (value.ValueKind != JsonValueKind.Array) throw new ScenarioServiceException("targets 必须是数组");
        var targets = new List<ScenarioTargetDto>();
        foreach (var item in value.EnumerateArray())
        {
            if (item.ValueKind != JsonValueKind.Object) continue;
            targets.Add(new ScenarioTargetDto
            {
                WindowId = FlexibleInt32(item, "window_id"),
                SourceState = String(item, "source_state", "unset"),
                SourceId = FlexibleInt64(item, "source_id"),
                Autoplay = FlexibleBoolean(item, "autoplay", true),
                Resume = FlexibleBoolean(item, "resume", true),
            });
        }
        return targets.ToArray();
    }

    private static bool FlexibleBoolean(JsonElement body, string name, bool fallback)
    {
        if (!body.TryGetProperty(name, out var value)) return fallback;
        if (value.ValueKind is JsonValueKind.True or JsonValueKind.False) return value.GetBoolean();
        return value.ValueKind == JsonValueKind.String
            ? value.GetString()?.Trim().ToLowerInvariant() is "true" or "1" or "yes" or "on"
            : fallback;
    }

    private static int FlexibleInt32(JsonElement body, string name)
    {
        if (!body.TryGetProperty(name, out var value)) return 0;
        if (value.TryGetInt32(out var numeric)) return numeric;
        return value.ValueKind == JsonValueKind.String && int.TryParse(value.GetString(), out var parsed) ? parsed : 0;
    }

    private static long? FlexibleInt64(JsonElement body, string name)
    {
        if (!body.TryGetProperty(name, out var value) || value.ValueKind == JsonValueKind.Null) return null;
        if (value.TryGetInt64(out var numeric)) return numeric;
        return value.ValueKind == JsonValueKind.String && long.TryParse(value.GetString(), out var parsed) ? parsed : null;
    }

    private static bool Has(JsonElement body, string name) => body.TryGetProperty(name, out _);
    private static string String(JsonElement body, string name, string fallback = "") => body.TryGetProperty(name, out var value) && value.ValueKind == JsonValueKind.String ? value.GetString() ?? fallback : fallback;
    private static int Integer(JsonElement body, string name, int fallback) => body.TryGetProperty(name, out var value) && value.TryGetInt32(out var parsed) ? parsed : fallback;
    private static long Integer64(JsonElement body, string name, long fallback) => body.TryGetProperty(name, out var value) && value.TryGetInt64(out var parsed) ? parsed : fallback;
    private readonly record struct BodyResult(JsonElement Value, IResult? Error);
}
