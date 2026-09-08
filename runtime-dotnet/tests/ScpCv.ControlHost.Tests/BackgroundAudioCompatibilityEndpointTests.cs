using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using ScpCv.Domain.Model;
using ScpCv.Infrastructure.Persistence;

namespace ScpCv.ControlHost.Tests;

public sealed class BackgroundAudioCompatibilityEndpointTests
{
    private const string InitialPassword = "Old-password-123";

    [Fact]
    public async Task SnapshotIncludesNestedSourceAndOrderedPlaylist()
    {
        using var factory = new ControlHostApplicationFactory();
        using var client = factory.CreateHttpsClient();
        var sourceIds = await SeedAudioSourcesAsync(factory);
        await SeedAudioSnapshotAsync(factory, sourceIds);
        await AuthenticateAsync(client);

        using var response = await client.GetAsync("/api/background-audio/");
        using var body = await Json(response);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var snapshot = body.RootElement.GetProperty("background_audio");
        var state = snapshot.GetProperty("state");
        Assert.Equal(sourceIds[0], state.GetProperty("source_id").GetInt64());
        Assert.Equal(sourceIds[0], state.GetProperty("source").GetProperty("id").GetInt64());
        Assert.Equal("播放中", state.GetProperty("playback_state_label").GetString());
        var playlist = snapshot.GetProperty("playlist").EnumerateArray().ToArray();
        Assert.Equal([sourceIds[1], sourceIds[0]], playlist.Select(SourceId));
        Assert.Equal(sourceIds[1], playlist[0].GetProperty("source").GetProperty("id").GetInt64());
    }

    [Fact]
    public async Task PlaySourcePersistsOpenIntentWithoutReportingActualPlayback()
    {
        using var factory = new ControlHostApplicationFactory();
        using var client = factory.CreateHttpsClient();
        var sourceIds = await SeedAudioSourcesAsync(factory);
        var csrf = await AuthenticateAsync(client);

        using var request = Request(
            HttpMethod.Post,
            "/api/background-audio/play-source/",
            csrf,
            new { source_id = sourceIds[1] });
        using var response = await client.SendAsync(request);
        using var body = await Json(response);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var snapshot = body.RootElement.GetProperty("background_audio");
        var state = snapshot.GetProperty("state");
        Assert.Equal(sourceIds[1], state.GetProperty("source_id").GetInt64());
        Assert.Equal("loading", state.GetProperty("playback_state").GetString());
        Assert.Equal("OPEN", state.GetProperty("pending_command").GetString());
        Assert.Single(snapshot.GetProperty("playlist").EnumerateArray());
    }

    [Fact]
    public async Task PlaySourceRejectsNonAudioMediaWithoutChangingState()
    {
        using var factory = new ControlHostApplicationFactory();
        using var client = factory.CreateHttpsClient();
        var sourceId = await SeedNonAudioSourceAsync(factory);
        var csrf = await AuthenticateAsync(client);

        using var request = Request(
            HttpMethod.Post,
            "/api/background-audio/play-source/",
            csrf,
            new { source_id = sourceId });
        using var response = await client.SendAsync(request);
        using var body = await Json(response);

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal("background_audio_error", body.RootElement.GetProperty("code").GetString());
        var contextFactory = factory.Services.GetRequiredService<IDbContextFactory<ControlDbContext>>();
        await using var database = await contextFactory.CreateDbContextAsync();
        Assert.Null((await database.BackgroundAudioStates.SingleAsync()).CurrentSourceId);
    }

    private static async Task<long[]> SeedAudioSourcesAsync(ControlHostApplicationFactory factory)
    {
        var contextFactory = factory.Services.GetRequiredService<IDbContextFactory<ControlDbContext>>();
        await using var database = await contextFactory.CreateDbContextAsync();
        var sources = new[]
        {
            NewSource("第一首", "first.mp3", MediaSourceType.Audio),
            NewSource("第二首", "second.mp3", MediaSourceType.Audio),
        };
        database.MediaSources.AddRange(sources);
        await database.SaveChangesAsync();
        return sources.Select(source => source.Id).ToArray();
    }

    private static async Task<long> SeedNonAudioSourceAsync(ControlHostApplicationFactory factory)
    {
        var contextFactory = factory.Services.GetRequiredService<IDbContextFactory<ControlDbContext>>();
        await using var database = await contextFactory.CreateDbContextAsync();
        var source = NewSource("图片", "cover.png", MediaSourceType.Image);
        database.MediaSources.Add(source);
        await database.SaveChangesAsync();
        return source.Id;
    }

    private static async Task SeedAudioSnapshotAsync(ControlHostApplicationFactory factory, long[] sourceIds)
    {
        var contextFactory = factory.Services.GetRequiredService<IDbContextFactory<ControlDbContext>>();
        await using var database = await contextFactory.CreateDbContextAsync();
        var state = await database.BackgroundAudioStates.SingleAsync();
        state.CurrentSourceId = sourceIds[0];
        state.PlaybackState = PlaybackState.Playing;
        state.PositionMs = 1234;
        database.BackgroundAudioPlaylistItems.AddRange(
            new BackgroundAudioPlaylistItem
            {
                SourceId = sourceIds[0],
                SortOrder = 2,
                CreatedAt = DateTimeOffset.UtcNow,
            },
            new BackgroundAudioPlaylistItem
            {
                SourceId = sourceIds[1],
                SortOrder = 1,
                CreatedAt = DateTimeOffset.UtcNow,
            });
        await database.SaveChangesAsync();
    }

    private static MediaSource NewSource(string name, string uri, MediaSourceType type) => new()
    {
        SourceType = type,
        Name = name,
        Uri = uri,
        IsAvailable = true,
        CreatedAt = DateTimeOffset.UtcNow,
    };

    private static long SourceId(JsonElement item) => item.GetProperty("source_id").GetInt64();

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
