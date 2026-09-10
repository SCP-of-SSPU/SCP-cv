using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using ScpCv.Domain.Model;
using ScpCv.Infrastructure.Persistence;

namespace ScpCv.ControlHost.Tests;

public sealed class PlaybackEndpointTests
{
    private const string InitialPassword = "Old-password-123";

    [Fact]
    public async Task RuntimeAndVolumeMutationsPreserveFourWindowPolicyAndResponseShape()
    {
        using var factory = new ControlHostApplicationFactory();
        using var client = factory.CreateHttpsClient();
        var csrf = await AuthenticateAsync(client);

        using var modeRequest = Request(HttpMethod.Patch, "/api/runtime/", csrf, new { big_screen_mode = "double" });
        using var modeResponse = await client.SendAsync(modeRequest);
        using var modeBody = await Json(modeResponse);
        Assert.Equal(HttpStatusCode.OK, modeResponse.StatusCode);
        Assert.Equal("double", modeBody.RootElement.GetProperty("runtime").GetProperty("big_screen_mode").GetString());
        Assert.Equal([3, 4], modeBody.RootElement.GetProperty("runtime").GetProperty("muted_windows").EnumerateArray().Select(item => item.GetInt32()));
        Assert.Equal(4, modeBody.RootElement.GetProperty("sessions").GetArrayLength());

        using var volumeRequest = Request(HttpMethod.Patch, "/api/volume/", csrf, new { level = 42, muted = true });
        using var volumeResponse = await client.SendAsync(volumeRequest);
        using var volumeBody = await Json(volumeResponse);
        Assert.Equal(HttpStatusCode.OK, volumeResponse.StatusCode);
        var volume = volumeBody.RootElement.GetProperty("volume");
        Assert.Equal(42, volume.GetProperty("level").GetInt32());
        Assert.True(volume.GetProperty("muted").GetBoolean());
        Assert.False(volume.GetProperty("system_synced").GetBoolean());
        Assert.Equal("runtime_state", volume.GetProperty("backend").GetString());
    }

    [Fact]
    public async Task AcceptedOpenDoesNotReportPlayingOrInferPresentationMode()
    {
        using var factory = new ControlHostApplicationFactory();
        using var client = factory.CreateHttpsClient();
        var sourceId = await SeedPresentationAsync(factory);
        var csrf = await AuthenticateAsync(client);

        using var openRequest = Request(
            HttpMethod.Post,
            "/api/playback/1/open/",
            csrf,
            new { source_id = sourceId, autoplay = true, target_slide = 2 });
        using var openResponse = await client.SendAsync(openRequest);
        using var body = await Json(openResponse);

        Assert.Equal(HttpStatusCode.OK, openResponse.StatusCode);
        var session = body.RootElement.GetProperty("sessions").EnumerateArray().Single(item => item.GetProperty("window_id").GetInt32() == 1);
        Assert.Equal("loading", session.GetProperty("playback_state").GetString());
        Assert.Equal(string.Empty, session.GetProperty("playback_mode").GetString());
        Assert.Equal("OPEN", session.GetProperty("pending_command").GetString());

        var contextFactory = factory.Services.GetRequiredService<IDbContextFactory<ControlDbContext>>();
        await using (var database = await contextFactory.CreateDbContextAsync())
        {
            var argsJson = await database.CommandRecords
                .Where(item => item.Command == "OPEN")
                .Select(item => item.ArgsJson)
                .SingleAsync();
            using var args = JsonDocument.Parse(argsJson);
            Assert.Equal("sha256:presentation", args.RootElement.GetProperty("content_digest").GetString());
            Assert.Equal("fallback.pdf", args.RootElement.GetProperty("fallback_uri").GetString());
            Assert.Equal("sha256:presentation", args.RootElement.GetProperty("fallback_digest").GetString());
            Assert.True(args.RootElement.GetProperty("fallback_fresh").GetBoolean());
        }

        using var closeRequest = Request(HttpMethod.Post, "/api/playback/1/close/", csrf, new { });
        using var closeResponse = await client.SendAsync(closeRequest);
        using var closeBody = await Json(closeResponse);
        Assert.Equal(HttpStatusCode.OK, closeResponse.StatusCode);
        var closed = closeBody.RootElement.GetProperty("sessions").EnumerateArray().Single(item => item.GetProperty("window_id").GetInt32() == 1);
        Assert.Equal(JsonValueKind.Null, closed.GetProperty("source_id").ValueKind);
        Assert.Equal("idle", closed.GetProperty("playback_state").GetString());
    }

    [Fact]
    public async Task DisplaysAndInvalidWindowsUseCompatibleShapes()
    {
        using var factory = new ControlHostApplicationFactory();
        using var client = factory.CreateHttpsClient();
        var csrf = await AuthenticateAsync(client);

        using var displays = await client.GetAsync("/api/displays/");
        using var displayBody = await Json(displays);
        Assert.Equal(HttpStatusCode.OK, displays.StatusCode);
        Assert.NotEmpty(displayBody.RootElement.GetProperty("targets").EnumerateArray());

        using var selectRequest = Request(
            HttpMethod.Post,
            "/api/displays/select/",
            csrf,
            new { window_id = 2, display_mode = "single", target_label = "模拟显示器" });
        using var selected = await client.SendAsync(selectRequest);
        using var selectedBody = await Json(selected);
        Assert.Equal(HttpStatusCode.OK, selected.StatusCode);
        Assert.Equal(
            "模拟显示器",
            selectedBody.RootElement.GetProperty("sessions").EnumerateArray()
                .Single(item => item.GetProperty("window_id").GetInt32() == 2)
                .GetProperty("target_display_label").GetString());

        using var invalid = await client.GetAsync("/api/sessions/9/");
        using var invalidBody = await Json(invalid);
        Assert.Equal(HttpStatusCode.BadRequest, invalid.StatusCode);
        Assert.Equal("invalid_window", invalidBody.RootElement.GetProperty("code").GetString());
    }

    private static async Task<long> SeedPresentationAsync(ControlHostApplicationFactory factory)
    {
        var contextFactory = factory.Services.GetRequiredService<IDbContextFactory<ControlDbContext>>();
        await using var database = await contextFactory.CreateDbContextAsync();
        var source = new MediaSource
        {
            SourceType = MediaSourceType.Presentation,
            Name = "演示",
            Uri = "presentation.pptx",
            IsAvailable = true,
            MetadataJson = "{\"slides_playback_mode\":\"pdf\",\"slides_pdf\":{\"status\":\"ready\",\"path\":\"fallback.pdf\",\"source_digest\":\"sha256:presentation\"}}",
            ContentDigest = "sha256:presentation",
            CreatedAt = DateTimeOffset.UtcNow,
        };
        database.MediaSources.Add(source);
        await database.SaveChangesAsync();
        return source.Id;
    }

    private static async Task<string> AuthenticateAsync(HttpClient client)
    {
        using var csrfResponse = await client.GetAsync("/api/auth/csrf/");
        using var csrfBody = await Json(csrfResponse);
        var csrf = csrfBody.RootElement.GetProperty("csrfToken").GetString()!;
        using var login = await client.PostAsJsonAsync(
            "/api/auth/login/",
            new { username = "operator", password = InitialPassword });
        login.EnsureSuccessStatusCode();
        return csrf;
    }

    private static HttpRequestMessage Request(HttpMethod method, string path, string csrf, object body)
    {
        var request = new HttpRequestMessage(method, path) { Content = JsonContent.Create(body) };
        request.Headers.Add("X-CSRFToken", csrf);
        return request;
    }

    private static async Task<JsonDocument> Json(HttpResponseMessage response) =>
        await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());
}
