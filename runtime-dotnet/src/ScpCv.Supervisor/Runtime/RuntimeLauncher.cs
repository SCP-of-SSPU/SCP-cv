using System.Diagnostics;
using ScpCv.Supervisor.Processes;

namespace ScpCv.Supervisor.Runtime;

public sealed class RuntimeLauncher(ProcessRegistry registry)
{
    public IReadOnlyList<OwnedProcess> Start(string runtimeRoot, string? mediaMtxPath = null)
    {
        var root = Path.GetFullPath(runtimeRoot);
        var started = new List<OwnedProcess>();
        try
        {
            for (var windowId = 1; windowId <= 4; windowId++)
                started.Add(StartProcess($"player-{windowId}", ResolveBinary(root, "ScpCv.PlayerWorker.exe"), $"--window-id {windowId}"));
            started.Add(StartProcess("audio", ResolveBinary(root, "ScpCv.AudioWorker.exe"), string.Empty));
            started.Add(StartProcess("office", ResolveBinary(root, "ScpCv.PowerPointHost.exe"), string.Empty));
            if (!string.IsNullOrWhiteSpace(mediaMtxPath)) started.Add(StartProcess("mediamtx", Path.GetFullPath(mediaMtxPath), string.Empty));
            return started;
        }
        catch
        {
            // 启动过程失败时只清理本次已经登记的自有子进程。
            foreach (var owned in started)
            {
                try
                {
                    if (ProcessRegistry.StillOwns(owned)) owned.Process.Kill(entireProcessTree: true);
                }
                catch (InvalidOperationException) { }
            }
            throw;
        }
    }

    private OwnedProcess StartProcess(string role, string path, string arguments)
    {
        if (!File.Exists(path)) throw new FileNotFoundException($"运行时组件不存在：{role}", path);
        var process = Process.Start(new ProcessStartInfo(path, arguments)
            {
                UseShellExecute = false,
                CreateNoWindow = false,
                WorkingDirectory = Path.GetDirectoryName(path) ?? AppContext.BaseDirectory,
            })
            ?? throw new InvalidOperationException($"无法启动 {role}");
        return registry.Register(role, process);
    }

    private static string ResolveBinary(string root, string fileName)
    {
        var direct = Path.Combine(root, fileName);
        if (File.Exists(direct)) return direct;

        // 允许从 runtime-dotnet 根目录直接运行开发构建；发布目录仍优先使用直达路径。
        var projectName = Path.GetFileNameWithoutExtension(fileName);
        IEnumerable<string> candidates = Directory.Exists(root)
            ? Directory.EnumerateFiles(root, fileName, SearchOption.AllDirectories)
                .Where(path => path.Contains($"{Path.DirectorySeparatorChar}{projectName}{Path.DirectorySeparatorChar}", StringComparison.OrdinalIgnoreCase))
                .OrderByDescending(File.GetLastWriteTimeUtc)
            : Array.Empty<string>();
        return candidates.FirstOrDefault() ?? direct;
    }
}
