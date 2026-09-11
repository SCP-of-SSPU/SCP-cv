using System.Runtime.Versioning;

namespace ScpCv.Supervisor.Runtime;

/// <summary>
/// Supervisor 侧的启动门持有者：创建命名 ManualReset 事件，经 <c>--start-gate</c>
/// 传给需要连接 ControlHost 的子进程；身份登记完成后由 <see cref="Open"/> 放行。
/// </summary>
[SupportedOSPlatform("windows")]
public sealed class RuntimeStartGateHandle : IDisposable
{
    private readonly EventWaitHandle _gate;

    private RuntimeStartGateHandle(EventWaitHandle gate, string name)
    {
        _gate = gate;
        Name = name;
    }

    public string Name { get; }

    public static RuntimeStartGateHandle? Create(string? controlPipe)
    {
        if (string.IsNullOrWhiteSpace(controlPipe)) return null;

        var name = $"Local\\SCP-cv.startgate.{Guid.NewGuid():N}";
        return new RuntimeStartGateHandle(new EventWaitHandle(false, EventResetMode.ManualReset, name), name);
    }

    public void Open() => _gate.Set();

    public void Dispose() => _gate.Dispose();
}
