namespace ScpCv.ControlHost.Configuration;

public enum SafetyMode
{
    Simulation,
    Hardware,
}

public sealed record SafetyModeOptions(SafetyMode Mode)
{
    public bool IsSimulation => Mode == SafetyMode.Simulation;

    public static SafetyModeOptions Parse(string? value)
    {
        var configured = string.IsNullOrWhiteSpace(value) ? nameof(SafetyMode.Simulation) : value;
        if (!Enum.TryParse<SafetyMode>(configured, ignoreCase: true, out var mode))
        {
            throw new InvalidOperationException(
                $"未知 SafetyMode '{configured}'。允许值为 Simulation 或 Hardware。");
        }

        return new SafetyModeOptions(mode);
    }
}
