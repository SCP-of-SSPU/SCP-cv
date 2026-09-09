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
    public int StartupTimeoutSeconds { get; set; } = 30;
    public int StopTimeoutSeconds { get; set; } = 15;
}

/// <summary>ControlHost 发起的本机 Supervisor 控制通道；未配置时保持 simulation 的明确 unavailable。</summary>
public sealed class RuntimeSupervisorControl(
    RuntimeSupervisorOptions options,
    NamedPipeServer? pipeServer = null,
    IRuntimeReadinessGate? readinessGate = null)
{
    public bool IsConfigured => !string.IsNullOrWhiteSpace(options.ExecutablePath);

    public Task<SupervisorLaunchResult> LaunchAsync(
        string action,
        CancellationToken cancellationToken = default) =>
        LaunchAsync(action, expectedGroupEpoch: null, cancellationToken);

    public async Task<SupervisorLaunchResult> LaunchAsync(
        string action,
        long? expectedGroupEpoch,
        CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        var normalizedAction = action.Trim().ToLowerInvariant();
        if (normalizedAction is not ("start" or "stop" or "restart" or "status"))
        {
            return new SupervisorLaunchResult(false, "invalid_supervisor_action", $"不支持 Supervisor 动作：{action}");
        }
        if (readinessGate is not null && normalizedAction is ("start" or "restart") && expectedGroupEpoch is not > 0)
        {
            return new SupervisorLaunchResult(false, "missing_group_epoch", "启动动作缺少当前 group epoch。");
        }
        var executable = Path.GetFullPath(options.ExecutablePath);
        if (!File.Exists(executable))
        {
            return new SupervisorLaunchResult(false, "supervisor_unavailable", $"Supervisor 不存在：{executable}");
        }

        var arguments = new List<string>
        {
            "--action", normalizedAction,
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
            return new SupervisorLaunchResult(false, "supervisor_start_failed", "无法启动 Supervisor。");
        }
        using (process)
        {
            if (normalizedAction is "stop" or "status")
            {
                using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
                timeout.CancelAfter(TimeSpan.FromSeconds(Math.Max(1, options.StopTimeoutSeconds)));
                try
                {
                    await process.WaitForExitAsync(timeout.Token).ConfigureAwait(false);
                }
                catch (OperationCanceledException) when (!cancellationToken.IsCancellationRequested)
                {
                    return new SupervisorLaunchResult(false, "supervisor_timeout", $"Supervisor {normalizedAction} 未在时限内完成。");
                }

                return process.ExitCode == 0
                    ? new SupervisorLaunchResult(true, "completed", $"Supervisor {normalizedAction} 已完成。")
                    : new SupervisorLaunchResult(false, "supervisor_failed", $"Supervisor {normalizedAction} 退出码为 {process.ExitCode}。");
            }

            if (readinessGate is null)
            {
                return new SupervisorLaunchResult(true, "accepted", $"Supervisor {normalizedAction} 已启动。");
            }
            var groupEpoch = expectedGroupEpoch
                ?? throw new InvalidOperationException("启动动作缺少当前 group epoch。");
            using var monitoring = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
            var readinessTask = readinessGate.WaitForRuntimeReadyAsync(
                groupEpoch,
                TimeSpan.FromSeconds(Math.Max(1, options.StartupTimeoutSeconds)),
                monitoring.Token);
            var processExitTask = process.WaitForExitAsync(monitoring.Token);
            var completed = await Task.WhenAny(readinessTask, processExitTask).ConfigureAwait(false);
            if (completed == processExitTask)
            {
                await processExitTask.ConfigureAwait(false);
                monitoring.Cancel();
                await ObserveCancellationAsync(readinessTask).ConfigureAwait(false);
                return new SupervisorLaunchResult(
                    false,
                    "supervisor_exited",
                    $"Supervisor {normalizedAction} 在 Worker 就绪前退出，退出码为 {process.ExitCode}。");
            }

            var readiness = await readinessTask.ConfigureAwait(false);
            if (process.HasExited)
            {
                monitoring.Cancel();
                await ObserveCancellationAsync(processExitTask).ConfigureAwait(false);
                return new SupervisorLaunchResult(
                    false,
                    "supervisor_exited",
                    $"Supervisor {normalizedAction} 在 Worker 就绪时已退出，退出码为 {process.ExitCode}。");
            }

            monitoring.Cancel();
            await ObserveCancellationAsync(processExitTask).ConfigureAwait(false);
            return readiness.Ready
                ? new SupervisorLaunchResult(true, "runtime_ready", $"Supervisor {normalizedAction} 的全部 Worker 已就绪。")
                : new SupervisorLaunchResult(
                    false,
                    "runtime_ready_timeout",
                    $"Worker 就绪超时，缺少：{string.Join(", ", readiness.MissingRoles)}。");
        }
    }

    private static string ResolvePath(string path) =>
        string.IsNullOrWhiteSpace(path) ? AppContext.BaseDirectory : Path.GetFullPath(path);

    private static async Task ObserveCancellationAsync(Task task)
    {
        try
        {
            await task.ConfigureAwait(false);
        }
        catch (OperationCanceledException)
        {
        }
    }
}

public sealed record SupervisorLaunchResult(bool Accepted, string Code, string Detail);
