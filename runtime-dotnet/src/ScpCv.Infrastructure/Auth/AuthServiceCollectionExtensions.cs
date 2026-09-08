using System.Security.Claims;
using System.Security.Cryptography;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using ScpCv.Domain.Model;
using ScpCv.Infrastructure.Persistence;

namespace ScpCv.Infrastructure.Auth;

public static class AuthServiceCollectionExtensions
{
    public const string CorsPolicyName = "scp-cv-control-clients";

    public static IServiceCollection AddScpCvAuthentication(
        this IServiceCollection services,
        IConfiguration configuration)
    {
        var options = configuration.GetSection(ScpCvAuthenticationOptions.SectionName)
            .Get<ScpCvAuthenticationOptions>() ?? new ScpCvAuthenticationOptions();
        options.AllowedOrigins = options.AllowedOrigins
            .Select(NormalizeOrigin)
            .Where(static origin => origin is not null)
            .Cast<string>()
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .ToArray();

        services.AddSingleton(options);
        services.AddSingleton<IPasswordHasher<UserAccount>, PasswordHasher<UserAccount>>();
        services.AddSingleton<CsrfTokenService>();
        services.AddSingleton<IAuthorizationHandler, ScpCvPermissionAuthorizationHandler>();
        services.AddScoped<DevelopmentAccountSeeder>();

        services.AddCors(cors => cors.AddPolicy(
            CorsPolicyName,
            policy =>
            {
                if (options.AllowedOrigins.Length > 0)
                {
                    policy.WithOrigins(options.AllowedOrigins)
                        .AllowCredentials()
                        .WithMethods("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")
                        .WithHeaders("Content-Type", CsrfTokenService.HeaderName);
                }
            }));

        services.AddAuthentication(CookieAuthenticationDefaults.AuthenticationScheme)
            .AddCookie(cookie =>
            {
                cookie.Cookie.Name = "sessionid";
                cookie.Cookie.HttpOnly = true;
                cookie.Cookie.IsEssential = true;
                cookie.Cookie.SameSite = options.CrossSiteCookies ? SameSiteMode.None : SameSiteMode.Lax;
                cookie.Cookie.SecurePolicy = options.CrossSiteCookies
                    ? CookieSecurePolicy.Always
                    : CookieSecurePolicy.SameAsRequest;
                cookie.Events.OnRedirectToLogin = context => WriteAuthErrorAsync(
                    context.Response,
                    StatusCodes.Status401Unauthorized,
                    "未登录",
                    "unauthorized");
                cookie.Events.OnRedirectToAccessDenied = context => WriteAuthErrorAsync(
                    context.Response,
                    StatusCodes.Status403Forbidden,
                    "权限不足",
                    "forbidden");
                cookie.Events.OnValidatePrincipal = ValidatePrincipalAsync;
            });
        services.AddAuthorization();
        return services;
    }

    internal static string? NormalizeOrigin(string? value)
    {
        if (string.IsNullOrWhiteSpace(value) ||
            !Uri.TryCreate(value.Trim(), UriKind.Absolute, out var uri) ||
            !string.IsNullOrEmpty(uri.UserInfo) ||
            uri.AbsolutePath != "/" ||
            !string.IsNullOrEmpty(uri.Query) ||
            !string.IsNullOrEmpty(uri.Fragment))
        {
            return null;
        }

        return uri.GetLeftPart(UriPartial.Authority);
    }

    private static async Task ValidatePrincipalAsync(CookieValidatePrincipalContext context)
    {
        var rawUserId = context.Principal?.FindFirstValue(ClaimTypes.NameIdentifier);
        if (!long.TryParse(rawUserId, out var userId))
        {
            context.RejectPrincipal();
            await context.HttpContext.SignOutAsync().ConfigureAwait(false);
            return;
        }

        var factory = context.HttpContext.RequestServices.GetRequiredService<IDbContextFactory<ControlDbContext>>();
        await using var database = await factory.CreateDbContextAsync(context.HttpContext.RequestAborted)
            .ConfigureAwait(false);
        var active = await database.UserAccounts
            .AsNoTracking()
            .AnyAsync(user => user.Id == userId && user.IsActive, context.HttpContext.RequestAborted)
            .ConfigureAwait(false);
        if (!active)
        {
            context.RejectPrincipal();
            await context.HttpContext.SignOutAsync().ConfigureAwait(false);
        }
    }

    private static Task WriteAuthErrorAsync(HttpResponse response, int statusCode, string detail, string code)
    {
        response.StatusCode = statusCode;
        return response.WriteAsJsonAsync(new { detail, code });
    }
}

public sealed class ScpCvAuthenticationOptions
{
    public const string SectionName = "Authentication";

    public string[] AllowedOrigins { get; set; } = [];
    public bool CrossSiteCookies { get; set; } = true;
    public DevelopmentAccountOptions DevelopmentAccount { get; set; } = new();
}

public sealed class DevelopmentAccountOptions
{
    public string Username { get; set; } = string.Empty;
    public string Password { get; set; } = string.Empty;
    public bool IsStaff { get; set; }
    public bool IsSuperuser { get; set; }
    public string[] Permissions { get; set; } = [];
}

public sealed class CsrfTokenService(ScpCvAuthenticationOptions options)
{
    public const string CookieName = "csrftoken";
    public const string HeaderName = "X-CSRFToken";

    public string EnsureToken(HttpContext context)
    {
        if (context.Request.Cookies.TryGetValue(CookieName, out var existing) && IsValidShape(existing))
        {
            return existing;
        }

        return IssueToken(context);
    }

    public string IssueToken(HttpContext context)
    {
        var token = Convert.ToBase64String(RandomNumberGenerator.GetBytes(32))
            .TrimEnd('=')
            .Replace('+', '-')
            .Replace('/', '_');
        context.Response.Cookies.Append(
            CookieName,
            token,
            new CookieOptions
            {
                HttpOnly = false,
                IsEssential = true,
                Path = "/",
                SameSite = options.CrossSiteCookies ? SameSiteMode.None : SameSiteMode.Lax,
                Secure = options.CrossSiteCookies || context.Request.IsHttps,
            });
        return token;
    }

    public CsrfValidationResult Validate(HttpContext context)
    {
        if (!IsOriginAllowed(context))
        {
            return new CsrfValidationResult(false, "请求 Origin 不在允许列表中");
        }

        if (!context.Request.Cookies.TryGetValue(CookieName, out var cookieToken) ||
            !context.Request.Headers.TryGetValue(HeaderName, out var headerValues))
        {
            return new CsrfValidationResult(false, "缺少 CSRF token");
        }

        var headerToken = headerValues.Count == 1 ? headerValues[0] : null;
        if (!IsValidShape(cookieToken) ||
            headerToken is null ||
            cookieToken.Length != headerToken.Length ||
            !CryptographicOperations.FixedTimeEquals(
                System.Text.Encoding.UTF8.GetBytes(cookieToken),
                System.Text.Encoding.UTF8.GetBytes(headerToken)))
        {
            return new CsrfValidationResult(false, "CSRF token 无效");
        }

        return new CsrfValidationResult(true, string.Empty);
    }

    public bool IsOriginAllowed(HttpContext context)
    {
        if (!context.Request.Headers.TryGetValue("Origin", out var values) || values.Count == 0)
        {
            return true;
        }

        var origin = AuthServiceCollectionExtensions.NormalizeOrigin(values.Count == 1 ? values[0] : null);
        if (origin is null)
        {
            return false;
        }

        var requestOrigin = $"{context.Request.Scheme}://{context.Request.Host}";
        return string.Equals(origin, requestOrigin, StringComparison.OrdinalIgnoreCase) ||
            options.AllowedOrigins.Contains(origin, StringComparer.OrdinalIgnoreCase);
    }

    private static bool IsValidShape(string? token) =>
        token is { Length: >= 40 and <= 64 } &&
        token.All(static character => char.IsAsciiLetterOrDigit(character) || character is '-' or '_');
}

public readonly record struct CsrfValidationResult(bool Succeeded, string Detail);

public static class ScpCvClaimTypes
{
    public const string IsStaff = "scp-cv:is_staff";
    public const string IsSuperuser = "scp-cv:is_superuser";
    public const string Permission = "scp-cv:permission";
}

public sealed record ScpCvPermissionRequirement(string Permission) : IAuthorizationRequirement;

public sealed class ScpCvPermissionAuthorizationHandler : AuthorizationHandler<ScpCvPermissionRequirement>
{
    protected override Task HandleRequirementAsync(
        AuthorizationHandlerContext context,
        ScpCvPermissionRequirement requirement)
    {
        var isSuperuser = context.User.HasClaim(ScpCvClaimTypes.IsSuperuser, "true");
        var hasPermission = context.User.HasClaim(
            claim => claim.Type == ScpCvClaimTypes.Permission &&
                string.Equals(claim.Value, requirement.Permission, StringComparison.Ordinal));
        if (isSuperuser || hasPermission)
        {
            context.Succeed(requirement);
        }

        return Task.CompletedTask;
    }
}
