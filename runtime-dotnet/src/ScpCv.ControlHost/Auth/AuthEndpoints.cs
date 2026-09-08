using System.Security.Claims;
using System.Text.Json;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using ScpCv.Contracts.Http;
using ScpCv.Domain.Model;
using ScpCv.Infrastructure.Auth;
using ScpCv.Infrastructure.Persistence;

namespace ScpCv.ControlHost.Auth;

public static class AuthEndpoints
{
    private static readonly JsonSerializerOptions WebJsonOptions = new(JsonSerializerDefaults.Web);

    public static IEndpointRouteBuilder MapAuthEndpoints(this IEndpointRouteBuilder endpoints)
    {
        var auth = endpoints.MapGroup("/api/auth");
        auth.MapGet("/csrf/", GetCsrfToken);
        auth.MapPost("/login/", LoginAsync);
        auth.MapPost("/logout/", LogoutAsync);
        auth.MapGet("/me/", GetCurrentUser).RequireAuthorization();
        auth.MapGet("/status/", GetStatus);
        auth.MapPost("/change-password/", ChangePasswordAsync).RequireAuthorization();
        return endpoints;
    }

    private static IResult GetCsrfToken(HttpContext context, CsrfTokenService csrf) =>
        Results.Ok(new CsrfTokenResponseDto { CsrfToken = csrf.EnsureToken(context) });

    private static async Task<IResult> LoginAsync(
        HttpContext context,
        IDbContextFactory<ControlDbContext> contextFactory,
        IPasswordHasher<UserAccount> passwordHasher,
        CsrfTokenService csrf,
        CancellationToken cancellationToken)
    {
        if (!csrf.IsOriginAllowed(context))
        {
            return Error(StatusCodes.Status403Forbidden, "请求 Origin 不在允许列表中", "origin_not_allowed");
        }

        var request = await ReadBodyAsync<LoginRequestDto>(context.Request, cancellationToken).ConfigureAwait(false)
            ?? new LoginRequestDto();
        var username = request.Username.Trim();
        if (username.Length == 0 || request.Password.Length == 0)
        {
            return Error(StatusCodes.Status400BadRequest, "用户名和密码不能为空", "invalid_credentials");
        }

        await using var database = await contextFactory.CreateDbContextAsync(cancellationToken).ConfigureAwait(false);
        var user = await database.UserAccounts
            .SingleOrDefaultAsync(candidate => candidate.Username == username, cancellationToken)
            .ConfigureAwait(false);
        if (user is null || !user.IsActive ||
            passwordHasher.VerifyHashedPassword(user, user.PasswordHash, request.Password) == PasswordVerificationResult.Failed)
        {
            return Error(StatusCodes.Status401Unauthorized, "用户名或密码错误", "invalid_credentials");
        }

        await context.SignInAsync(
            CookieAuthenticationDefaults.AuthenticationScheme,
            CreatePrincipal(user),
            new AuthenticationProperties { IsPersistent = false })
            .ConfigureAwait(false);
        _ = csrf.EnsureToken(context);
        return Results.Ok(new AuthUserResponseDto { User = ToDto(user) });
    }

    private static async Task<IResult> LogoutAsync(HttpContext context, CsrfTokenService csrf)
    {
        if (context.User.Identity?.IsAuthenticated == true)
        {
            var validation = csrf.Validate(context);
            if (!validation.Succeeded)
            {
                return Error(StatusCodes.Status400BadRequest, validation.Detail, "csrf_failed");
            }
        }

        await context.SignOutAsync(CookieAuthenticationDefaults.AuthenticationScheme).ConfigureAwait(false);
        context.Response.Cookies.Delete(CsrfTokenService.CookieName);
        return Results.Ok(new { detail = "ok" });
    }

    private static IResult GetCurrentUser(ClaimsPrincipal principal) =>
        TryReadUser(principal, out var user)
            ? Results.Ok(new AuthUserResponseDto { User = user })
            : Error(StatusCodes.Status401Unauthorized, "未登录", "unauthorized");

    private static IResult GetStatus(ClaimsPrincipal principal) =>
        TryReadUser(principal, out var user)
            ? Results.Ok(new AuthStatusResponseDto { Authenticated = true, User = user })
            : Results.Ok(new AuthStatusResponseDto { Authenticated = false, User = null });

    private static async Task<IResult> ChangePasswordAsync(
        HttpContext context,
        IDbContextFactory<ControlDbContext> contextFactory,
        IPasswordHasher<UserAccount> passwordHasher,
        CsrfTokenService csrf,
        CancellationToken cancellationToken)
    {
        var validation = csrf.Validate(context);
        if (!validation.Succeeded)
        {
            return Error(StatusCodes.Status400BadRequest, validation.Detail, "csrf_failed");
        }

        var request = await ReadBodyAsync<ChangePasswordRequestDto>(context.Request, cancellationToken)
            .ConfigureAwait(false) ?? new ChangePasswordRequestDto();
        if (!long.TryParse(context.User.FindFirstValue(ClaimTypes.NameIdentifier), out var userId))
        {
            return Error(StatusCodes.Status401Unauthorized, "未登录", "unauthorized");
        }

        await using var database = await contextFactory.CreateDbContextAsync(cancellationToken).ConfigureAwait(false);
        var user = await database.UserAccounts.SingleOrDefaultAsync(
            candidate => candidate.Id == userId && candidate.IsActive,
            cancellationToken).ConfigureAwait(false);
        if (user is null)
        {
            return Error(StatusCodes.Status401Unauthorized, "未登录", "unauthorized");
        }

        if (passwordHasher.VerifyHashedPassword(user, user.PasswordHash, request.CurrentPassword) ==
            PasswordVerificationResult.Failed)
        {
            return Error(StatusCodes.Status400BadRequest, "当前密码错误", "invalid_password");
        }

        var passwordError = ValidatePassword(request.NewPassword, user.Username);
        if (passwordError is not null)
        {
            return Error(StatusCodes.Status400BadRequest, passwordError, "weak_password");
        }

        user.PasswordHash = passwordHasher.HashPassword(user, request.NewPassword);
        await database.SaveChangesAsync(cancellationToken).ConfigureAwait(false);
        await context.SignInAsync(
            CookieAuthenticationDefaults.AuthenticationScheme,
            CreatePrincipal(user),
            new AuthenticationProperties { IsPersistent = false }).ConfigureAwait(false);
        _ = csrf.IssueToken(context);
        return Results.Ok(new { detail = "密码已修改" });
    }

    private static string? ValidatePassword(string password, string username)
    {
        if (password.Length < 8)
        {
            return "密码长度至少为 8 个字符";
        }

        if (password.All(char.IsDigit))
        {
            return "密码不能全部为数字";
        }

        if (string.Equals(password, "password", StringComparison.OrdinalIgnoreCase) ||
            string.Equals(password, "password123", StringComparison.OrdinalIgnoreCase) ||
            string.Equals(password, "12345678", StringComparison.Ordinal))
        {
            return "密码过于常见";
        }

        if (username.Length >= 3 && password.Contains(username, StringComparison.OrdinalIgnoreCase))
        {
            return "密码与用户名过于相似";
        }

        return null;
    }

    private static ClaimsPrincipal CreatePrincipal(UserAccount user)
    {
        var claims = new List<Claim>
        {
            new(ClaimTypes.NameIdentifier, user.Id.ToString(System.Globalization.CultureInfo.InvariantCulture)),
            new(ClaimTypes.Name, user.Username),
            new(ScpCvClaimTypes.IsStaff, user.IsStaff ? "true" : "false"),
            new(ScpCvClaimTypes.IsSuperuser, user.IsSuperuser ? "true" : "false"),
        };
        foreach (var permission in ReadPermissions(user.PermissionsJson))
        {
            claims.Add(new Claim(ScpCvClaimTypes.Permission, permission));
        }

        return new ClaimsPrincipal(new ClaimsIdentity(
            claims,
            CookieAuthenticationDefaults.AuthenticationScheme,
            ClaimTypes.Name,
            ClaimTypes.Role));
    }

    private static bool TryReadUser(ClaimsPrincipal principal, out AuthUserDto user)
    {
        user = new AuthUserDto();
        if (principal.Identity?.IsAuthenticated != true ||
            !long.TryParse(principal.FindFirstValue(ClaimTypes.NameIdentifier), out var id) ||
            principal.Identity.Name is not { Length: > 0 } username)
        {
            return false;
        }

        user = new AuthUserDto
        {
            Id = id,
            Username = username,
            IsStaff = string.Equals(principal.FindFirstValue(ScpCvClaimTypes.IsStaff), "true", StringComparison.Ordinal),
            IsSuperuser = string.Equals(principal.FindFirstValue(ScpCvClaimTypes.IsSuperuser), "true", StringComparison.Ordinal),
        };
        return true;
    }

    private static string[] ReadPermissions(string json)
    {
        try
        {
            return JsonSerializer.Deserialize<string[]>(json) ?? [];
        }
        catch (JsonException)
        {
            return [];
        }
    }

    private static IResult Error(int statusCode, string detail, string code) =>
        Results.Json(new { detail, code }, statusCode: statusCode);

    private static async Task<T?> ReadBodyAsync<T>(HttpRequest request, CancellationToken cancellationToken)
    {
        if (request.ContentLength is 0)
        {
            return default;
        }

        try
        {
            return await JsonSerializer.DeserializeAsync<T>(
                request.Body,
                WebJsonOptions,
                cancellationToken).ConfigureAwait(false);
        }
        catch (JsonException)
        {
            return default;
        }
    }

    private static AuthUserDto ToDto(UserAccount user) => new()
    {
        Id = user.Id,
        Username = user.Username,
        IsStaff = user.IsStaff,
        IsSuperuser = user.IsSuperuser,
    };
}
