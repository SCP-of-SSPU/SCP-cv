using System.Runtime.InteropServices;
using System.Text.Json;
using System.Windows.Interop;
using System.Windows.Threading;

namespace ScpCv.InteropProbe;

internal static partial class Program
{
    private const int WindowStyleIndex = -16;
    private const long ChildWindowStyle = 0x40000000L;
    private const long PopupWindowStyle = 0x80000000L;
    private static readonly nint PerMonitorAwareV2 = new(-4);
    private static readonly JsonSerializerOptions JsonOptions = new() { WriteIndented = true };

    [STAThread]
    public static int Main(string[] args)
    {
        if (!OperatingSystem.IsWindows())
        {
            Console.Error.WriteLine("ScpCv.InteropProbe 仅支持 Windows 交互桌面。");
            return 1;
        }

        var officeHandle = ParseOfficeHandle(args);
        var dpiAwarenessSet = SetProcessDpiAwarenessContext(PerMonitorAwareV2);
        var apartment = Thread.CurrentThread.GetApartmentState();
        var dispatcherPumped = PumpDispatcherOnce();
        using var parent = CreateProbeWindow("SCP-cv Interop Probe Parent");
        using var child = CreateProbeWindow("SCP-cv Interop Probe Child");
        var childStyle = GetWindowLongPtr(child.Handle, WindowStyleIndex).ToInt64();
        _ = SetWindowLongPtr(
            child.Handle,
            WindowStyleIndex,
            new nint((childStyle | ChildWindowStyle) & ~PopupWindowStyle));
        _ = SetParent(child.Handle, parent.Handle);
        var setParentError = Marshal.GetLastPInvokeError();
        var childAttached = GetParent(child.Handle) == parent.Handle;
        var parentDetails = InspectWindow(parent.Handle);
        var childDetails = InspectWindow(child.Handle);
        WindowDetails? officeDetails = officeHandle is null ? null : InspectWindow(officeHandle.Value);

        var result = new
        {
            apartment = apartment.ToString(),
            dispatcher_pumped = dispatcherPumped,
            dpi_awareness_set = dpiAwarenessSet,
            set_parent_verified = childAttached,
            set_parent_error = setParentError,
            parent = parentDetails,
            child = childDetails,
            office = officeDetails,
        };
        Console.WriteLine(JsonSerializer.Serialize(result, JsonOptions));

        var officeValid = officeDetails is null || officeDetails.IsWindow;
        return apartment == ApartmentState.STA && dispatcherPumped && childAttached && officeValid ? 0 : 2;
    }

    private static nint? ParseOfficeHandle(string[] args)
    {
        for (var index = 0; index < args.Length; index++)
        {
            if (!string.Equals(args[index], "--office-hwnd", StringComparison.OrdinalIgnoreCase))
            {
                continue;
            }

            if (index + 1 >= args.Length || !long.TryParse(args[index + 1], out var rawHandle) || rawHandle <= 0)
            {
                throw new ArgumentException("--office-hwnd 需要一个正整数 HWND。");
            }

            return new nint(rawHandle);
        }

        return null;
    }

    private static bool PumpDispatcherOnce()
    {
        var frame = new DispatcherFrame();
        _ = Dispatcher.CurrentDispatcher.BeginInvoke(
            DispatcherPriority.Background,
            new Action(() => frame.Continue = false));
        Dispatcher.PushFrame(frame);
        return !frame.Continue;
    }

    private static HwndSource CreateProbeWindow(string name) =>
        new(new HwndSourceParameters(name)
        {
            Width = 64,
            Height = 64,
            WindowStyle = unchecked((int)0x80000000),
        });

    private static WindowDetails InspectWindow(nint handle)
    {
        var isWindow = IsWindow(handle);
        uint processId = 0;
        var threadId = isWindow ? GetWindowThreadProcessId(handle, out processId) : 0;
        var dpi = isWindow ? GetDpiForWindow(handle) : 0;
        NativeRectangle rectangle = default;
        var hasRectangle = isWindow && GetWindowRect(handle, out rectangle);
        return new WindowDetails(
            handle.ToInt64(),
            isWindow,
            processId,
            threadId,
            dpi,
            hasRectangle ? rectangle.Left : 0,
            hasRectangle ? rectangle.Top : 0,
            hasRectangle ? rectangle.Right - rectangle.Left : 0,
            hasRectangle ? rectangle.Bottom - rectangle.Top : 0);
    }

    private sealed record WindowDetails(
        long Handle,
        bool IsWindow,
        uint ProcessId,
        uint ThreadId,
        uint Dpi,
        int X,
        int Y,
        int Width,
        int Height);

    [StructLayout(LayoutKind.Sequential)]
    private struct NativeRectangle
    {
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }

    [LibraryImport("user32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static partial bool SetProcessDpiAwarenessContext(nint dpiContext);

    [LibraryImport("user32.dll", SetLastError = true)]
    private static partial nint SetParent(nint childWindow, nint newParentWindow);

    [LibraryImport("user32.dll", EntryPoint = "GetWindowLongPtrW", SetLastError = true)]
    private static partial nint GetWindowLongPtr(nint window, int index);

    [LibraryImport("user32.dll", EntryPoint = "SetWindowLongPtrW", SetLastError = true)]
    private static partial nint SetWindowLongPtr(nint window, int index, nint newValue);

    [LibraryImport("user32.dll")]
    private static partial nint GetParent(nint window);

    [LibraryImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static partial bool IsWindow(nint window);

    [LibraryImport("user32.dll")]
    private static partial uint GetWindowThreadProcessId(nint window, out uint processId);

    [LibraryImport("user32.dll")]
    private static partial uint GetDpiForWindow(nint window);

    [LibraryImport("user32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static partial bool GetWindowRect(nint window, out NativeRectangle rectangle);
}
