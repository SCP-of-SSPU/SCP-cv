using System.Net;
using System.Net.Http.Json;
using System.Security.Claims;
using System.Text.Json;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.Identity;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using ScpCv.Infrastructure.Auth;
using ScpCv.Infrastructure.Persistence;
using ScpCv.Domain.Model;

namespace ScpCv.ControlHost.Tests;

public sealed class AuthEndpointTests
{
    private const string InitialPassword = "Old-password-123";

    [Fact]
    public async Task AnonymousStatusIsPublicButMeIsUnauthorized()
    {
        using var factory = new ControlHostApplicationFactory();
        using var client = factory.CreateHttpsClient();

        using var status = await client.GetAsync("/api/auth/status/");
        using var statusBody = await JsonDocument.ParseAsync(await status.Content.ReadAsStreamAsync());
        Assert.Equal(HttpStatusCode.OK, status.StatusCode);
        Assert.False(statusBody.RootElement.GetProperty("authenticated").GetBoolean());
        Assert.Equal(JsonValueKind.Null, statusBody.RootElement.GetProperty("user").ValueKind);

        using var me = await client.GetAsync("/api/auth/me/");
        using var meBody = await JsonDocument.ParseAsync(await me.Content.ReadAsStreamAsync());
        Assert.Equal(HttpStatusCode.Unauthorized, me.StatusCode);
        Assert.Equal("unauthorized", meBody.RootElement.GetProperty("code").GetString());
    }

    [Fact]
    public async Task CsrfAndLoginPreserveCookieAndUserResponseContract()
    {
        using var factory = new ControlHostApplicationFactory();
        using var client = factory.CreateHttpsClient();

        var contextFactory = factory.Services.GetRequiredService<IDbContextFactory<ControlDbContext>>();
        await using var database = await contextFactory.CreateDbContextAsync();
        var seededUser = await database.UserAccounts.SingleAsync();
        Assert.Equal("operator", seededUser.Username);
        Assert.NotEqual(InitialPassword, seededUser.PasswordHash);

        using var csrf = await client.GetAsync("/api/auth/csrf/");
        using var csrfBody = await JsonDocument.ParseAsync(await csrf.Content.ReadAsStreamAsync());
        var csrfToken = csrfBody.RootElement.GetProperty("csrfToken").GetString();
        Assert.Equal(HttpStatusCode.OK, csrf.StatusCode);
        Assert.False(string.IsNullOrWhiteSpace(csrfToken));
        var csrfCookie = Assert.Single(csrf.Headers.GetValues("Set-Cookie"));
        Assert.Contains("csrftoken=", csrfCookie, StringComparison.OrdinalIgnoreCase);
        Assert.Contains("secure", csrfCookie, StringComparison.OrdinalIgnoreCase);
        Assert.Contains("samesite=none", csrfCookie, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("httponly", csrfCookie, StringComparison.OrdinalIgnoreCase);

        using var malformed = await client.PostAsync(
            "/api/auth/login/",
            new StringContent("not-json", System.Text.Encoding.UTF8, "application/json"));
        Assert.Equal(HttpStatusCode.BadRequest, malformed.StatusCode);
        Assert.Equal("invalid_credentials", await ReadCodeAsync(malformed));

        using var missing = await client.PostAsJsonAsync("/api/auth/login/", new { username = "", password = "" });
        Assert.Equal(HttpStatusCode.BadRequest, missing.StatusCode);
        Assert.Equal("invalid_credentials", await ReadCodeAsync(missing));

        using var invalid = await client.PostAsJsonAsync(
            "/api/auth/login/",
            new { username = "operator", password = "wrong" });
        Assert.Equal(HttpStatusCode.Unauthorized, invalid.StatusCode);
        Assert.Equal("invalid_credentials", await ReadCodeAsync(invalid));

        using var login = await client.PostAsJsonAsync(
            "/api/auth/login/",
            new { username = " operator ", password = InitialPassword });
        using var loginBody = await JsonDocument.ParseAsync(await login.Content.ReadAsStreamAsync());
        Assert.Equal(HttpStatusCode.OK, login.StatusCode);
        var user = loginBody.RootElement.GetProperty("user");
        Assert.Equal("operator", user.GetProperty("username").GetString());
        Assert.True(user.GetProperty("is_staff").GetBoolean());
        Assert.False(user.GetProperty("is_superuser").GetBoolean());
        Assert.Contains(
            login.Headers.GetValues("Set-Cookie"),
            value => value.Contains("sessionid=", StringComparison.OrdinalIgnoreCase) &&
                value.Contains("httponly", StringComparison.OrdinalIgnoreCase));

        using var me = await client.GetAsync("/api/auth/me/");
        Assert.Equal(HttpStatusCode.OK, me.StatusCode);
    }

    [Fact]
    public async Task ChangePasswordRequiresCsrfAndKeepsCurrentSession()
    {
        using var factory = new ControlHostApplicationFactory();
        using var client = factory.CreateHttpsClient();
        var csrfToken = await GetCsrfTokenAsync(client);
        await LoginAsync(client, InitialPassword);

        using var missingToken = await client.PostAsJsonAsync(
            "/api/auth/change-password/",
            new { current_password = InitialPassword, new_password = "New-password-456" });
        Assert.Equal(HttpStatusCode.BadRequest, missingToken.StatusCode);
        Assert.Equal("csrf_failed", await ReadCodeAsync(missingToken));

        using var wrongPasswordRequest = CreateCsrfRequest(
            "/api/auth/change-password/",
            csrfToken,
            new { current_password = "wrong", new_password = "New-password-456" });
        using var wrongPassword = await client.SendAsync(wrongPasswordRequest);
        Assert.Equal(HttpStatusCode.BadRequest, wrongPassword.StatusCode);
        Assert.Equal("invalid_password", await ReadCodeAsync(wrongPassword));

        using var weakPasswordRequest = CreateCsrfRequest(
            "/api/auth/change-password/",
            csrfToken,
            new { current_password = InitialPassword, new_password = "12345678" });
        using var weakPassword = await client.SendAsync(weakPasswordRequest);
        Assert.Equal(HttpStatusCode.BadRequest, weakPassword.StatusCode);
        Assert.Equal("weak_password", await ReadCodeAsync(weakPassword));

        using var changeRequest = CreateCsrfRequest(
            "/api/auth/change-password/",
            csrfToken,
            new { current_password = InitialPassword, new_password = "New-password-456" });
        using var changed = await client.SendAsync(changeRequest);
        Assert.Equal(HttpStatusCode.OK, changed.StatusCode);

        using var me = await client.GetAsync("/api/auth/me/");
        Assert.Equal(HttpStatusCode.OK, me.StatusCode);

        var refreshedCsrfToken = await GetCsrfTokenAsync(client);
        using var logoutRequest = CreateCsrfRequest("/api/auth/logout/", refreshedCsrfToken, new { });
        using var logout = await client.SendAsync(logoutRequest);
        Assert.Equal(HttpStatusCode.OK, logout.StatusCode);
        using var afterLogout = await client.GetAsync("/api/auth/me/");
        Assert.Equal(HttpStatusCode.Unauthorized, afterLogout.StatusCode);

        using var newLogin = await client.PostAsJsonAsync(
            "/api/auth/login/",
            new { username = "operator", password = "New-password-456" });
        Assert.Equal(HttpStatusCode.OK, newLogin.StatusCode);
    }

    [Fact]
    public async Task CorsUsesExactConfiguredOriginAndRejectsUntrustedOrigin()
    {
        using var factory = new ControlHostApplicationFactory();
        using var client = factory.CreateHttpsClient();

        using var trustedRequest = new HttpRequestMessage(HttpMethod.Options, "/api/auth/login/");
        trustedRequest.Headers.Add("Origin", ControlHostApplicationFactory.AllowedOrigin);
        trustedRequest.Headers.Add("Access-Control-Request-Method", "POST");
        trustedRequest.Headers.Add("Access-Control-Request-Headers", "content-type,x-csrftoken");
        using var trusted = await client.SendAsync(trustedRequest);
        Assert.Equal(HttpStatusCode.NoContent, trusted.StatusCode);
        Assert.Equal(ControlHostApplicationFactory.AllowedOrigin, trusted.Headers.GetValues("Access-Control-Allow-Origin").Single());
        Assert.Equal("true", trusted.Headers.GetValues("Access-Control-Allow-Credentials").Single());
        Assert.Contains("Origin", trusted.Headers.Vary);

        using var untrustedRequest = new HttpRequestMessage(HttpMethod.Options, "/api/auth/login/");
        untrustedRequest.Headers.Add("Origin", "https://evil.example.test");
        untrustedRequest.Headers.Add("Access-Control-Request-Method", "POST");
        using var untrusted = await client.SendAsync(untrustedRequest);
        Assert.False(untrusted.Headers.Contains("Access-Control-Allow-Origin"));

        using var untrustedLogin = new HttpRequestMessage(HttpMethod.Post, "/api/auth/login/")
        {
            Content = JsonContent.Create(new { username = "operator", password = InitialPassword }),
        };
        untrustedLogin.Headers.Add("Origin", "https://evil.example.test");
        using var rejected = await client.SendAsync(untrustedLogin);
        Assert.Equal(HttpStatusCode.Forbidden, rejected.StatusCode);
        Assert.Equal("origin_not_allowed", await ReadCodeAsync(rejected));
    }

    [Fact]
    public async Task PermissionRequirementAcceptsExplicitPermissionOrSuperuserOnly()
    {
        using var factory = new ControlHostApplicationFactory();
        using var client = factory.CreateHttpsClient();
        var authorization = factory.Services.GetRequiredService<IAuthorizationService>();
        var requirement = new ScpCvPermissionRequirement("playback.control");

        var permitted = CreatePrincipal(new Claim(ScpCvClaimTypes.Permission, "playback.control"));
        var denied = CreatePrincipal(new Claim(ScpCvClaimTypes.Permission, "media.view"));
        var superuser = CreatePrincipal(new Claim(ScpCvClaimTypes.IsSuperuser, "true"));

        Assert.True((await authorization.AuthorizeAsync(permitted, null, requirement)).Succeeded);
        Assert.False((await authorization.AuthorizeAsync(denied, null, requirement)).Succeeded);
        Assert.True((await authorization.AuthorizeAsync(superuser, null, requirement)).Succeeded);
    }

    [Fact]
    public async Task DevelopmentSeedDoesNotOverwriteExistingAccount()
    {
        using var factory = new ControlHostApplicationFactory();
        using var client = factory.CreateHttpsClient();
        var services = factory.Services;
        var contextFactory = services.GetRequiredService<IDbContextFactory<ControlDbContext>>();
        string originalHash;
        await using (var before = await contextFactory.CreateDbContextAsync())
        {
            originalHash = (await before.UserAccounts.SingleAsync()).PasswordHash;
        }

        var secondSeed = new DevelopmentAccountSeeder(
            services.GetRequiredService<WriteCoordinator>(),
            services.GetRequiredService<IPasswordHasher<UserAccount>>(),
            new ScpCvAuthenticationOptions
            {
                DevelopmentAccount = new DevelopmentAccountOptions
                {
                    Username = "operator",
                    Password = "Replacement-password-789",
                    IsSuperuser = true,
                },
            });
        await secondSeed.SeedAsync();

        await using var after = await contextFactory.CreateDbContextAsync();
        var unchanged = await after.UserAccounts.SingleAsync();
        Assert.Equal(originalHash, unchanged.PasswordHash);
        Assert.False(unchanged.IsSuperuser);
    }

    private static async Task<string> GetCsrfTokenAsync(HttpClient client)
    {
        using var response = await client.GetAsync("/api/auth/csrf/");
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());
        return body.RootElement.GetProperty("csrfToken").GetString()!;
    }

    private static async Task LoginAsync(HttpClient client, string password)
    {
        using var response = await client.PostAsJsonAsync(
            "/api/auth/login/",
            new { username = "operator", password });
        response.EnsureSuccessStatusCode();
    }

    private static HttpRequestMessage CreateCsrfRequest(string path, string csrfToken, object body)
    {
        var request = new HttpRequestMessage(HttpMethod.Post, path)
        {
            Content = JsonContent.Create(body),
        };
        request.Headers.Add("X-CSRFToken", csrfToken);
        return request;
    }

    private static async Task<string?> ReadCodeAsync(HttpResponseMessage response)
    {
        using var body = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());
        return body.RootElement.GetProperty("code").GetString();
    }

    private static ClaimsPrincipal CreatePrincipal(params Claim[] claims) =>
        new(new ClaimsIdentity(claims, "test"));
}

internal sealed class ControlHostApplicationFactory : WebApplicationFactory<Program>
{
    public const string AllowedOrigin = "https://localhost";
    private readonly string _temporaryRoot = Path.Combine(
        Path.GetTempPath(),
        "scp-cv-control-host-tests",
        Guid.NewGuid().ToString("N"));

    public string TemporaryRoot => _temporaryRoot;

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.UseEnvironment("Testing");
        builder.UseSetting("DataRoot", _temporaryRoot);
        builder.UseSetting("SafetyMode", "Simulation");
        builder.UseSetting("Authentication:AllowedOrigins:0", AllowedOrigin);
        builder.UseSetting("Authentication:CrossSiteCookies", "true");
        builder.UseSetting("Authentication:DevelopmentAccount:Username", "operator");
        builder.UseSetting("Authentication:DevelopmentAccount:Password", InitialPassword);
        builder.UseSetting("Authentication:DevelopmentAccount:IsStaff", "true");
        builder.UseSetting("Authentication:DevelopmentAccount:IsSuperuser", "false");
        builder.UseSetting("Authentication:DevelopmentAccount:Permissions:0", "playback.control");
    }

    public HttpClient CreateHttpsClient() => CreateClient(new WebApplicationFactoryClientOptions
    {
        AllowAutoRedirect = false,
        BaseAddress = new Uri("https://localhost"),
        HandleCookies = true,
    });

    protected override void Dispose(bool disposing)
    {
        base.Dispose(disposing);
        if (!disposing)
        {
            return;
        }

        SqliteConnection.ClearAllPools();
        var fullRoot = Path.GetFullPath(_temporaryRoot);
        var expectedParent = Path.GetFullPath(Path.Combine(Path.GetTempPath(), "scp-cv-control-host-tests"));
        if (!string.Equals(Path.GetDirectoryName(fullRoot), expectedParent, StringComparison.OrdinalIgnoreCase))
        {
            throw new InvalidOperationException("拒绝清理测试根目录之外的路径。");
        }

        if (Directory.Exists(fullRoot))
        {
            Directory.Delete(fullRoot, recursive: true);
        }
    }

    private const string InitialPassword = "Old-password-123";
}
