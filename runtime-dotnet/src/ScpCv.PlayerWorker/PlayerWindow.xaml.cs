using System.Windows;
using System.Windows.Interop;

namespace ScpCv.PlayerWorker;

/// <summary>单实例 PlayerWorker 的无边框输出窗口；显示器坐标由 Supervisor 提供。</summary>
public partial class PlayerWindow : Window
{
    public PlayerWindow()
    {
        InitializeComponent();
        SourceInitialized += (_, _) => ApplyPerMonitorDpiAwareness();
    }

    public void AssignBounds(int x, int y, int width, int height)
    {
        Left = x;
        Top = y;
        Width = width;
        Height = height;
    }

    public void SetSurface(FrameworkElement surface)
    {
        ArgumentNullException.ThrowIfNull(surface);
        SurfaceHost.Children.Clear();
        SurfaceHost.Children.Add(surface);
    }

    public nint NativeHandle => new WindowInteropHelper(this).Handle;

    public int NativeDpi => NativeHandle == 0 ? 0 : checked((int)GetDpiForWindow(NativeHandle));

    [System.Runtime.InteropServices.DllImport("user32.dll")]
    private static extern uint GetDpiForWindow(nint hWnd);

    private static void ApplyPerMonitorDpiAwareness()
    {
        // WPF 使用系统 DPI；真实混合 DPI 映射由 Supervisor 的拓扑快照和 AttachSurface 再校验。
    }
}
