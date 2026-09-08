using System.Collections.ObjectModel;
using System.Text;

namespace ScpCv.Infrastructure.Diagnostics;

public static class LogRedaction
{
    public const string RedactedValue = "[REDACTED]";

    private static readonly HashSet<string> SensitiveKeys = new(StringComparer.OrdinalIgnoreCase)
    {
        "authorization",
        "cookie",
        "set-cookie",
        "password",
        "current_password",
        "new_password",
        "csrf",
        "csrftoken",
        "csrfToken",
        "x-csrftoken",
        "session",
        "sessionid",
        "token",
        "access_token",
        "refresh_token",
        "claim_token",
        "secret",
        "api_key",
    };

    public static IReadOnlyDictionary<string, object?> Properties(
        IEnumerable<KeyValuePair<string, object?>> properties)
    {
        ArgumentNullException.ThrowIfNull(properties);
        var result = new Dictionary<string, object?>(StringComparer.Ordinal);
        foreach (var property in properties)
        {
            result[property.Key] = Value(property.Key, property.Value);
        }

        return new ReadOnlyDictionary<string, object?>(result);
    }

    public static object? Value(string key, object? value)
    {
        ArgumentNullException.ThrowIfNull(key);
        if (IsSensitiveKey(key))
        {
            return RedactedValue;
        }

        return value is string text ? RedactUri(text) : value;
    }

    private static bool IsSensitiveKey(string key) =>
        SensitiveKeys.Contains(key) ||
        key.EndsWith("_password", StringComparison.OrdinalIgnoreCase) ||
        key.EndsWith("_token", StringComparison.OrdinalIgnoreCase) ||
        key.EndsWith("_secret", StringComparison.OrdinalIgnoreCase);

    private static string RedactUri(string value)
    {
        if (!Uri.TryCreate(value, UriKind.Absolute, out var uri) ||
            (uri.Scheme != Uri.UriSchemeHttp && uri.Scheme != Uri.UriSchemeHttps))
        {
            return value;
        }

        var builder = new UriBuilder(uri);
        if (!string.IsNullOrEmpty(builder.UserName) || !string.IsNullOrEmpty(builder.Password))
        {
            builder.UserName = RedactedValue;
            builder.Password = RedactedValue;
        }

        if (!string.IsNullOrEmpty(builder.Query))
        {
            builder.Query = RedactQuery(builder.Query.AsSpan(1));
        }

        return builder.Uri.AbsoluteUri;
    }

    private static string RedactQuery(ReadOnlySpan<char> query)
    {
        var result = new StringBuilder(query.Length);
        foreach (var segment in query.ToString().Split('&', StringSplitOptions.RemoveEmptyEntries))
        {
            if (result.Length > 0)
            {
                result.Append('&');
            }

            var separator = segment.IndexOf('=', StringComparison.Ordinal);
            var encodedKey = separator < 0 ? segment : segment[..separator];
            var key = Uri.UnescapeDataString(encodedKey.Replace('+', ' '));
            result.Append(encodedKey);
            if (separator >= 0)
            {
                result.Append('=');
                result.Append(IsSensitiveKey(key) ? Uri.EscapeDataString(RedactedValue) : segment[(separator + 1)..]);
            }
        }

        return result.ToString();
    }
}
