using ScpCv.Supervisor.Processes;

namespace ScpCv.Supervisor.Runtime;

public sealed class ShutdownCoordinator(ProcessRegistry registry)
{
    public async Task StopAsync(CancellationToken cancellationToken = default)
    {
        foreach (var owned in registry.Snapshot())
        {
            if (!ProcessRegistry.StillOwns(owned)) { registry.Remove(owned.ProcessId); continue; }
            try { owned.Process.CloseMainWindow(); } catch (InvalidOperationException) { }
        }

        var deadline = DateTimeOffset.UtcNow.AddSeconds(5);
        while (DateTimeOffset.UtcNow < deadline && registry.Snapshot().Any(ProcessRegistry.StillOwns))
            await Task.Delay(100, cancellationToken).ConfigureAwait(false);

        foreach (var owned in registry.Snapshot())
        {
            if (!ProcessRegistry.StillOwns(owned)) { registry.Remove(owned.ProcessId); continue; }
            // Office 进程只允许协作退出；不能证明 COM 所有权时绝不强杀。
            if (owned.Role == "office") continue;
            owned.Process.Kill(entireProcessTree: true);
            await owned.Process.WaitForExitAsync(cancellationToken).WaitAsync(TimeSpan.FromSeconds(3), cancellationToken).ConfigureAwait(false);
            registry.Remove(owned.ProcessId);
        }
    }
}
