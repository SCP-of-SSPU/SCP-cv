using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using ScpCv.Domain.Model;
using ScpCv.Infrastructure.Persistence;

namespace ScpCv.ControlHost.Tests;

public sealed class RuntimeIntentQueueTests
{
    private const string InitialPassword = "Old-password-123";

    [Fact]
    public async Task DisplayOpenAndNavigationArePersistedBeforeReturningAcceptedProjection()
    {
        using var factory = new ControlHostApplicationFactory();
        using var client = factory.CreateHttpsClient();
        var sourceId = await SeedSourceAsync(factory, MediaSourceType.Presentation, sourceRevision: 7);
        var csrf = await AuthenticateAsync(client);

        using (var openRequest = Request(
            HttpMethod.Post,
            "/api/playback/1/open/",
            csrf,
            new { source_id = sourceId, autoplay = true, target_slide = 2 }))
        using (var openResponse = await client.SendAsync(openRequest))
        {
            Assert.Equal(HttpStatusCode.OK, openResponse.StatusCode);
        }

        using (var nextRequest = Request(
            HttpMethod.Post,
            "/api/playback/1/navigate/",
            csrf,
            new { action = "next" }))
        using (var nextResponse = await client.SendAsync(nextRequest))
        {
            Assert.Equal(HttpStatusCode.OK, nextResponse.StatusCode);
        }

        await using var database = await ContextAsync(factory);
        var commands = await database.CommandRecords
            .Where(command => command.TargetKind == CommandTargetKind.Display && command.TargetId == 1)
            .OrderBy(command => command.TargetSequence)
            .ToArrayAsync();
        Assert.Equal(["OPEN", "NEXT"], commands.Select(command => command.Command));
        Assert.Equal([1L, 2L], commands.Select(command => command.TargetSequence));
        Assert.Equal(1, commands[0].SourceGeneration);
        Assert.Equal(7, commands[0].SourceRevision);
        Assert.Equal(sourceId, JsonDocument.Parse(commands[0].ArgsJson).RootElement.GetProperty("source_id").GetInt64());

        var session = await database.PlaybackSessions.SingleAsync(item => item.WindowId == 1);
        Assert.Equal("OPEN", session.PendingCommand);
        Assert.Equal(commands[0].ArgsJson, session.CommandArgsJson);
    }

    [Fact]
    public async Task AudioWritesUseOrderedDurableQueueAndOpenDoesNotSupersedeRelativeCommands()
    {
        using var factory = new ControlHostApplicationFactory();
        using var client = factory.CreateHttpsClient();
        var sourceId = await SeedSourceAsync(factory, MediaSourceType.Audio, sourceRevision: 3);
        var csrf = await AuthenticateAsync(client);

        using (var playRequest = Request(
            HttpMethod.Post,
            "/api/background-audio/play-source/",
            csrf,
            new { source_id = sourceId }))
        using (var playResponse = await client.SendAsync(playRequest))
        {
            Assert.Equal(HttpStatusCode.OK, playResponse.StatusCode);
        }

        using (var nextRequest = Request(
            HttpMethod.Post,
            "/api/background-audio/control/",
            csrf,
            new { action = "next" }))
        using (var nextResponse = await client.SendAsync(nextRequest))
        {
            Assert.Equal(HttpStatusCode.OK, nextResponse.StatusCode);
        }

        await using var database = await ContextAsync(factory);
        var commands = await database.CommandRecords
            .Where(command => command.TargetKind == CommandTargetKind.Audio && command.TargetId == 1)
            .OrderBy(command => command.TargetSequence)
            .ToArrayAsync();
        Assert.Equal(["OPEN", "OPEN"], commands.Select(command => command.Command));
        Assert.All(commands, command => Assert.Equal(CommandStatus.Pending, command.Status));
        Assert.Equal([1L, 2L], commands.Select(command => command.SourceGeneration));
        Assert.Equal(3, commands[0].SourceRevision);

        var state = await database.BackgroundAudioStates.SingleAsync();
        Assert.Equal("OPEN", state.PendingCommand);
        Assert.Equal(commands[0].ArgsJson, state.CommandArgsJson);
    }

    [Fact]
    public async Task ScenarioActivationCreatesOneDurableCommandForEveryChangedDisplay()
    {
        using var factory = new ControlHostApplicationFactory();
        using var client = factory.CreateHttpsClient();
        var sourceId = await SeedSourceAsync(factory, MediaSourceType.Image, sourceRevision: 5);
        var csrf = await AuthenticateAsync(client);

        using var createRequest = Request(
            HttpMethod.Post,
            "/api/scenarios/",
            csrf,
            new
            {
                name = "队列预案",
                targets = new object[]
                {
                    new { window_id = 1, source_state = "empty" },
                    new { window_id = 2, source_state = "set", source_id = sourceId, autoplay = true, resume = false },
                },
            });
        using var createResponse = await client.SendAsync(createRequest);
        using var createBody = await JsonDocument.ParseAsync(await createResponse.Content.ReadAsStreamAsync());
        var scenarioId = createBody.RootElement.GetProperty("scenario").GetProperty("id").GetInt64();

        using var activateRequest = Request(HttpMethod.Post, $"/api/scenarios/{scenarioId}/activate/", csrf, new { });
        using var activateResponse = await client.SendAsync(activateRequest);
        Assert.Equal(HttpStatusCode.OK, activateResponse.StatusCode);

        await using var database = await ContextAsync(factory);
        var commands = await database.CommandRecords
            .Where(command => command.TargetKind == CommandTargetKind.Display)
            .OrderBy(command => command.TargetId)
            .ToArrayAsync();
        Assert.Equal(2, commands.Length);
        Assert.Collection(
            commands,
            command =>
            {
                Assert.Equal(1, command.TargetId);
                Assert.Equal("CLOSE", command.Command);
            },
            command =>
            {
                Assert.Equal(2, command.TargetId);
                Assert.Equal("OPEN", command.Command);
                Assert.Equal(5, command.SourceRevision);
            });
    }

    [Fact]
    public async Task BigScreenModeChangePersistsRequiredWindowMuteCommand()
    {
        using var factory = new ControlHostApplicationFactory();
        using var client = factory.CreateHttpsClient();
        var csrf = await AuthenticateAsync(client);

        using var request = Request(
            HttpMethod.Patch,
            "/api/runtime/",
            csrf,
            new { big_screen_mode = "double" });
        using var response = await client.SendAsync(request);
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);

        await using var database = await ContextAsync(factory);
        var commands = await database.CommandRecords
            .Where(candidate => candidate.TargetKind == CommandTargetKind.Display)
            .OrderBy(candidate => candidate.TargetId)
            .ToArrayAsync();
        Assert.Equal([3, 4], commands.Select(command => command.TargetId));
        Assert.All(commands, command =>
        {
            Assert.Equal("SET_MUTE", command.Command);
            Assert.True(JsonDocument.Parse(command.ArgsJson).RootElement.GetProperty("muted").GetBoolean());
        });
        var sessions = await database.PlaybackSessions
            .Where(candidate => candidate.WindowId >= 3)
            .OrderBy(candidate => candidate.WindowId)
            .ToArrayAsync();
        Assert.All(sessions, session =>
        {
            Assert.Equal("SET_MUTE", session.PendingCommand);
            Assert.True(session.IsMuted);
        });
    }

    private static async Task<long> SeedSourceAsync(
        ControlHostApplicationFactory factory,
        MediaSourceType type,
        long sourceRevision)
    {
        await using var database = await ContextAsync(factory);
        var source = new MediaSource
        {
            SourceType = type,
            Name = $"队列测试-{type}",
            Uri = $"queue-test-{type.ToString().ToLowerInvariant()}",
            IsAvailable = true,
            SourceRevision = sourceRevision,
            CreatedAt = DateTimeOffset.UtcNow,
        };
        database.MediaSources.Add(source);
        await database.SaveChangesAsync();
        return source.Id;
    }

    private static async Task<ControlDbContext> ContextAsync(ControlHostApplicationFactory factory)
    {
        var contextFactory = factory.Services.GetRequiredService<IDbContextFactory<ControlDbContext>>();
        return await contextFactory.CreateDbContextAsync();
    }

    private static async Task<string> AuthenticateAsync(HttpClient client)
    {
        using var csrfResponse = await client.GetAsync("/api/auth/csrf/");
        using var csrfBody = await JsonDocument.ParseAsync(await csrfResponse.Content.ReadAsStreamAsync());
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
}
