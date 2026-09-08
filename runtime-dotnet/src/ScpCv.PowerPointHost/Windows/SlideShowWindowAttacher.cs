using System.Diagnostics;
using System.Runtime.InteropServices;

namespace ScpCv.PowerPointHost.Windows;

public sealed record SlideShowSurfaceRequest(
    nint ParentHwnd,
    nint SlideShowHwnd,
    int ExpectedProcessId,
    DateTimeOffset ExpectedProcessStart,
    int ExpectedDpi,
    int X,
    int Y,
    int Width,
    int Height);

public sealed record SlideShowSurfaceResult(bool Attached, string Code, int ActualDpi);

public sealed class SlideShowWindowAttacher
{
    public static SlideShowSurfaceResult Attach(SlideShowSurfaceRequest request)
    {
        if (!OperatingSystem.IsWindows()) return new(false, "windows_only", 0);
        if (!IsWindow(request.ParentHwnd) || !IsWindow(request.SlideShowHwnd)) return new(false, "invalid_hwnd", 0);
        var pid = GetWindowThreadProcessId(request.SlideShowHwnd, out var rawPid);
        if (pid == 0 || rawPid != request.ExpectedProcessId) return new(false, "pid_mismatch", 0);
        try
        {
            using var process = Process.GetProcessById(request.ExpectedProcessId);
            var start = new DateTimeOffset(process.StartTime.ToUniversalTime(), TimeSpan.Zero);
            if (start != request.ExpectedProcessStart) return new(false, "process_start_mismatch", 0);
        }
        catch { return new(false, "process_unavailable", 0); }

        var dpi = GetDpiForWindow(request.SlideShowHwnd);
        if (request.ExpectedDpi > 0 && dpi != request.ExpectedDpi) return new(false, "dpi_mismatch", (int)dpi);
        _ = SetParent(request.SlideShowHwnd, request.ParentHwnd);
        if (GetParent(request.SlideShowHwnd) != request.ParentHwnd) return new(false, "attach_failed", (int)dpi);
        if (!SetWindowPos(request.SlideShowHwnd, IntPtr.Zero, request.X, request.Y, request.Width, request.Height, 0x0040))
            return new(false, "resize_failed", (int)dpi);
        return new(true, "attached", (int)dpi);
    }

    [DllImport("user32.dll")] private static extern bool IsWindow(nint hWnd);
    [DllImport("user32.dll")] private static extern uint GetWindowThreadProcessId(nint hWnd, out uint processId);
    [DllImport("user32.dll")] private static extern uint GetDpiForWindow(nint hWnd);
    [DllImport("user32.dll")] private static extern nint SetParent(nint child, nint parent);
    [DllImport("user32.dll")] private static extern nint GetParent(nint child);
    [DllImport("user32.dll")] private static extern bool SetWindowPos(nint hWnd, nint insertAfter, int x, int y, int cx, int cy, uint flags);
}
