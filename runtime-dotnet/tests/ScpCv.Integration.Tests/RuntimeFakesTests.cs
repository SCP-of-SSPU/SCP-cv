using ScpCv.Integration.Tests.Fixtures;

namespace ScpCv.Integration.Tests;

public sealed class RuntimeFakesTests
{
    [Fact]
    public async Task FixtureProvidesDeterministicClockOfficeAndDeviceFakes()
    {
        await using var fixture = await ControlHostFixture.CreateAsync();
        var before = fixture.TimeProvider.GetUtcNow();

        fixture.TimeProvider.Advance(TimeSpan.FromSeconds(5));
        fixture.Devices.SetState("wall", "on");

        Assert.Equal(before.AddSeconds(5), fixture.TimeProvider.GetUtcNow());
        Assert.Equal("on", fixture.Devices.GetState("wall"));
        Assert.True(File.Exists(fixture.Database.Layout.DatabasePath));
    }
}
