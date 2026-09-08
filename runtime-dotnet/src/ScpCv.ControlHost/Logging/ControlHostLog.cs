using Microsoft.Extensions.Logging;
using ScpCv.ControlHost.Configuration;

namespace ScpCv.ControlHost.Logging;

internal static partial class ControlHostLog
{
    [LoggerMessage(
        EventId = 1000,
        Level = LogLevel.Information,
        Message = "ControlHost initialized with safety mode {SafetyMode} and database {DatabaseFileName}")]
    public static partial void Initialized(
        ILogger logger,
        SafetyMode safetyMode,
        string databaseFileName);
}
