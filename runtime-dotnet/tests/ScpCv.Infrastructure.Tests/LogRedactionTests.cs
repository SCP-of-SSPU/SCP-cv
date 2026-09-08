using ScpCv.Infrastructure.Diagnostics;

namespace ScpCv.Infrastructure.Tests;

public sealed class LogRedactionTests
{
    [Fact]
    public void SensitiveKeysAreRedactedCaseInsensitively()
    {
        var redacted = LogRedaction.Properties(new Dictionary<string, object?>
        {
            ["username"] = "admin",
            ["PASSWORD"] = "plain-text",
            ["claim_token"] = "execution-secret",
            ["Authorization"] = "Bearer session-secret",
        });

        Assert.Equal("admin", redacted["username"]);
        Assert.Equal(LogRedaction.RedactedValue, redacted["PASSWORD"]);
        Assert.Equal(LogRedaction.RedactedValue, redacted["claim_token"]);
        Assert.Equal(LogRedaction.RedactedValue, redacted["Authorization"]);
    }

    [Fact]
    public void CredentialedUrlKeepsDestinationButRemovesSecrets()
    {
        var redacted = Assert.IsType<string>(LogRedaction.Value(
            "source_uri",
            "https://user:pass@example.test/media?id=7&access_token=secret&quality=high"));

        Assert.Contains("example.test/media", redacted, StringComparison.Ordinal);
        Assert.Contains("id=7", redacted, StringComparison.Ordinal);
        Assert.Contains("quality=high", redacted, StringComparison.Ordinal);
        Assert.DoesNotContain("user", redacted, StringComparison.Ordinal);
        Assert.DoesNotContain("pass", redacted, StringComparison.Ordinal);
        Assert.DoesNotContain("secret", redacted, StringComparison.Ordinal);
        Assert.Contains(Uri.EscapeDataString(LogRedaction.RedactedValue), redacted, StringComparison.Ordinal);
    }
}
