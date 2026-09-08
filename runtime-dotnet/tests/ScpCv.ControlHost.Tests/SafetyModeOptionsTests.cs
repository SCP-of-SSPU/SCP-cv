using ScpCv.ControlHost.Configuration;

namespace ScpCv.ControlHost.Tests;

public sealed class SafetyModeOptionsTests
{
    [Fact]
    public void MissingConfigurationDefaultsToSimulation()
    {
        var options = SafetyModeOptions.Parse(null);

        Assert.Equal(SafetyMode.Simulation, options.Mode);
        Assert.True(options.IsSimulation);
    }

    [Fact]
    public void HardwareRequiresExplicitConfiguration()
    {
        var options = SafetyModeOptions.Parse("Hardware");

        Assert.Equal(SafetyMode.Hardware, options.Mode);
        Assert.False(options.IsSimulation);
    }

    [Fact]
    public void UnknownSafetyModeFailsClosed()
    {
        Assert.Throws<InvalidOperationException>(() => SafetyModeOptions.Parse("unsafe-auto"));
    }
}
