using System.Text.Json.Serialization;

namespace ScpCv.Contracts.Http;

public sealed record AuthUserDto
{
    [JsonPropertyName("id")]
    public long Id { get; init; }

    [JsonPropertyName("username")]
    public string Username { get; init; } = string.Empty;

    [JsonPropertyName("is_staff")]
    public bool IsStaff { get; init; }

    [JsonPropertyName("is_superuser")]
    public bool IsSuperuser { get; init; }
}

public sealed record CsrfTokenResponseDto
{
    [JsonPropertyName("csrfToken")]
    public string CsrfToken { get; init; } = string.Empty;
}

public sealed record LoginRequestDto
{
    [JsonPropertyName("username")]
    public string Username { get; init; } = string.Empty;

    [JsonPropertyName("password")]
    public string Password { get; init; } = string.Empty;
}

public sealed record ChangePasswordRequestDto
{
    [JsonPropertyName("current_password")]
    public string CurrentPassword { get; init; } = string.Empty;

    [JsonPropertyName("new_password")]
    public string NewPassword { get; init; } = string.Empty;
}

public sealed record AuthUserResponseDto
{
    [JsonPropertyName("user")]
    public AuthUserDto User { get; init; } = new();
}

public sealed record AuthStatusResponseDto
{
    [JsonPropertyName("authenticated")]
    public bool Authenticated { get; init; }

    [JsonPropertyName("user")]
    public AuthUserDto? User { get; init; }
}
