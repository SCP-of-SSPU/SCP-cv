using System.Net;
using System.Net.Http.Json;
using System.Text;
using System.Text.Json;

namespace ScpCv.ControlHost.Tests;

public sealed class MediaEndpointTests
{
    private const string InitialPassword = "Old-password-123";

    [Fact]
    public async Task FolderAndWebSourceCrudPreservesCompatibilityContract()
    {
        using var factory = new ControlHostApplicationFactory();
        using var client = factory.CreateHttpsClient();
        var csrf = await AuthenticateAsync(client);

        using var createFolder = CreateJsonRequest(HttpMethod.Post, "/api/folders/", csrf, new { name = "网页" });
        using var createdFolder = await client.SendAsync(createFolder);
        using var folderBody = await ReadJsonAsync(createdFolder);
        Assert.True(
            createdFolder.StatusCode == HttpStatusCode.Created,
            $"期望 201，实际 {(int)createdFolder.StatusCode}：{folderBody.RootElement.GetRawText()}");
        var folderId = folderBody.RootElement.GetProperty("folder").GetProperty("id").GetInt64();

        using var createSource = CreateJsonRequest(
            HttpMethod.Post,
            "/api/sources/web/",
            csrf,
            new { url = "example.test/dashboard", name = "监控页", folder_id = folderId, preheat_enabled = true });
        using var createdSource = await client.SendAsync(createSource);
        using var sourceBody = await ReadJsonAsync(createdSource);
        Assert.Equal(HttpStatusCode.Created, createdSource.StatusCode);
        var source = sourceBody.RootElement.GetProperty("source");
        var sourceId = source.GetProperty("id").GetInt64();
        Assert.Equal("http://example.test/dashboard", source.GetProperty("uri").GetString());
        Assert.Equal(folderId, source.GetProperty("folder_id").GetInt64());
        Assert.True(source.GetProperty("keep_alive").GetBoolean());
        Assert.True(source.GetProperty("preheat_enabled").GetBoolean());

        using var updateSource = CreateJsonRequest(
            HttpMethod.Patch,
            $"/api/sources/{sourceId}/",
            csrf,
            new { name = "更新后的监控页", uri = "https://example.test/live", keep_alive = false });
        using var updatedSource = await client.SendAsync(updateSource);
        using var updatedBody = await ReadJsonAsync(updatedSource);
        Assert.Equal(HttpStatusCode.OK, updatedSource.StatusCode);
        Assert.Equal("更新后的监控页", updatedBody.RootElement.GetProperty("source").GetProperty("name").GetString());
        Assert.Equal("https://example.test/live", updatedBody.RootElement.GetProperty("source").GetProperty("uri").GetString());
        Assert.False(updatedBody.RootElement.GetProperty("source").GetProperty("preheat_enabled").GetBoolean());

        using var moveSource = CreateJsonRequest(
            HttpMethod.Patch,
            $"/api/sources/{sourceId}/move/",
            csrf,
            new { folder_id = (long?)null });
        using var movedSource = await client.SendAsync(moveSource);
        using var movedBody = await ReadJsonAsync(movedSource);
        Assert.Equal(HttpStatusCode.OK, movedSource.StatusCode);
        Assert.Equal(JsonValueKind.Null, movedBody.RootElement.GetProperty("source").GetProperty("folder_id").ValueKind);

        using var filtered = await client.GetAsync("/api/sources/?source_type=web&folder_id=-1");
        using var filteredBody = await ReadJsonAsync(filtered);
        Assert.Equal(HttpStatusCode.OK, filtered.StatusCode);
        Assert.Single(filteredBody.RootElement.GetProperty("sources").EnumerateArray());

        using var deleteSource = CreateJsonRequest(HttpMethod.Delete, $"/api/sources/{sourceId}/", csrf, new { });
        using var deletedSource = await client.SendAsync(deleteSource);
        Assert.Equal(HttpStatusCode.OK, deletedSource.StatusCode);

        using var deleteFolder = CreateJsonRequest(HttpMethod.Delete, $"/api/folders/{folderId}/", csrf, new { });
        using var deletedFolder = await client.SendAsync(deleteFolder);
        Assert.Equal(HttpStatusCode.OK, deletedFolder.StatusCode);
    }

    [Fact]
    public async Task UploadPreviewDownloadAndLocalPathBoundaryUsePlaybackHostFiles()
    {
        using var factory = new ControlHostApplicationFactory();
        using var client = factory.CreateHttpsClient();
        var csrf = await AuthenticateAsync(client);
        var imageBytes = Encoding.UTF8.GetBytes("contract-image");

        using var upload = new MultipartFormDataContent();
        using var fileContent = new ByteArrayContent(imageBytes);
        fileContent.Headers.ContentType = new System.Net.Http.Headers.MediaTypeHeaderValue("image/png");
        upload.Add(fileContent, "file", "poster.png");
        upload.Add(new StringContent("海报"), "name");
        using var uploadRequest = new HttpRequestMessage(HttpMethod.Post, "/api/sources/upload/") { Content = upload };
        uploadRequest.Headers.Add("X-CSRFToken", csrf);
        using var uploaded = await client.SendAsync(uploadRequest);
        using var uploadedBody = await ReadJsonAsync(uploaded);
        Assert.True(
            uploaded.StatusCode == HttpStatusCode.Created,
            $"期望 201，实际 {(int)uploaded.StatusCode}：{uploadedBody.RootElement.GetRawText()}");
        var uploadedSource = uploadedBody.RootElement.GetProperty("source");
        var sourceId = uploadedSource.GetProperty("id").GetInt64();
        var managedPath = uploadedSource.GetProperty("uri").GetString()!;
        Assert.True(File.Exists(managedPath));

        using var preview = await client.GetAsync($"/api/sources/{sourceId}/preview/");
        Assert.Equal(HttpStatusCode.OK, preview.StatusCode);
        Assert.Equal(imageBytes, await preview.Content.ReadAsByteArrayAsync());
        Assert.Null(preview.Content.Headers.ContentDisposition);

        using var download = await client.GetAsync($"/api/sources/{sourceId}/download/");
        Assert.Equal(HttpStatusCode.OK, download.StatusCode);
        Assert.Equal("poster.png", download.Content.Headers.ContentDisposition?.FileNameStar);
        Assert.Equal(imageBytes, await download.Content.ReadAsByteArrayAsync());

        var localPath = Path.Combine(factory.TemporaryRoot, "local.mp4");
        await File.WriteAllBytesAsync(localPath, [1, 2, 3, 4]);
        using var addLocal = CreateJsonRequest(
            HttpMethod.Post,
            "/api/sources/local/",
            csrf,
            new { path = localPath });
        using var local = await client.SendAsync(addLocal);
        Assert.Equal(HttpStatusCode.Created, local.StatusCode);

        var outsidePath = Path.Combine(
            Path.GetDirectoryName(factory.TemporaryRoot)!,
            $"outside-{Guid.NewGuid():N}.png");
        await File.WriteAllBytesAsync(outsidePath, [1]);
        try
        {
            using var addOutside = CreateJsonRequest(
                HttpMethod.Post,
                "/api/sources/local/",
                csrf,
                new { path = outsidePath });
            using var rejected = await client.SendAsync(addOutside);
            using var rejectedBody = await ReadJsonAsync(rejected);
            Assert.Equal(HttpStatusCode.BadRequest, rejected.StatusCode);
            Assert.Equal("media_error", rejectedBody.RootElement.GetProperty("code").GetString());
        }
        finally
        {
            File.Delete(outsidePath);
        }

        using var deleteUpload = CreateJsonRequest(HttpMethod.Delete, $"/api/sources/{sourceId}/", csrf, new { });
        using var deleted = await client.SendAsync(deleteUpload);
        Assert.Equal(HttpStatusCode.OK, deleted.StatusCode);
        Assert.False(File.Exists(managedPath));
        Assert.True(File.Exists(localPath));
    }

    private static async Task<string> AuthenticateAsync(HttpClient client)
    {
        using var csrfResponse = await client.GetAsync("/api/auth/csrf/");
        using var csrfBody = await ReadJsonAsync(csrfResponse);
        var csrf = csrfBody.RootElement.GetProperty("csrfToken").GetString()!;
        using var login = await client.PostAsJsonAsync(
            "/api/auth/login/",
            new { username = "operator", password = InitialPassword });
        login.EnsureSuccessStatusCode();
        return csrf;
    }

    private static HttpRequestMessage CreateJsonRequest(HttpMethod method, string path, string csrf, object body)
    {
        var request = new HttpRequestMessage(method, path) { Content = JsonContent.Create(body) };
        request.Headers.Add("X-CSRFToken", csrf);
        return request;
    }

    private static async Task<JsonDocument> ReadJsonAsync(HttpResponseMessage response) =>
        await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());
}
