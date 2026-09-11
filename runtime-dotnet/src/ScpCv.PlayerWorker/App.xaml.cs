using System.Windows;
using ScpCv.Contracts.Ipc;
using ScpCv.Contracts.Runtime;
using ScpCv.PlayerWorker.Playback;

namespace ScpCv.PlayerWorker;

public partial class App : System.Windows.Application, IDisposable
{
    private CancellationTokenSource? _stop;
    private RuntimeWorkerSession? _session;
    private PlayerRuntimeHost? _runtime;
    private int _disposed;

    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);
        var windowId = int.TryParse(Option(e.Args, "window-id"), out var parsed) && parsed is >= 1 and <= 4 ? parsed : 1;
        var pipeName = Option(e.Args, "pipe-name");
        var startGate = Option(e.Args, "start-gate");
        var instanceId = Guid.TryParse(Option(e.Args, "instance-id"), out var id) ? id : Guid.NewGuid();
        var window = new PlayerWindow();
        var screens = System.Windows.Forms.Screen.AllScreens;
        var screen = screens[Math.Min(windowId - 1, screens.Length - 1)].Bounds;
        window.AssignBounds(screen.X, screen.Y, screen.Width, screen.Height);
        window.Show();
        if (string.IsNullOrWhiteSpace(pipeName)) return;

        _stop = new CancellationTokenSource();
        _session = new RuntimeWorkerSession(pipeName, new RuntimeWorkerIdentity(
            $"player-{windowId}",
            instanceId,
            new IpcTargetDto { Kind = "display", Id = windowId },
            ["wpf", "libvlc", "webview2", "windows.data.pdf", "image"]));
        _runtime = new PlayerRuntimeHost(window, windowId, _session);
        _ = RunRuntimeAsync(_session, _runtime, startGate, _stop.Token);
    }

    protected override void OnExit(ExitEventArgs e)
    {
        Dispose();
        base.OnExit(e);
    }

    public void Dispose()
    {
        if (Interlocked.Exchange(ref _disposed, 1) != 0) return;
        _stop?.Cancel();
        _session?.DisposeAsync().AsTask().GetAwaiter().GetResult();
        _runtime?.DisposeAsync().AsTask().GetAwaiter().GetResult();
        _stop?.Dispose();
        GC.SuppressFinalize(this);
    }

    private async Task RunRuntimeAsync(
        RuntimeWorkerSession session,
        PlayerRuntimeHost runtime,
        string? startGate,
        CancellationToken cancellationToken)
    {
        try
        {
            await RuntimeStartGate.WaitAsync(startGate, cancellationToken: cancellationToken);
            await session.RunAsync(runtime.ExecuteAsync, cancellationToken);
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested) { }
        catch (Exception exception)
        {
            await Dispatcher.InvokeAsync(() =>
            {
                System.Windows.MessageBox.Show(
                    exception.Message,
                    "PlayerWorker 运行时故障",
                    MessageBoxButton.OK,
                    MessageBoxImage.Error);
                Shutdown(1);
            });
        }
    }

    private static string? Option(string[] values, string name)
    {
        var prefix = $"--{name}=";
        var inline = values.FirstOrDefault(value => value.StartsWith(prefix, StringComparison.OrdinalIgnoreCase));
        if (inline is not null) return inline[prefix.Length..];
        var index = Array.FindIndex(values, value => string.Equals(value, $"--{name}", StringComparison.OrdinalIgnoreCase));
        return index >= 0 && index + 1 < values.Length ? values[index + 1] : null;
    }
}
