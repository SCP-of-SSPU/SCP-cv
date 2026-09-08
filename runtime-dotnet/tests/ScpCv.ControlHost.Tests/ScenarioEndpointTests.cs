using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using ScpCv.Domain.Model;
using ScpCv.Infrastructure.Persistence;

namespace ScpCv.ControlHost.Tests;

public sealed class ScenarioEndpointTests
{
    private const string InitialPassword = "Old-password-123";

    [Fact]
    public async Task CrudAndPinPreserveCompatibleOrderingAndErrors()
    {
        using var factory = new ControlHostApplicationFactory();
        using var client = factory.CreateHttpsClient();
        var csrf = await AuthenticateAsync(client);

        var firstId = await CreateScenarioAsync(client, csrf, "第一预案");
        var secondId = await CreateScenarioAsync(client, csrf, "第二预案");

        using (var pinRequest = Request(HttpMethod.Post, $"/api/scenarios/{firstId}/pin/", csrf, new { }))
        using (var pinResponse = await client.SendAsync(pinRequest))
        using (var pinBody = await Json(pinResponse))
        {
            Assert.Equal(HttpStatusCode.OK, pinResponse.StatusCode);
            Assert.True(pinBody.RootElement.GetProperty("scenario").GetProperty("sort_order").GetInt32() > 0);
        }

        using (var listResponse = await client.GetAsync("/api/scenarios/"))
        using (var listBody = await Json(listResponse))
        {
            Assert.Equal(HttpStatusCode.OK, listResponse.StatusCode);
            var scenarios = listBody.RootElement.GetProperty("scenarios").EnumerateArray().ToArray();
            Assert.Equal(firstId, scenarios[0].GetProperty("id").GetInt64());
        }

        using (var patchRequest = Request(
            HttpMethod.Patch,
            $"/api/scenarios/{secondId}/",
            csrf,
            new { name = "更新预案", description = "更新说明", volume_state = "set", volume_level = 36 }))
        using (var patchResponse = await client.SendAsync(patchRequest))
        using (var patchBody = await Json(patchResponse))
        {
            Assert.Equal(HttpStatusCode.OK, patchResponse.StatusCode);
            var scenario = patchBody.RootElement.GetProperty("scenario");
            Assert.Equal("更新预案", scenario.GetProperty("name").GetString());
            Assert.Equal(36, scenario.GetProperty("volume_level").GetInt32());
        }

        using (var invalidRequest = Request(
            HttpMethod.Patch,
            $"/api/scenarios/{secondId}/",
            csrf,
            new { targets = "not-an-array" }))
        using (var invalidResponse = await client.SendAsync(invalidRequest))
        using (var invalidBody = await Json(invalidResponse))
        {
            Assert.Equal(HttpStatusCode.BadRequest, invalidResponse.StatusCode);
            Assert.Equal("scenario_error", invalidBody.RootElement.GetProperty("code").GetString());
        }

        using (var deleteRequest = Request(HttpMethod.Delete, $"/api/scenarios/{secondId}/", csrf, new { }))
        using (var deleteResponse = await client.SendAsync(deleteRequest))
        {
            Assert.Equal(HttpStatusCode.OK, deleteResponse.StatusCode);
        }

        using var missingResponse = await client.GetAsync($"/api/scenarios/{secondId}/");
        Assert.Equal(HttpStatusCode.NotFound, missingResponse.StatusCode);
    }

    [Fact]
    public async Task CaptureStoresRuntimeAndAllFourWindowStates()
    {
        using var factory = new ControlHostApplicationFactory();
        using var client = factory.CreateHttpsClient();
        var sourceId = await SeedSourceAsync(factory, "捕获源");
        var csrf = await AuthenticateAsync(client);

        using (var runtimeRequest = Request(HttpMethod.Patch, "/api/runtime/", csrf, new { big_screen_mode = "double" }))
        using (var runtimeResponse = await client.SendAsync(runtimeRequest))
        {
            runtimeResponse.EnsureSuccessStatusCode();
        }

        using (var volumeRequest = Request(HttpMethod.Patch, "/api/volume/", csrf, new { level = 43 }))
        using (var volumeResponse = await client.SendAsync(volumeRequest))
        {
            volumeResponse.EnsureSuccessStatusCode();
        }

        using (var openRequest = Request(HttpMethod.Post, "/api/playback/1/open/", csrf, new { source_id = sourceId }))
        using (var openResponse = await client.SendAsync(openRequest))
        {
            openResponse.EnsureSuccessStatusCode();
        }

        using var captureRequest = Request(
            HttpMethod.Post,
            "/api/scenarios/capture/",
            csrf,
            new { name = "当前状态", description = "四窗捕获" });
        using var captureResponse = await client.SendAsync(captureRequest);
        using var captureBody = await Json(captureResponse);

        Assert.Equal(HttpStatusCode.OK, captureResponse.StatusCode);
        var scenario = captureBody.RootElement.GetProperty("scenario");
        Assert.Equal("set", scenario.GetProperty("big_screen_mode_state").GetString());
        Assert.Equal("double", scenario.GetProperty("big_screen_mode").GetString());
        Assert.Equal("set", scenario.GetProperty("volume_state").GetString());
        Assert.Equal(43, scenario.GetProperty("volume_level").GetInt32());
        var targets = scenario.GetProperty("targets").EnumerateArray().OrderBy(TargetWindow).ToArray();
        Assert.Equal(4, targets.Length);
        Assert.Equal("set", targets[0].GetProperty("source_state").GetString());
        Assert.Equal(sourceId, targets[0].GetProperty("source_id").GetInt64());
        Assert.All(targets[1..], target => Assert.Equal("empty", target.GetProperty("source_state").GetString()));
    }

    [Fact]
    public async Task ActivateHonorsUnsetEmptySetResumeAndAutoplayWithoutInferringPlaybackMode()
    {
        using var factory = new ControlHostApplicationFactory();
        using var client = factory.CreateHttpsClient();
        var firstSourceId = await SeedSourceAsync(factory, "原源");
        var secondSourceId = await SeedSourceAsync(factory, "新源");
        await SeedActiveSessionsAsync(factory, firstSourceId);
        var csrf = await AuthenticateAsync(client);

        using var createRequest = Request(
            HttpMethod.Post,
            "/api/scenarios/",
            csrf,
            new
            {
                name = "三态激活",
                big_screen_mode_state = "set",
                big_screen_mode = "double",
                volume_state = "set",
                volume_level = 55,
                targets = new object[]
                {
                    new { window_id = 1, source_state = "unset", source_id = (long?)null, autoplay = true, resume = true },
                    new { window_id = 2, source_state = "empty", source_id = (long?)null, autoplay = true, resume = true },
                    new { window_id = 3, source_state = "set", source_id = secondSourceId, autoplay = false, resume = false },
                    new { window_id = 4, source_state = "set", source_id = firstSourceId, autoplay = true, resume = true },
                },
            });
        using var createResponse = await client.SendAsync(createRequest);
        using var createBody = await Json(createResponse);
        var scenarioId = createBody.RootElement.GetProperty("scenario").GetProperty("id").GetInt64();

        using var activateRequest = Request(HttpMethod.Post, $"/api/scenarios/{scenarioId}/activate/", csrf, new { });
        using var activateResponse = await client.SendAsync(activateRequest);
        using var activateBody = await Json(activateResponse);

        Assert.Equal(HttpStatusCode.OK, activateResponse.StatusCode);
        var sessions = activateBody.RootElement.GetProperty("sessions").EnumerateArray().ToDictionary(SessionWindow);
        Assert.Equal("playing", sessions[1].GetProperty("playback_state").GetString());
        Assert.Equal("pdf", sessions[1].GetProperty("playback_mode").GetString());
        Assert.Equal(10, await DesiredGenerationAsync(factory, 1));

        Assert.Equal(JsonValueKind.Null, sessions[2].GetProperty("source_id").ValueKind);
        Assert.Equal("idle", sessions[2].GetProperty("playback_state").GetString());
        Assert.Equal("CLOSE", sessions[2].GetProperty("pending_command").GetString());

        Assert.Equal(secondSourceId, sessions[3].GetProperty("source_id").GetInt64());
        Assert.Equal("loading", sessions[3].GetProperty("playback_state").GetString());
        Assert.Equal(string.Empty, sessions[3].GetProperty("playback_mode").GetString());
        Assert.Equal("OPEN", sessions[3].GetProperty("pending_command").GetString());
        Assert.False((await CommandArgsAsync(factory, 3)).GetProperty("autoplay").GetBoolean());

        Assert.Equal(firstSourceId, sessions[4].GetProperty("source_id").GetInt64());
        Assert.Equal("paused", sessions[4].GetProperty("playback_state").GetString());
        Assert.Equal("pdf", sessions[4].GetProperty("playback_mode").GetString());
        Assert.Equal(40, await DesiredGenerationAsync(factory, 4));

        using var runtimeResponse = await client.GetAsync("/api/runtime/");
        using var runtimeBody = await Json(runtimeResponse);
        Assert.Equal("double", runtimeBody.RootElement.GetProperty("runtime").GetProperty("big_screen_mode").GetString());
        Assert.Equal(55, runtimeBody.RootElement.GetProperty("runtime").GetProperty("volume_level").GetInt32());
    }

    private static async Task<long> CreateScenarioAsync(HttpClient client, string csrf, string name)
    {
        using var request = Request(HttpMethod.Post, "/api/scenarios/", csrf, new { name });
        using var response = await client.SendAsync(request);
        using var body = await Json(response);
        Assert.Equal(HttpStatusCode.Created, response.StatusCode);
        return body.RootElement.GetProperty("scenario").GetProperty("id").GetInt64();
    }

    private static async Task<long> SeedSourceAsync(ControlHostApplicationFactory factory, string name)
    {
        var contextFactory = factory.Services.GetRequiredService<IDbContextFactory<ControlDbContext>>();
        await using var database = await contextFactory.CreateDbContextAsync();
        var source = new MediaSource
        {
            SourceType = MediaSourceType.Presentation,
            Name = name,
            Uri = $"{name}.pptx",
            IsAvailable = true,
            CreatedAt = DateTimeOffset.UtcNow,
        };
        database.MediaSources.Add(source);
        await database.SaveChangesAsync();
        return source.Id;
    }

    private static async Task SeedActiveSessionsAsync(ControlHostApplicationFactory factory, long sourceId)
    {
        var contextFactory = factory.Services.GetRequiredService<IDbContextFactory<ControlDbContext>>();
        await using var database = await contextFactory.CreateDbContextAsync();
        var sessions = await database.PlaybackSessions.OrderBy(item => item.WindowId).ToArrayAsync();
        foreach (var session in sessions)
        {
            session.MediaSourceId = sourceId;
            session.PlaybackMode = PlaybackMode.Pdf;
            session.PlaybackState = session.WindowId == 4 ? PlaybackState.Paused : PlaybackState.Playing;
            session.DesiredGeneration = session.WindowId * 10;
        }
        await database.SaveChangesAsync();
    }

    private static async Task<long> DesiredGenerationAsync(ControlHostApplicationFactory factory, int windowId)
    {
        var contextFactory = factory.Services.GetRequiredService<IDbContextFactory<ControlDbContext>>();
        await using var database = await contextFactory.CreateDbContextAsync();
        return await database.PlaybackSessions.Where(item => item.WindowId == windowId)
            .Select(item => item.DesiredGeneration).SingleAsync();
    }

    private static async Task<JsonElement> CommandArgsAsync(ControlHostApplicationFactory factory, int windowId)
    {
        var contextFactory = factory.Services.GetRequiredService<IDbContextFactory<ControlDbContext>>();
        await using var database = await contextFactory.CreateDbContextAsync();
        var json = await database.PlaybackSessions.Where(item => item.WindowId == windowId)
            .Select(item => item.CommandArgsJson).SingleAsync();
        return JsonDocument.Parse(json).RootElement.Clone();
    }

    private static int TargetWindow(JsonElement target) => target.GetProperty("window_id").GetInt32();
    private static int SessionWindow(JsonElement session) => session.GetProperty("window_id").GetInt32();

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
