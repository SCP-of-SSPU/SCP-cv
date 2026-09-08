using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using ScpCv.Domain.Model;
using ScpCv.Infrastructure.Persistence;

namespace ScpCv.ControlHost.Tests;

public sealed class LegacyHttpContractTests
{
    private const string InitialPassword = "Old-password-123";

    [Theory]
    [InlineData("/api/folders/")]
    [InlineData("/api/sources/")]
    [InlineData("/api/sessions/")]
    [InlineData("/api/runtime/")]
    [InlineData("/api/volume/")]
    [InlineData("/api/scenarios/")]
    [InlineData("/api/devices/")]
    [InlineData("/api/background-audio/")]
    public async Task BusinessReadsRequireTheCompatibleSession(string path)
    {
        using var factory = new ControlHostApplicationFactory();
        using var client = factory.CreateHttpsClient();

        using var response = await client.GetAsync(path);
        using var body = await ReadJsonAsync(response);

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
        AssertObjectHasExactly(body.RootElement, "detail", "code");
        Assert.Equal("unauthorized", body.RootElement.GetProperty("code").GetString());
    }

    [Fact]
    public async Task AuthenticatedReadsPreserveLegacyTopLevelAndEntityShapes()
    {
        using var factory = new ControlHostApplicationFactory();
        using var client = factory.CreateHttpsClient();
        await SeedLegacyFixtureAsync(factory);
        await LoginAsync(client);

        using (var response = await client.GetAsync("/api/folders/"))
        using (var body = await ReadJsonAsync(response))
        {
            Assert.Equal(HttpStatusCode.OK, response.StatusCode);
            AssertObjectHasExactly(body.RootElement, "success", "folders");
            var folder = Assert.Single(body.RootElement.GetProperty("folders").EnumerateArray());
            AssertObjectHasExactly(folder, "id", "name", "parent_id", "created_at", "updated_at");
        }

        using (var response = await client.GetAsync("/api/sources/"))
        using (var body = await ReadJsonAsync(response))
        {
            Assert.Equal(HttpStatusCode.OK, response.StatusCode);
            AssertObjectHasExactly(body.RootElement, "success", "sources", "sync_result");
            Assert.Equal(JsonValueKind.Object, body.RootElement.GetProperty("sync_result").ValueKind);
            var source = Assert.Single(body.RootElement.GetProperty("sources").EnumerateArray());
            AssertObjectHasExactly(
                source,
                "id", "source_type", "name", "uri", "is_available", "stream_identifier", "folder_id",
                "original_filename", "file_size", "mime_type", "is_temporary", "expires_at", "metadata",
                "keep_alive", "preheat_enabled", "playback_mode", "created_at", "preview_url",
                "thumbnail_url", "preview_kind", "preview_label");
            Assert.Equal("ppt", source.GetProperty("source_type").GetString());
            Assert.Equal("pdf", source.GetProperty("playback_mode").GetString());
        }

        using (var response = await client.GetAsync("/api/sessions/"))
        using (var body = await ReadJsonAsync(response))
        {
            Assert.Equal(HttpStatusCode.OK, response.StatusCode);
            AssertObjectHasExactly(body.RootElement, "success", "sessions");
            var sessions = body.RootElement.GetProperty("sessions").EnumerateArray().ToArray();
            Assert.Equal(4, sessions.Length);
            Assert.Equal([1, 2, 3, 4], sessions.Select(item => item.GetProperty("window_id").GetInt32()));
            AssertPlaybackSessionShape(sessions[0]);
            Assert.Equal("pdf", sessions[0].GetProperty("playback_mode").GetString());
        }

        using (var response = await client.GetAsync("/api/sessions/1/"))
        using (var body = await ReadJsonAsync(response))
        {
            Assert.Equal(HttpStatusCode.OK, response.StatusCode);
            AssertObjectHasExactly(body.RootElement, "success", "session");
            AssertPlaybackSessionShape(body.RootElement.GetProperty("session"));
        }

        using (var response = await client.GetAsync("/api/runtime/"))
        using (var body = await ReadJsonAsync(response))
        {
            Assert.Equal(HttpStatusCode.OK, response.StatusCode);
            AssertObjectHasExactly(body.RootElement, "success", "runtime");
            AssertObjectHasExactly(
                body.RootElement.GetProperty("runtime"),
                "big_screen_mode", "volume_level", "muted_windows");
        }

        using (var response = await client.GetAsync("/api/volume/"))
        using (var body = await ReadJsonAsync(response))
        {
            Assert.Equal(HttpStatusCode.OK, response.StatusCode);
            AssertObjectHasExactly(body.RootElement, "success", "volume");
            AssertObjectHasExactly(
                body.RootElement.GetProperty("volume"),
                "level", "muted", "system_synced", "backend");
        }

        using (var response = await client.GetAsync("/api/scenarios/"))
        using (var body = await ReadJsonAsync(response))
        {
            Assert.Equal(HttpStatusCode.OK, response.StatusCode);
            AssertObjectHasExactly(body.RootElement, "success", "scenarios");
            var scenario = Assert.Single(body.RootElement.GetProperty("scenarios").EnumerateArray());
            AssertObjectHasExactly(
                scenario,
                "id", "name", "description", "sort_order", "big_screen_mode_state", "big_screen_mode",
                "big_screen_mode_label", "volume_state", "volume_level", "targets", "window1_source_id",
                "window1_source_name", "window1_autoplay", "window1_resume", "window2_source_id",
                "window2_source_name", "window2_autoplay", "window2_resume", "created_at", "updated_at");
        }

        using (var response = await client.GetAsync("/api/devices/"))
        using (var body = await ReadJsonAsync(response))
        {
            Assert.Equal(HttpStatusCode.OK, response.StatusCode);
            AssertObjectHasExactly(body.RootElement, "success", "devices");
            var devices = body.RootElement.GetProperty("devices").EnumerateArray().ToArray();
            Assert.Equal(3, devices.Length);
            Assert.All(devices, device => AssertObjectHasExactly(
                device,
                "name", "device_type", "device_type_label", "host", "port", "action", "detail"));
        }

        using (var response = await client.GetAsync("/api/background-audio/"))
        using (var body = await ReadJsonAsync(response))
        {
            Assert.Equal(HttpStatusCode.OK, response.StatusCode);
            AssertObjectHasExactly(body.RootElement, "success", "background_audio");
            var backgroundAudio = body.RootElement.GetProperty("background_audio");
            AssertObjectHasExactly(backgroundAudio, "state", "playlist");
            AssertObjectHasExactly(
                backgroundAudio.GetProperty("state"),
                "id", "source_id", "source_name", "source_uri", "source", "current_item_id",
                "playback_state", "playback_state_label", "error_message", "position_ms", "duration_ms",
                "volume", "is_muted", "loop_enabled", "pending_command", "updated_at");
            var item = Assert.Single(backgroundAudio.GetProperty("playlist").EnumerateArray());
            AssertObjectHasExactly(item, "id", "source_id", "source_name", "sort_order", "created_at", "source");
        }
    }

    [Theory]
    [InlineData("/api/sources/local/", "missing_path")]
    [InlineData("/api/sources/web/", "missing_url")]
    [InlineData("/api/scenarios/create/", "missing_name")]
    [InlineData("/api/background-audio/play-source/", "invalid_source")]
    public async Task RepresentativeInvalidWritesPreserveLegacyErrorShape(string path, string expectedCode)
    {
        using var factory = new ControlHostApplicationFactory();
        using var client = factory.CreateHttpsClient();
        var csrfToken = await GetCsrfTokenAsync(client);
        await LoginAsync(client);
        using var request = CreateJsonRequest(HttpMethod.Post, path, csrfToken, new { });

        using var response = await client.SendAsync(request);
        using var body = await ReadJsonAsync(response);

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        AssertObjectHasExactly(body.RootElement, "detail", "code");
        Assert.Equal(expectedCode, body.RootElement.GetProperty("code").GetString());
    }

    [Fact]
    public async Task UnknownDevicePreservesNotFoundErrorContractWithoutSendingNetworkTraffic()
    {
        using var factory = new ControlHostApplicationFactory();
        using var client = factory.CreateHttpsClient();
        var csrfToken = await GetCsrfTokenAsync(client);
        await LoginAsync(client);
        using var request = CreateJsonRequest(
            HttpMethod.Post,
            "/api/devices/not-configured/toggle/",
            csrfToken,
            new { });

        using var response = await client.SendAsync(request);
        using var body = await ReadJsonAsync(response);

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
        AssertObjectHasExactly(body.RootElement, "detail", "code");
        Assert.Equal("device_error", body.RootElement.GetProperty("code").GetString());
    }

    private static async Task SeedLegacyFixtureAsync(ControlHostApplicationFactory factory)
    {
        var contextFactory = factory.Services.GetRequiredService<IDbContextFactory<ControlDbContext>>();
        await using var database = await contextFactory.CreateDbContextAsync();
        var timestamp = new DateTimeOffset(2026, 9, 8, 8, 0, 0, TimeSpan.Zero);
        var folder = new MediaFolder
        {
            Name = "演示资料",
            CreatedAt = timestamp,
            UpdatedAt = timestamp,
        };
        var source = new MediaSource
        {
            SourceType = MediaSourceType.Presentation,
            Name = "季度汇报",
            Uri = "media/quarterly.pptx",
            UploadedFile = "media/quarterly.pptx",
            IsAvailable = true,
            Folder = folder,
            OriginalFilename = "quarterly.pptx",
            FileSize = 4096,
            MimeType = "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            MetadataJson = "{\"slides_playback_mode\":\"pdf\",\"custom\":\"preserved\"}",
            KeepAlive = true,
            SourceRevision = 1,
            ContentDigest = new string('a', 64),
            CreatedAt = timestamp,
        };
        var scenario = new Scenario
        {
            Name = "开场",
            Description = "合同测试",
            SortOrder = 1,
            BigScreenModeState = ScenarioValueState.Set,
            BigScreenMode = BigScreenMode.Single,
            VolumeState = ScenarioValueState.Set,
            VolumeLevel = 80,
            TargetsJson = "[{\"window_id\":1,\"source_state\":\"set\",\"source_id\":0,\"autoplay\":true,\"resume\":true}]",
            CreatedAt = timestamp,
            UpdatedAt = timestamp,
        };
        database.MediaFolders.Add(folder);
        database.MediaSources.Add(source);
        database.Scenarios.Add(scenario);
        await database.SaveChangesAsync();

        scenario.TargetsJson = $"[{{\"window_id\":1,\"source_state\":\"set\",\"source_id\":{source.Id},\"autoplay\":true,\"resume\":true}}]";
        var session = await database.PlaybackSessions.SingleAsync(item => item.WindowId == 1);
        session.MediaSourceId = source.Id;
        session.PlaybackMode = PlaybackMode.Pdf;
        session.PlaybackState = PlaybackState.Playing;
        session.CurrentSlide = 2;
        session.TotalSlides = 5;
        session.LastUpdatedAt = timestamp;
        var audio = await database.BackgroundAudioStates.SingleAsync();
        audio.CurrentSourceId = source.Id;
        audio.UpdatedAt = timestamp;
        database.BackgroundAudioPlaylistItems.Add(new BackgroundAudioPlaylistItem
        {
            StateId = BackgroundAudioState.SingletonId,
            SourceId = source.Id,
            SortOrder = 1,
            CreatedAt = timestamp,
        });
        await database.SaveChangesAsync();
    }

    private static void AssertPlaybackSessionShape(JsonElement session) => AssertObjectHasExactly(
        session,
        "window_id", "session_id", "source_id", "source_name", "source_type", "source_type_label",
        "source_uri", "playback_mode", "playback_state", "playback_state_label", "error_message",
        "display_mode", "display_mode_label", "target_display_label", "current_slide", "total_slides",
        "position_ms", "duration_ms", "pending_command", "player_online", "player_last_seen_at",
        "last_updated_at", "volume", "is_muted", "loop_enabled");

    private static void AssertObjectHasExactly(JsonElement element, params string[] expectedNames)
    {
        Assert.Equal(JsonValueKind.Object, element.ValueKind);
        var actualNames = element.EnumerateObject().Select(property => property.Name).ToHashSet(StringComparer.Ordinal);
        Assert.True(
            actualNames.SetEquals(expectedNames),
            $"JSON 属性不匹配。期望：{string.Join(", ", expectedNames.Order())}；实际：{string.Join(", ", actualNames.Order())}");
    }

    private static async Task<string> GetCsrfTokenAsync(HttpClient client)
    {
        using var response = await client.GetAsync("/api/auth/csrf/");
        using var body = await ReadJsonAsync(response);
        return body.RootElement.GetProperty("csrfToken").GetString()!;
    }

    private static async Task LoginAsync(HttpClient client)
    {
        using var response = await client.PostAsJsonAsync(
            "/api/auth/login/",
            new { username = "operator", password = InitialPassword });
        response.EnsureSuccessStatusCode();
    }

    private static HttpRequestMessage CreateJsonRequest(HttpMethod method, string path, string csrfToken, object body)
    {
        var request = new HttpRequestMessage(method, path)
        {
            Content = JsonContent.Create(body),
        };
        request.Headers.Add("X-CSRFToken", csrfToken);
        return request;
    }

    private static async Task<JsonDocument> ReadJsonAsync(HttpResponseMessage response) =>
        await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());
}
