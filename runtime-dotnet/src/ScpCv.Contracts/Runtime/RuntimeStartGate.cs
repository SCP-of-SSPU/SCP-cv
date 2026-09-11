using System.Runtime.Versioning;

namespace ScpCv.Contracts.Runtime;

/// <summary>
/// Supervisor 与 Worker 之间的启动门。
/// Supervisor 先启动全部子进程，再完成 ControlHost 身份登记，最后打开此门；
/// Worker 在门打开前不得连接 Named Pipe。否则会出现“子进程先连接、Supervisor 后登记”
/// 的确定性竞态：ControlHost 按安全规则拒绝未登记身份，PowerPointHost 随即退出并触发整组停止。
/// </summary>
public static class RuntimeStartGate
{
    private static readonly TimeSpan DefaultTimeout = TimeSpan.FromSeconds(60);

    /// <summary>
    /// 等待 Supervisor 完成身份登记。未提供门名称时立即返回，兼容单进程诊断模式。
    /// 等待超时或取消后仍返回，让调用方按既有连接逻辑报错，避免新增无界挂起。
    /// </summary>
    [SupportedOSPlatform("windows")]
    public static async Task WaitAsync(
        string? name,
        TimeSpan? timeout = null,
        CancellationToken cancellationToken = default)
    {
        if (string.IsNullOrWhiteSpace(name)) return;

        using var gate = new EventWaitHandle(false, EventResetMode.ManualReset, name);
        var handles = new WaitHandle[] { gate, cancellationToken.WaitHandle };
        await Task.Run(
                () => WaitHandle.WaitAny(handles, timeout ?? DefaultTimeout),
                CancellationToken.None)
            .ConfigureAwait(false);
    }
}
