using System.Reflection;
using ScpCv.Contracts.Errors;

namespace ScpCv.Contracts.Tests;

public sealed class ErrorCodeTests
{
    [Fact]
    public void StableErrorCodesAreUniqueAndKeepLegacyValues()
    {
        var values = typeof(ErrorCodes)
            .GetFields(BindingFlags.Public | BindingFlags.Static)
            .Select(field => Assert.IsType<string>(field.GetRawConstantValue()))
            .ToArray();

        Assert.Equal(values.Length, values.Distinct(StringComparer.Ordinal).Count());
        Assert.Contains("invalid_json", values, StringComparer.Ordinal);
        Assert.Contains("unauthorized", values, StringComparer.Ordinal);
        Assert.Contains("playback_error", values, StringComparer.Ordinal);
        Assert.Contains("runtime_not_armed", values, StringComparer.Ordinal);
        Assert.Contains("stale_claim", values, StringComparer.Ordinal);
    }
}
