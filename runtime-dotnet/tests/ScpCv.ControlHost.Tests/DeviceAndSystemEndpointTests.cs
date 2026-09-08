using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using ScpCv.Domain.Model;
using ScpCv.Infrastructure.Devices;
using ScpCv.Infrastructure.Persistence;
using ScpCv.Infrastructure.Runtime;

namespace ScpCv.ControlHost.Tests;

public sealed class DeviceAndSystemEndpointTests
{
    private const string InitialPassword = "Old-password-123";

    [Fact]
    public async Task DeviceListComesFromConfigurationInStableOrder()
    {
        using var factory = new ControlHostApplicationFactory();
        using var client = factory.CreateHttpsClient();
        await AuthenticateAsync(client);

        using var response = await client.GetAsync("/api/devices/");
        using var body = await Json(response);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var devices = body.RootElement.GetProperty("devices").EnumerateArray().ToArray();
        Assert.Equal(["splice_screen", "tv_left", "tv_right"], devices.Select(DeviceType));
        Assert.Equal(["192.168.5.10", "192.168.5.161", "192.168.5.162"], devices.Select(DeviceHost));
        Assert.All(devices, device => Assert.Equal(8889, device.GetProperty("port").GetInt32()));
        Assert.All(devices, device => Assert.Equal(string.Empty, device.GetProperty("action").GetString()));
    }

    [Fact]
    public async Task SimulationDeviceControlRecordsFramesWithoutNetworkTraffic()
    {
        using var factory = new ControlHostApplicationFactory();
        using var client = factory.CreateHttpsClient();
        var csrf = await AuthenticateAsync(client);
        var transport = factory.Services.GetRequiredService<SimulationDeviceCommandTransport>();

        using var request = Request(HttpMethod.Post, "/api/devices/tv_left/toggle/", csrf);
        using var response = await client.SendAsync(request);
        using var body = await Json(response);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var device = body.RootElement.GetProperty("device");
        Assert.Equal("toggle", device.GetProperty("action").GetString());
        Assert.Contains("Simulation", device.GetProperty("detail").GetString(), StringComparison.Ordinal);
        var commands = transport.Commands.ToArray();
        var command = Assert.Single(commands);
        Assert.Equal("tv_left", command.DeviceType);
        Assert.Equal(["FF06010A00330001FA", "FF06010A00330000FA"], command.Frames);
    }

    [Theory]
    [InlineData("/api/devices/splice_screen/toggle/", HttpStatusCode.NotFound, "device_error")]
    [InlineData("/api/devices/tv_left/power/on/", HttpStatusCode.NotFound, "device_error")]
    [InlineData("/api/devices/splice_screen/power/invalid/", HttpStatusCode.BadRequest, "invalid_action")]
    public async Task InvalidDeviceOperationsPreserveLegacyErrors(string path, HttpStatusCode status, string code)
    {
        using var factory = new ControlHostApplicationFactory();
        using var client = factory.CreateHttpsClient();
        var csrf = await AuthenticateAsync(client);

        using var request = Request(HttpMethod.Post, path, csrf);
        using var response = await client.SendAsync(request);
        using var body = await Json(response);

        Assert.Equal(status, response.StatusCode);
        Assert.Equal(code, body.RootElement.GetProperty("code").GetString());
    }

    [Theory]
    [InlineData("shutdown", "系统关闭请求已发送")]
    [InlineData("restart", "系统重启请求已发送")]
    public async Task SystemRequestRevokesDispatchBeforeReturningAcceptedState(string action, string detail)
    {
        using var factory = new ControlHostApplicationFactory();
        using var client = factory.CreateHttpsClient();
        await ArmRuntimeAsync(factory);
        await SeedPlayingSessionAsync(factory);
        var csrf = await AuthenticateAsync(client);

        using var request = Request(HttpMethod.Post, $"/api/system/{action}/", csrf);
        using var response = await client.SendAsync(request);
        using var body = await Json(response);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal(detail, body.RootElement.GetProperty("detail").GetString());
        Assert.Equal(4, body.RootElement.GetProperty("sessions").GetArrayLength());
        Assert.All(
            body.RootElement.GetProperty("sessions").EnumerateArray(),
            session =>
            {
                Assert.Equal("idle", session.GetProperty("playback_state").GetString());
                Assert.Equal("CLOSE", session.GetProperty("pending_command").GetString());
            });

        var authority = factory.Services.GetRequiredService<RuntimeAuthorityRepository>();
        var group = await authority.GetGroupAsync();
        Assert.Equal(RuntimeGroupState.Draining, group.State);
        Assert.Equal($"system_{action}", group.StopReason);
    }

    private static async Task ArmRuntimeAsync(ControlHostApplicationFactory factory)
    {
        var authority = factory.Services.GetRequiredService<RuntimeAuthorityRepository>();
        var requestId = Guid.NewGuid();
        var starting = await authority.BeginStartAsync(requestId);
        await authority.ArmAsync(requestId, starting.GroupEpoch);
    }

    private static async Task SeedPlayingSessionAsync(ControlHostApplicationFactory factory)
    {
        var contextFactory = factory.Services.GetRequiredService<IDbContextFactory<ControlDbContext>>();
        await using var database = await contextFactory.CreateDbContextAsync();
        var session = await database.PlaybackSessions.SingleAsync(item => item.WindowId == 1);
        session.PlaybackState = PlaybackState.Playing;
        session.PlaybackMode = PlaybackMode.Pdf;
        await database.SaveChangesAsync();
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

    private static HttpRequestMessage Request(HttpMethod method, string path, string csrf)
    {
        var request = new HttpRequestMessage(method, path) { Content = JsonContent.Create(new { }) };
        request.Headers.Add("X-CSRFToken", csrf);
        return request;
    }

    private static string DeviceType(JsonElement device) => device.GetProperty("device_type").GetString()!;
    private static string DeviceHost(JsonElement device) => device.GetProperty("host").GetString()!;

    private static async Task<JsonDocument> Json(HttpResponseMessage response) =>
        await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());
}
