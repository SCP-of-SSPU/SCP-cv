using System.Text.Json;
using ScpCv.Contracts.Http;

namespace ScpCv.Contracts.Tests;

public sealed class HttpContractTests
{
    [Fact]
    public void AuthDtosKeepExistingMixedAndSnakeCaseFieldNames()
    {
        var csrf = Serialize(new CsrfTokenResponseDto { CsrfToken = "token" });
        var user = Serialize(new AuthUserDto
        {
            Id = 1,
            Username = "admin",
            IsStaff = true,
            IsSuperuser = true,
        });

        AssertPropertySet(csrf, "csrfToken");
        AssertPropertySet(user, "id", "username", "is_staff", "is_superuser");
    }

    [Fact]
    public void MediaAndPlaybackDtosKeepRuntimeFactFields()
    {
        var source = Serialize(new MediaSourceDto
        {
            Id = 7,
            SourceType = "ppt",
            PlaybackMode = "pdf",
        });
        var session = Serialize(new PlaybackSessionDto
        {
            WindowId = 2,
            SourceType = "ppt",
            PlaybackMode = "powerpoint",
        });
        var runtime = Serialize(new RuntimeStateDto { MutedWindows = [2, 3] });

        Assert.Equal("ppt", source.GetProperty("source_type").GetString());
        Assert.Equal("pdf", source.GetProperty("playback_mode").GetString());
        Assert.Equal(2, session.GetProperty("window_id").GetInt32());
        Assert.Equal("powerpoint", session.GetProperty("playback_mode").GetString());
        Assert.Equal([2, 3], runtime.GetProperty("muted_windows").EnumerateArray().Select(value => value.GetInt32()));
        Assert.DoesNotContain(session.EnumerateObject(), property => char.IsUpper(property.Name[0]));
    }

    [Theory]
    [InlineData("unset", null)]
    [InlineData("empty", null)]
    [InlineData("set", 42L)]
    public void ScenarioTargetKeepsThreeStateSourceContract(string sourceState, long? sourceId)
    {
        var target = Serialize(new ScenarioTargetDto
        {
            WindowId = 4,
            SourceState = sourceState,
            SourceId = sourceId,
        });

        Assert.Equal(4, target.GetProperty("window_id").GetInt32());
        Assert.Equal(sourceState, target.GetProperty("source_state").GetString());
        if (sourceId is null)
        {
            Assert.Equal(JsonValueKind.Null, target.GetProperty("source_id").ValueKind);
        }
        else
        {
            Assert.Equal(sourceId.Value, target.GetProperty("source_id").GetInt64());
        }
    }

    [Theory]
    [InlineData("AuthUser.yaml", "is_staff", "is_superuser")]
    [InlineData("CsrfTokenResponse.yaml", "csrfToken", null)]
    [InlineData("MediaSource.yaml", "source_type", "playback_mode")]
    [InlineData("SessionSnapshot.yaml", "window_id", "playback_mode")]
    [InlineData("RuntimeSnapshot.yaml", "muted_windows", null)]
    [InlineData("ScenarioTarget.yaml", "window_id", "source_state")]
    public void OpenApiSchemasDeclareCompatibilityCriticalFields(
        string schemaFile,
        string requiredField,
        string? secondRequiredField)
    {
        var schema = File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "OpenApiSchemas", schemaFile));

        Assert.Contains($"  - {requiredField}", schema, StringComparison.Ordinal);
        Assert.Contains($"  {requiredField}:", schema, StringComparison.Ordinal);
        if (secondRequiredField is not null)
        {
            Assert.Contains($"  - {secondRequiredField}", schema, StringComparison.Ordinal);
            Assert.Contains($"  {secondRequiredField}:", schema, StringComparison.Ordinal);
        }
    }

    private static JsonElement Serialize<T>(T value) =>
        JsonSerializer.SerializeToElement(value);

    private static void AssertPropertySet(JsonElement element, params string[] expected) =>
        Assert.Equal(expected.Order(), element.EnumerateObject().Select(property => property.Name).Order());
}
