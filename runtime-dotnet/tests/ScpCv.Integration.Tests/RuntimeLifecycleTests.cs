using System.Diagnostics;
using ScpCv.Domain.Model;
using ScpCv.Integration.Tests.Fixtures;
using ScpCv.Infrastructure.Runtime;
using ScpCv.Supervisor.Processes;

namespace ScpCv.Integration.Tests;

public sealed class RuntimeLifecycleTests
{
    [Fact]
    public async Task StopLatchRejectsNewWorkerAuthorityUntilExplicitStart()
    {
        await using var fixture = await ControlHostFixture.CreateAsync();
        var starting = await fixture.RuntimeAuthority.BeginStartAsync(Guid.NewGuid());
        await fixture.RuntimeAuthority.ArmAsync(starting.ExplicitStartRequestId!.Value, starting.GroupEpoch);
        await fixture.RuntimeAuthority.BeginDrainAsync("test-stop");
        await Assert.ThrowsAsync<RuntimeAuthorityException>(() => fixture.RuntimeAuthority.RegisterWorkerAsync(new(
            CommandTargetKind.Display, 1, Guid.NewGuid(), 1, DateTimeOffset.UtcNow, 1, starting.GroupEpoch, "[]")));
    }

    [Fact]
    public void ProcessRegistryRequiresPidStartTimeAndSessionEvidence()
    {
        var registry = new ProcessRegistry();
        using var current = Process.GetCurrentProcess();
        var owned = registry.Register("test", current);
        Assert.True(ProcessRegistry.StillOwns(owned));
        Assert.False(ProcessRegistry.StillOwns(owned with { StartTime = owned.StartTime.AddMilliseconds(1) }));
    }
}
