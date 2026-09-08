using ScpCv.Domain.Rules;

namespace ScpCv.Domain.Tests;

public sealed class ResourceSwitchTests
{
    [Fact]
    public void NewReadyGenerationIsAccepted()
    {
        var result = ResourceSwitchPolicy.Decide(
            new ResourceKey(1, "a", "web"), 3,
            new ResourceKey(2, "b", "web"), 4, true, true);

        Assert.True(result.Accepted);
        Assert.False(result.KeepCurrent);
    }

    [Theory]
    [InlineData(false, "candidate_not_ready")]
    [InlineData(true, "stale_generation")]
    public void LateOrUnreadyResourcesKeepHealthyCurrent(bool ready, string code)
    {
        var result = ResourceSwitchPolicy.Decide(
            new ResourceKey(1, "a", "web"), 4,
            new ResourceKey(2, "b", "web"), ready ? 3 : 5, ready, true);

        Assert.False(result.Accepted);
        Assert.True(result.KeepCurrent);
        Assert.Equal(code, result.Code);
    }
}
