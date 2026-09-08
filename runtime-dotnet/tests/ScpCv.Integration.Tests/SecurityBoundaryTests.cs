using System.Diagnostics;
using System.IO.Pipes;
using System.Net;
using System.Net.Http;
using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Data.Sqlite;
using ScpCv.ControlHost.Ipc;
using ScpCv.Infrastructure.Diagnostics;
using ScpCv.Infrastructure.Media;
using ScpCv.Integration.Tests.Fixtures;

namespace ScpCv.Integration.Tests;

public sealed class SecurityBoundaryTests
{
    [Fact]
    public void SensitiveLogPropertiesAndUriCredentialsAreRedacted()
    {
        var values = LogRedaction.Properties(new Dictionary<string, object?>
        {
            ["new_password"] = "do-not-log",
            ["claim_token"] = "do-not-log-either",
            ["source"] = "https://operator:secret@example.test/media?token=abc&quality=high",
        });

        Assert.Equal(LogRedaction.RedactedValue, values["new_password"]);
        Assert.Equal(LogRedaction.RedactedValue, values["claim_token"]);
        var uri = Assert.IsType<string>(values["source"]);
        Assert.DoesNotContain("secret", uri, StringComparison.Ordinal);
        Assert.DoesNotContain("token=abc", uri, StringComparison.Ordinal);
        Assert.Contains("quality=high", uri, StringComparison.Ordinal);
    }

    [Fact]
    public async Task LocalMediaPathCannotEscapeConfiguredRoots()
    {
        await using var fixture = await ControlHostFixture.CreateAsync();
        var service = new MediaSourceService(
            fixture.Database,
            fixture.Writes,
            fixture.Database,
            new MediaStorageOptions(),
            fixture.TimeProvider);
        var outside = Path.Combine(Path.GetTempPath(), $"scp-cv-outside-{Guid.NewGuid():N}.png");
        await File.WriteAllBytesAsync(outside, [1, 2, 3]);
        try
        {
            var error = await Assert.ThrowsAsync<MediaServiceException>(() =>
                service.AddLocalAsync(outside, null, "image", null, false));
            Assert.Contains("超出允许目录", error.Message, StringComparison.Ordinal);
        }
        finally
        {
            File.Delete(outside);
        }
    }

    [Fact]
    public async Task AuthenticatedMutationRequiresCsrfAndCorsAllowsOnlyExactOrigin()
    {
        using var factory = new SecurityApplicationFactory();
        using var client = factory.CreateClient(new WebApplicationFactoryClientOptions
        {
            AllowAutoRedirect = false,
            BaseAddress = new Uri("https://localhost"),
            HandleCookies = true,
        });
        using var csrfResponse = await client.GetAsync("/api/auth/csrf/");
        using var csrfBody = await JsonDocument.ParseAsync(await csrfResponse.Content.ReadAsStreamAsync());
        var csrf = csrfBody.RootElement.GetProperty("csrfToken").GetString();
        using var login = await client.PostAsJsonAsync(
            "/api/auth/login/",
            new { username = "operator", password = "Security-password-123" });
        login.EnsureSuccessStatusCode();

        using var mutation = await client.PostAsJsonAsync("/api/playback/reset-all/", new { });
        Assert.Equal(HttpStatusCode.BadRequest, mutation.StatusCode);
        using var mutationBody = await JsonDocument.ParseAsync(await mutation.Content.ReadAsStreamAsync());
        Assert.Equal("csrf_failed", mutationBody.RootElement.GetProperty("code").GetString());

        using var allowedRequest = new HttpRequestMessage(HttpMethod.Get, "/api/auth/status/");
        allowedRequest.Headers.Add("Origin", SecurityApplicationFactory.AllowedOrigin);
        using var allowed = await client.SendAsync(allowedRequest);
        Assert.Equal(SecurityApplicationFactory.AllowedOrigin, allowed.Headers.GetValues("Access-Control-Allow-Origin").Single());

        using var deniedRequest = new HttpRequestMessage(HttpMethod.Get, "/api/auth/status/");
        deniedRequest.Headers.Add("Origin", "https://evil.example");
        using var denied = await client.SendAsync(deniedRequest);
        Assert.False(denied.Headers.Contains("Access-Control-Allow-Origin"));
        Assert.NotNull(csrf);
    }

    [Fact]
    public async Task NamedPipeRejectsRegisteredProcessWithWrongRuntimeIdentity()
    {
        using var process = Process.GetCurrentProcess();
        var registry = new RegisteredProcessRegistry();
        registry.Register(new RegisteredProcessIdentity(
            process.Id,
            new DateTimeOffset(process.StartTime.ToUniversalTime(), TimeSpan.Zero),
            process.SessionId,
            "player",
            Guid.NewGuid()));
        var expectedInstance = Guid.NewGuid();
        var server = new NamedPipeServer(Guid.NewGuid(), process.SessionId, registry);
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(5));
        var accept = server.AcceptAsync("player", expectedInstance, timeout.Token);
        await using var client = new NamedPipeClientStream(".", server.PipeName, PipeDirection.InOut, PipeOptions.Asynchronous);
        await client.ConnectAsync(timeout.Token);

        await Assert.ThrowsAsync<UnauthorizedAccessException>(async () => await accept);
    }
}

internal sealed class SecurityApplicationFactory : WebApplicationFactory<Program>
{
    public const string AllowedOrigin = "https://console.example.test";
    private readonly string _temporaryRoot = Path.Combine(Path.GetTempPath(), "scp-cv-security-tests", Guid.NewGuid().ToString("N"));

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.UseEnvironment("Testing");
        builder.UseSetting("DataRoot", _temporaryRoot);
        builder.UseSetting("SafetyMode", "Simulation");
        builder.UseSetting("Authentication:AllowedOrigins:0", AllowedOrigin);
        builder.UseSetting("Authentication:DevelopmentAccount:Username", "operator");
        builder.UseSetting("Authentication:DevelopmentAccount:Password", "Security-password-123");
    }

    protected override void Dispose(bool disposing)
    {
        base.Dispose(disposing);
        if (!disposing) return;
        SqliteConnection.ClearAllPools();
        if (Directory.Exists(_temporaryRoot)) Directory.Delete(_temporaryRoot, recursive: true);
    }
}
