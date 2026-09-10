using System.Runtime.InteropServices;
using NAudio.CoreAudioApi;
using ScpCv.Contracts.Http;

namespace ScpCv.Infrastructure.Playback;

public sealed record DisplayTopologySnapshot(
    bool Available,
    IReadOnlyList<DisplayTargetDto> Targets,
    string Backend,
    string Detail = "");

public interface IDisplayTopologyProvider
{
    DisplayTopologySnapshot GetCurrent();
}

public sealed class SimulationDisplayTopologyProvider : IDisplayTopologyProvider
{
    private static readonly IReadOnlyList<DisplayTargetDto> Targets =
    [
        new DisplayTargetDto
        {
            Index = 1,
            Name = "模拟显示器",
            Width = 1920,
            Height = 1080,
            X = 0,
            Y = 0,
            IsPrimary = true,
        },
    ];

    public DisplayTopologySnapshot GetCurrent() => new(true, Targets, "simulation");
}

public sealed class WindowsDisplayTopologyProvider : IDisplayTopologyProvider
{
    private const uint PrimaryMonitor = 1;

    public DisplayTopologySnapshot GetCurrent()
    {
        if (!OperatingSystem.IsWindows())
            return new(false, [], "windows_display_topology_unavailable", "当前操作系统不是 Windows。");
        if (!Environment.UserInteractive)
            return new(false, [], "windows_display_topology_unavailable", "ControlHost 不在交互桌面会话中。");

        var previousDpiContext = SetThreadDpiAwarenessContext(new nint(-4)); // PER_MONITOR_AWARE_V2
        try
        {
            try
            {
                var monitors = new List<NativeMonitor>();
                MonitorEnumProc callback = (monitor, _, _, _) =>
                {
                    var info = new MonitorInfoEx { Size = Marshal.SizeOf<MonitorInfoEx>() };
                    if (GetMonitorInfo(monitor, ref info))
                    {
                        monitors.Add(new NativeMonitor(
                            info.DeviceName,
                            info.Monitor.Left,
                            info.Monitor.Top,
                            info.Monitor.Right - info.Monitor.Left,
                            info.Monitor.Bottom - info.Monitor.Top,
                            (info.Flags & PrimaryMonitor) != 0));
                    }
                    return true;
                };
                if (!EnumDisplayMonitors(0, 0, callback, 0))
                    return new(false, [], "windows_display_topology_unavailable", $"EnumDisplayMonitors 失败：{Marshal.GetLastWin32Error()}。");

                var targets = monitors
                    .OrderByDescending(display => display.Primary)
                    .ThenBy(display => display.X)
                    .ThenBy(display => display.Y)
                    .Select((display, index) => new DisplayTargetDto
                    {
                        Index = index + 1,
                        Name = display.DeviceName,
                        Width = display.Width,
                        Height = display.Height,
                        X = display.X,
                        Y = display.Y,
                        IsPrimary = display.Primary,
                    })
                    .ToArray();
                return targets.Length == 0
                    ? new(false, [], "windows_display_topology_unavailable", "交互桌面没有可用显示器。")
                    : new(true, targets, "windows_display_topology");
            }
            catch (Exception exception) when (exception is ExternalException or InvalidOperationException)
            {
                return new(false, [], "windows_display_topology_unavailable", $"显示器枚举失败：{exception.Message}");
            }
        }
        finally
        {
            if (previousDpiContext != 0) _ = SetThreadDpiAwarenessContext(previousDpiContext);
        }
    }

    private delegate bool MonitorEnumProc(nint monitor, nint deviceContext, nint monitorRect, nint userData);

    [DllImport("user32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool EnumDisplayMonitors(
        nint deviceContext,
        nint clipRect,
        MonitorEnumProc callback,
        nint userData);

    [DllImport("user32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool GetMonitorInfo(nint monitor, ref MonitorInfoEx monitorInfo);

    [DllImport("user32.dll")]
    private static extern nint SetThreadDpiAwarenessContext(nint dpiContext);

    [StructLayout(LayoutKind.Sequential)]
    private struct NativeRect
    {
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    private struct MonitorInfoEx
    {
        public int Size;
        public NativeRect Monitor;
        public NativeRect Work;
        public uint Flags;

        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)]
        public string DeviceName;
    }

    private sealed record NativeMonitor(
        string DeviceName,
        int X,
        int Y,
        int Width,
        int Height,
        bool Primary);
}

public sealed record SystemAudioSnapshot(
    bool Available,
    int Level,
    bool Muted,
    string Backend,
    string Detail = "");

public interface ISystemAudioController
{
    bool IsHardware { get; }
    SystemAudioSnapshot GetCurrent();
    SystemAudioSnapshot Apply(int? level, bool? muted);
}

public sealed class SimulationSystemAudioController : ISystemAudioController
{
    public bool IsHardware => false;

    public SystemAudioSnapshot GetCurrent() =>
        new(false, 0, false, "runtime_state", "Simulation 模式不访问系统音频设备。");

    public SystemAudioSnapshot Apply(int? level, bool? muted) => GetCurrent();
}

public sealed class WindowsCoreAudioController : ISystemAudioController
{
    public bool IsHardware => true;

    public SystemAudioSnapshot GetCurrent() => Execute(endpoint => Snapshot(endpoint));

    public SystemAudioSnapshot Apply(int? level, bool? muted) => Execute(endpoint =>
    {
        var current = Snapshot(endpoint);
        var targetLevel = level ?? current.Level;
        var targetMuted = muted ?? (targetLevel == 0 || current.Muted);
        endpoint.MasterVolumeLevelScalar = targetLevel / 100f;
        endpoint.Mute = targetMuted;
        return Snapshot(endpoint);
    });

    private static SystemAudioSnapshot Execute(Func<AudioEndpointVolume, SystemAudioSnapshot> operation)
    {
        if (!OperatingSystem.IsWindows())
            return Unavailable("当前操作系统不是 Windows。");
        if (!Environment.UserInteractive)
            return Unavailable("ControlHost 不在交互桌面会话中。");

        try
        {
            using var enumerator = new MMDeviceEnumerator();
            using var device = enumerator.GetDefaultAudioEndpoint(DataFlow.Render, Role.Multimedia);
            return operation(device.AudioEndpointVolume);
        }
        catch (Exception exception) when (exception is COMException or InvalidOperationException)
        {
            return Unavailable($"默认渲染设备不可用：{exception.Message}");
        }
    }

    private static SystemAudioSnapshot Snapshot(AudioEndpointVolume endpoint) => new(
        true,
        Math.Clamp((int)Math.Round(endpoint.MasterVolumeLevelScalar * 100, MidpointRounding.AwayFromZero), 0, 100),
        endpoint.Mute,
        "windows_core_audio");

    private static SystemAudioSnapshot Unavailable(string detail) =>
        new(false, 0, false, "windows_core_audio_unavailable", detail);
}
