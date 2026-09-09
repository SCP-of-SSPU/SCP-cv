using System.Diagnostics;
using ScpCv.ControlHost.Ipc;

namespace ScpCv.ControlHost.Runtime;

public sealed class RuntimeSupervisorOptions
{
    public const string SectionName = "Supervisor";
    public string ExecutablePath { get; set; } = string.Empty;
    public string RuntimeRoot { get; set; } = string.Empty;
    public string StatePath { get; set; } = string.Empty;
    public string MediaMtxPath { get; set; } = string.Empty;
}

/// <summary>ControlHost 发起的本机 Supervisor 控制通道；未配置时保持 simulation 的明确 unavailable。</summary>
public sealed class RuntimeSupervisorControl(
    RuntimeSupervisorOptions options,
    NamedPipeServer? pipeServer = null)
{
    public bool IsConfigured => !string.IsNullOrWhiteSpace(options.ExecutablePath);

    public Task<SupervisorLaunchResult> LaunchAsync(
        string action,
        CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        var executable = Path.GetFullPath(options.ExecutablePath);
        if (!File.Exists(executable))
        {
            return Task.FromResult(new SupervisorLaunchResult(false, "supervisor_unavailable", $"Supervisor 不存在：{executable}"));
        }

        var arguments = new List<string>
        {
            "--action", action,
            "--runtime-root", ResolvePath(options.RuntimeRoot),
            "--state", ResolvePath(options.StatePath),
        };
        if (!string.IsNullOrWhiteSpace(options.MediaMtxPath))
        {
            arguments.Add("--mediamtx");
            arguments.Add(Path.GetFullPath(options.MediaMtxPath));
        }
        if (pipeServer is not null)
        {
            arguments.Add("--control-pipe");
            arguments.Add(pipeServer.PipeName);
        }

        var startInfo = new ProcessStartInfo
        {
            FileName = executable,
            WorkingDirectory = Path.GetDirectoryName(executable) ?? AppContext.BaseDirectory,
            UseShellExecute = false,
            CreateNoWindow = false,
        };
        foreach (var argument in arguments)
        {
            startInfo.ArgumentList.Add(argument);
        }

        var process = Process.Start(startInfo);
        if (process is null)
        {
            return Task.FromResult(new SupervisorLaunchResult(false, "supervisor_start_failed", "无法启动 Supervisor。"));
        }
        process.Dispose();
        return Task.FromResult(new SupervisorLaunchResult(true, "accepted", $"Supervisor {action} 已启动。"));
    }

    private static string ResolvePath(string path) =>
        string.IsNullOrWhiteSpace(path) ? AppContext.BaseDirectory : Path.GetFullPath(path);
}

public sealed record SupervisorLaunchResult(bool Accepted, string Code, string Detail);
