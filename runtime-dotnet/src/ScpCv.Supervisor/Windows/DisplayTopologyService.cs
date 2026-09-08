using System.Windows.Forms;

namespace ScpCv.Supervisor.Windows;

public sealed record DisplayTopologyItem(string DevicePath, int X, int Y, int Width, int Height, bool Primary, int Dpi);

public sealed class DisplayTopologyService
{
    public static IReadOnlyList<DisplayTopologyItem> Enumerate() => Screen.AllScreens
        .Select(screen => new DisplayTopologyItem(
            screen.DeviceName,
            screen.Bounds.X,
            screen.Bounds.Y,
            screen.Bounds.Width,
            screen.Bounds.Height,
            screen.Primary,
            96))
        .OrderByDescending(display => display.Primary)
        .ThenBy(display => display.X)
        .ThenBy(display => display.Y)
        .ToArray();

    public static IReadOnlyDictionary<int, DisplayTopologyItem> AssignFourOutputs()
    {
        var displays = Enumerate();
        if (displays.Count < 4) throw new InvalidOperationException($"需要 4 台显示器，当前仅检测到 {displays.Count} 台。");
        return Enumerable.Range(1, 4).ToDictionary(windowId => windowId, windowId => displays[windowId - 1]);
    }
}
