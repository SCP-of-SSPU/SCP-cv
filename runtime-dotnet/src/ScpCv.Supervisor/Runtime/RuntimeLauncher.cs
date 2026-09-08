using System.Diagnostics;
using ScpCv.Supervisor.Processes;

namespace ScpCv.Supervisor.Runtime;

public sealed class RuntimeLauncher(ProcessRegistry registry)
{
    public IReadOnlyList<OwnedProcess> Start(string runtimeRoot, string? mediaMtxPath = null)
    {
        var root = Path.GetFullPath(runtimeRoot);
        var started = new List<OwnedProcess>();
        for (var windowId = 1; windowId <= 4; windowId++)
            started.Add(StartProcess($"player-{windowId}", Path.Combine(root, "ScpCv.PlayerWorker.exe"), $"--window-id {windowId}"));
        started.Add(StartProcess("audio", Path.Combine(root, "ScpCv.AudioWorker.exe"), string.Empty));
        started.Add(StartProcess("office", Path.Combine(root, "ScpCv.PowerPointHost.exe"), string.Empty));
        if (!string.IsNullOrWhiteSpace(mediaMtxPath)) started.Add(StartProcess("mediamtx", Path.GetFullPath(mediaMtxPath), string.Empty));
        return started;
    }

    private OwnedProcess StartProcess(string role, string path, string arguments)
    {
        if (!File.Exists(path)) throw new FileNotFoundException($"运行时组件不存在：{role}", path);
        var process = Process.Start(new ProcessStartInfo(path, arguments) { UseShellExecute = false, CreateNoWindow = false })
            ?? throw new InvalidOperationException($"无法启动 {role}");
        return registry.Register(role, process);
    }
}
