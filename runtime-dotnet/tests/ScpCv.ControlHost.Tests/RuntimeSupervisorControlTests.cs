using System.Diagnostics;
using ScpCv.ControlHost.Ipc;
using ScpCv.ControlHost.Runtime;

namespace ScpCv.ControlHost.Tests;

public sealed class RuntimeSupervisorControlTests
{
    [Fact]
    public async Task StartFailsImmediatelyWhenSupervisorExitsBeforeWorkersAreReady()
    {
        if (!OperatingSystem.IsWindows()) return;

        var executable = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.Windows),
            "System32",
            "where.exe");
        var control = new RuntimeSupervisorControl(
            new RuntimeSupervisorOptions
            {
                ExecutablePath = executable,
                RuntimeRoot = AppContext.BaseDirectory,
                StatePath = Path.Combine(Path.GetTempPath(), $"scp-cv-{Guid.NewGuid():N}.json"),
                StartupTimeoutSeconds = 10,
            },
            readinessGate: new NeverReadyGate());

        var stopwatch = Stopwatch.StartNew();
        var result = await control.LaunchAsync("start", 1, CancellationToken.None);

        Assert.False(result.Accepted);
        Assert.Equal("supervisor_exited", result.Code);
        Assert.True(stopwatch.Elapsed < TimeSpan.FromSeconds(5));
    }

    private sealed class NeverReadyGate : IRuntimeReadinessGate
    {
        public async Task<RuntimeReadinessResult> WaitForRuntimeReadyAsync(
            long groupEpoch,
            TimeSpan timeout,
            CancellationToken cancellationToken = default)
        {
            await Task.Delay(Timeout.InfiniteTimeSpan, cancellationToken);
            return new RuntimeReadinessResult(false, ["player-1"]);
        }
    }
}
