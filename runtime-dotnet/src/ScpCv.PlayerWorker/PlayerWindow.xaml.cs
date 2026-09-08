using System.Windows;

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

    private static void ApplyPerMonitorDpiAwareness()
    {
        // WPF 使用系统 DPI；真实混合 DPI 映射由 Supervisor 的拓扑快照和 AttachSurface 再校验。
    }
}
