using System.Globalization;
using System.Text.Json;
using ScpCv.Infrastructure.Media;

namespace ScpCv.ControlHost.Endpoints;

public static class MediaEndpoints
{
    public static IEndpointRouteBuilder MapMediaEndpoints(this IEndpointRouteBuilder endpoints)
    {
        var api = endpoints.MapGroup("/api").RequireSessionAndCsrf();
        api.MapGet("/folders/", ListFoldersAsync);
        api.MapPost("/folders/", CreateFolderAsync);
        api.MapPatch("/folders/{folderId:long}/", UpdateFolderAsync);
        api.MapDelete("/folders/{folderId:long}/", DeleteFolderAsync);
        api.MapGet("/sources/", ListSourcesAsync);
        api.MapPost("/sources/upload/", UploadSourceAsync).DisableAntiforgery();
        api.MapPost("/sources/local/", AddLocalSourceAsync);
        api.MapPost("/sources/web/", AddWebSourceAsync);
        api.MapPatch("/sources/{sourceId:long}/move/", MoveSourceAsync);
        api.MapGet("/sources/{sourceId:long}/download/", DownloadSourceAsync);
        api.MapGet("/sources/{sourceId:long}/preview/", PreviewSourceAsync);
        api.MapPatch("/sources/{sourceId:long}/", UpdateSourceAsync);
        api.MapDelete("/sources/{sourceId:long}/", DeleteSourceAsync);
        return endpoints;
    }

    private static async Task<IResult> ListFoldersAsync(
        MediaSourceService media,
        CancellationToken cancellationToken) =>
        Results.Ok(new
        {
            success = true,
            folders = await media.ListFoldersAsync(cancellationToken).ConfigureAwait(false),
        });

    private static async Task<IResult> CreateFolderAsync(
        HttpRequest request,
        MediaSourceService media,
        CancellationToken cancellationToken)
    {
        var body = await ReadBodyAsync(request, cancellationToken).ConfigureAwait(false);
        if (body.Error is not null)
        {
            return body.Error;
        }

        try
        {
            var folder = await media.CreateFolderAsync(
                String(body.Value, "name"),
                NullableInt64(body.Value, "parent_id"),
                cancellationToken).ConfigureAwait(false);
            return Results.Json(new { success = true, folder }, statusCode: StatusCodes.Status201Created);
        }
        catch (MediaServiceException exception)
        {
            return MediaError(exception);
        }
    }

    private static async Task<IResult> UpdateFolderAsync(
        long folderId,
        HttpRequest request,
        MediaSourceService media,
        CancellationToken cancellationToken)
    {
        var body = await ReadBodyAsync(request, cancellationToken).ConfigureAwait(false);
        if (body.Error is not null)
        {
            return body.Error;
        }

        try
        {
            var folder = await media.UpdateFolderAsync(
                folderId,
                Has(body.Value, "name") ? String(body.Value, "name") : null,
                NullableInt64(body.Value, "parent_id"),
                Has(body.Value, "parent_id"),
                cancellationToken).ConfigureAwait(false);
            return Results.Ok(new { success = true, folder });
        }
        catch (MediaServiceException exception)
        {
            return MediaError(exception);
        }
    }

    private static async Task<IResult> DeleteFolderAsync(
        long folderId,
        HttpRequest request,
        MediaSourceService media,
        CancellationToken cancellationToken)
    {
        var deleteContents = ParseBoolean(request.Query["delete_contents"].ToString(), false);
        if (request.ContentLength is not 0)
        {
            var body = await ReadBodyAsync(request, cancellationToken).ConfigureAwait(false);
            if (body.Error is null && Has(body.Value, "delete_contents"))
            {
                deleteContents = Boolean(body.Value, "delete_contents", false);
            }
        }

        try
        {
            await media.DeleteFolderAsync(folderId, deleteContents, cancellationToken).ConfigureAwait(false);
            return Results.Ok(new { success = true });
        }
        catch (MediaServiceException exception)
        {
            return MediaError(exception, notFoundForMissing: true);
        }
    }

    private static async Task<IResult> ListSourcesAsync(
        HttpRequest request,
        MediaSourceService media,
        CancellationToken cancellationToken)
    {
        try
        {
            long? folderId = long.TryParse(
                request.Query["folder_id"],
                NumberStyles.Integer,
                CultureInfo.InvariantCulture,
                out var parsedFolderId)
                ? parsedFolderId
                : null;
            var sources = await media.ListSourcesAsync(
                request.Query["source_type"].ToString(),
                folderId,
                cancellationToken).ConfigureAwait(false);
            return Results.Ok(new
            {
                success = true,
                sources,
                sync_result = new { created = 0, updated = 0, removed = 0 },
            });
        }
        catch (MediaServiceException exception)
        {
            return MediaError(exception);
        }
    }

    private static async Task<IResult> UploadSourceAsync(
        HttpRequest request,
        MediaSourceService media,
        CancellationToken cancellationToken)
    {
        if (!request.HasFormContentType)
        {
            return ApiEndpointSupport.Error("缺少 file 字段", "missing_file");
        }

        var form = await request.ReadFormAsync(cancellationToken).ConfigureAwait(false);
        var file = form.Files.GetFile("file");
        if (file is null)
        {
            return ApiEndpointSupport.Error("缺少 file 字段", "missing_file");
        }

        try
        {
            await using var content = file.OpenReadStream();
            var source = await media.AddUploadedAsync(
                content,
                file.FileName,
                file.ContentType,
                form["name"].ToString(),
                EmptyToNull(form["source_type"].ToString()),
                ParseNullableLong(form["folder_id"].ToString()),
                ParseBoolean(form["is_temporary"].ToString(), false),
                ParseBoolean(form["preheat_enabled"].ToString(), true),
                cancellationToken).ConfigureAwait(false);
            return Results.Json(new { success = true, source }, statusCode: StatusCodes.Status201Created);
        }
        catch (MediaServiceException exception)
        {
            return MediaError(exception);
        }
    }

    private static async Task<IResult> AddLocalSourceAsync(
        HttpRequest request,
        MediaSourceService media,
        CancellationToken cancellationToken)
    {
        var body = await ReadBodyAsync(request, cancellationToken).ConfigureAwait(false);
        if (body.Error is not null)
        {
            return body.Error;
        }

        var path = String(body.Value, "path").Trim();
        if (path.Length == 0)
        {
            return ApiEndpointSupport.Error("缺少 path 字段", "missing_path");
        }

        try
        {
            var source = await media.AddLocalAsync(
                path,
                EmptyToNull(String(body.Value, "name")),
                EmptyToNull(String(body.Value, "source_type")),
                NullableInt64(body.Value, "folder_id"),
                Boolean(body.Value, "preheat_enabled", Boolean(body.Value, "keep_alive", true)),
                cancellationToken).ConfigureAwait(false);
            return Results.Json(new { success = true, source }, statusCode: StatusCodes.Status201Created);
        }
        catch (MediaServiceException exception)
        {
            return MediaError(exception);
        }
    }

    private static async Task<IResult> AddWebSourceAsync(
        HttpRequest request,
        MediaSourceService media,
        CancellationToken cancellationToken)
    {
        var body = await ReadBodyAsync(request, cancellationToken).ConfigureAwait(false);
        if (body.Error is not null)
        {
            return body.Error;
        }

        var url = String(body.Value, "url").Trim();
        if (url.Length == 0)
        {
            return ApiEndpointSupport.Error("缺少 url 字段", "missing_url");
        }

        try
        {
            var source = await media.AddWebAsync(
                url,
                EmptyToNull(String(body.Value, "name")),
                NullableInt64(body.Value, "folder_id"),
                Boolean(body.Value, "preheat_enabled", Boolean(body.Value, "keep_alive", true)),
                cancellationToken).ConfigureAwait(false);
            return Results.Json(new { success = true, source }, statusCode: StatusCodes.Status201Created);
        }
        catch (MediaServiceException exception)
        {
            return MediaError(exception);
        }
    }

    private static async Task<IResult> MoveSourceAsync(
        long sourceId,
        HttpRequest request,
        MediaSourceService media,
        CancellationToken cancellationToken)
    {
        var body = await ReadBodyAsync(request, cancellationToken).ConfigureAwait(false);
        if (body.Error is not null)
        {
            return body.Error;
        }

        try
        {
            var source = await media.MoveSourceAsync(
                sourceId,
                NullableInt64(body.Value, "folder_id"),
                cancellationToken).ConfigureAwait(false);
            return Results.Ok(new { success = true, source });
        }
        catch (MediaServiceException exception)
        {
            return MediaError(exception, notFoundForMissing: true);
        }
    }

    private static async Task<IResult> UpdateSourceAsync(
        long sourceId,
        HttpRequest request,
        MediaSourceService media,
        CancellationToken cancellationToken)
    {
        var body = await ReadBodyAsync(request, cancellationToken).ConfigureAwait(false);
        if (body.Error is not null)
        {
            return body.Error;
        }

        try
        {
            var source = await media.UpdateSourceAsync(
                sourceId,
                Has(body.Value, "name") ? String(body.Value, "name") : null,
                Has(body.Value, "uri") ? String(body.Value, "uri") : null,
                Has(body.Value, "preheat_enabled")
                    ? Boolean(body.Value, "preheat_enabled", true)
                    : Has(body.Value, "keep_alive") ? Boolean(body.Value, "keep_alive", true) : null,
                cancellationToken).ConfigureAwait(false);
            return Results.Ok(new { success = true, source });
        }
        catch (MediaServiceException exception)
        {
            return MediaError(exception);
        }
    }

    private static async Task<IResult> DeleteSourceAsync(
        long sourceId,
        MediaSourceService media,
        CancellationToken cancellationToken)
    {
        try
        {
            await media.DeleteSourceAsync(sourceId, cancellationToken).ConfigureAwait(false);
            return Results.Ok(new { success = true });
        }
        catch (MediaServiceException exception)
        {
            return MediaError(exception, notFoundForMissing: true);
        }
    }

    private static async Task<IResult> DownloadSourceAsync(
        long sourceId,
        MediaSourceService media,
        CancellationToken cancellationToken)
    {
        try
        {
            var file = await media.GetDownloadAsync(sourceId, cancellationToken).ConfigureAwait(false);
            return Results.File(file.Path, file.ContentType, file.FileName, enableRangeProcessing: true);
        }
        catch (MediaServiceException exception)
        {
            return MediaError(exception, notFoundForMissing: true);
        }
    }

    private static async Task<IResult> PreviewSourceAsync(
        long sourceId,
        MediaSourceService media,
        CancellationToken cancellationToken)
    {
        try
        {
            var file = await media.GetPreviewAsync(sourceId, cancellationToken).ConfigureAwait(false);
            return Results.File(file.Path, file.ContentType, enableRangeProcessing: true);
        }
        catch (MediaServiceException exception)
        {
            return MediaError(exception, notFoundForMissing: true);
        }
    }

    private static IResult MediaError(MediaServiceException exception, bool notFoundForMissing = false) =>
        ApiEndpointSupport.Error(
            exception.Message,
            "media_error",
            exception.IsNotFound && notFoundForMissing ? StatusCodes.Status404NotFound : StatusCodes.Status400BadRequest);

    private static async Task<BodyResult> ReadBodyAsync(HttpRequest request, CancellationToken cancellationToken)
    {
        if (request.ContentLength is 0)
        {
            return new BodyResult(JsonDocument.Parse("{}").RootElement.Clone(), null);
        }

        try
        {
            var element = await JsonSerializer.DeserializeAsync<JsonElement>(
                request.Body,
                cancellationToken: cancellationToken).ConfigureAwait(false);
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

    private static string String(JsonElement body, string name) =>
        body.TryGetProperty(name, out var value) && value.ValueKind == JsonValueKind.String
            ? value.GetString() ?? string.Empty
            : string.Empty;

    private static long? NullableInt64(JsonElement body, string name)
    {
        if (!body.TryGetProperty(name, out var value) || value.ValueKind is JsonValueKind.Null or JsonValueKind.Undefined)
        {
            return null;
        }

        if (value.TryGetInt64(out var number))
        {
            return number;
        }

        return value.ValueKind == JsonValueKind.String ? ParseNullableLong(value.GetString()) : null;
    }

    private static bool Boolean(JsonElement body, string name, bool defaultValue)
    {
        if (!body.TryGetProperty(name, out var value))
        {
            return defaultValue;
        }

        return value.ValueKind switch
        {
            JsonValueKind.True => true,
            JsonValueKind.False => false,
            JsonValueKind.String => ParseBoolean(value.GetString(), defaultValue),
            _ => defaultValue,
        };
    }

    private static bool ParseBoolean(string? value, bool defaultValue) => string.IsNullOrWhiteSpace(value)
        ? defaultValue
        : value.Trim().ToLowerInvariant() is "true" or "1" or "yes" or "on";

    private static long? ParseNullableLong(string? value) => long.TryParse(
        value,
        NumberStyles.Integer,
        CultureInfo.InvariantCulture,
        out var parsed) ? parsed : null;

    private static string? EmptyToNull(string? value) => string.IsNullOrWhiteSpace(value) ? null : value;

    private readonly record struct BodyResult(JsonElement Value, IResult? Error);
}
