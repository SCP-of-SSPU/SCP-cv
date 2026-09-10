using System.IO;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using LibVLCSharp.Shared;
using LibVLCSharp.WPF;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.Wpf;
using ScpCv.Contracts.Ipc;
using ScpCv.Contracts.Runtime;
using ScpCv.PlayerWorker.Adapters;
using VlcMediaPlayer = LibVLCSharp.Shared.MediaPlayer;
using WpfBrushes = System.Windows.Media.Brushes;
using WpfHorizontalAlignment = System.Windows.HorizontalAlignment;

namespace ScpCv.PlayerWorker.Playback;

/// <summary>单个输出进程内拥有真实 WPF/WebView2/LibVLC/PDF/图片资源，不跨进程传递原生对象。</summary>
public sealed partial class PlayerRuntimeHost(
    PlayerWindow window,
    int windowId,
    RuntimeWorkerSession? officeSession = null) : IAsyncDisposable
{
    private readonly PlayerWindow _window = window;
    private readonly int _windowId = windowId;
    private readonly RuntimeWorkerSession? _officeSession = officeSession;
    private readonly Dictionary<string, SurfaceResource> _warmWebResources = new(StringComparer.Ordinal);
    private SurfaceResource? _current;
    private long _sourceId;
    private long _generation;
    private string _state = "idle";
    private int _currentSlide;
    private int _totalSlides;
    private long _officePresentationIdentity;
    private long _officeHostEpoch;
    private long _officeSlotEpoch;
    private int _disposed;

    public Task<WorkerExecutionResult> ExecuteAsync(
        CommandLeaseDto lease,
        CancellationToken cancellationToken) =>
        _window.Dispatcher.InvokeAsync(() => ExecuteCoreAsync(lease, cancellationToken)).Task.Unwrap();

    public async ValueTask DisposeAsync()
    {
        if (Interlocked.Exchange(ref _disposed, 1) != 0) return;
        if (_window.Dispatcher.CheckAccess())
        {
            await DisposeCoreAsync();
        }
        else
        {
            await _window.Dispatcher.InvokeAsync(DisposeCoreAsync).Task.Unwrap();
        }
        GC.SuppressFinalize(this);
    }

    private async Task DisposeCoreAsync()
    {
        if (_current is not null) await _current.DisposeAsync();
        foreach (var resource in _warmWebResources.Values.Distinct()) await resource.DisposeAsync();
        _warmWebResources.Clear();
    }

    private async Task<WorkerExecutionResult> ExecuteCoreAsync(
        CommandLeaseDto lease,
        CancellationToken cancellationToken)
    {
        ObjectDisposedException.ThrowIf(Volatile.Read(ref _disposed) != 0, this);
        var command = lease.Command.Trim().ToUpperInvariant();
        switch (command)
        {
            case "OPEN": await OpenAsync(lease, cancellationToken); break;
            case "CLOSE":
            case "RESET_PPT": await CloseAsync(lease, cancellationToken); break;
            case "PLAY": await CurrentControlAsync(lease, "play", cancellationToken); _state = "playing"; break;
            case "PAUSE": await CurrentControlAsync(lease, "pause", cancellationToken); _state = "paused"; break;
            case "STOP": await CurrentControlAsync(lease, "stop", cancellationToken); _state = "stopped"; break;
            case "SEEK": await SeekAsync(Long(lease.Args, "position_ms"), cancellationToken); break;
            case "NEXT": await NavigateAsync(lease, _currentSlide + 1, cancellationToken); break;
            case "PREV": await NavigateAsync(lease, Math.Max(1, _currentSlide - 1), cancellationToken); break;
            case "GOTO": await NavigateAsync(lease, Int(lease.Args, "target_index", 1), cancellationToken); break;
            case "SET_VOLUME": SetVolume(Int(lease.Args, "volume", 100)); break;
            case "SET_MUTE": SetMute(Bool(lease.Args, "muted", false)); break;
            case "SET_LOOP": SetLoop(Bool(lease.Args, "enabled", false)); break;
            case "SHOW_ID": ShowWindowId(); break;
            case "PPT_MEDIA": await ControlPptMediaAsync(lease, cancellationToken); break;
            default: throw new InvalidOperationException($"PlayerWorker 不支持命令 {lease.Command}。");
        }

        _generation = Math.Max(_generation, lease.SourceGeneration);
        return new WorkerExecutionResult("completed", "ok", Snapshot());
    }

    private async Task OpenAsync(CommandLeaseDto lease, CancellationToken cancellationToken)
    {
        var sourceId = Long(lease.Args, "source_id");
        var uri = String(lease.Args, "uri");
        var sourceType = String(lease.Args, "source_type", InferType(uri));
        if (_current?.Kind == "powerpoint" && _officePresentationIdentity != 0)
        {
            await ClosePowerPointAsync(lease, "switch-close", cancellationToken).ConfigureAwait(false);
        }
        SurfaceResource next;
        switch (sourceType)
        {
            case "image": next = await OpenImageAsync(uri, cancellationToken); break;
            case "web": next = await OpenWebAsync(sourceId, lease.SourceRevision, uri, cancellationToken); break;
            case "video":
            case "audio":
            case "custom_stream":
            case "rtsp":
            case "srt": next = await OpenVlcAsync(uri, Bool(lease.Args, "autoplay", true), cancellationToken); break;
            case "ppt" when Path.GetExtension(LocalPath(uri)).Equals(".pdf", StringComparison.OrdinalIgnoreCase):
                next = await OpenPdfAsync(uri, Int(lease.Args, "target_slide", 1), cancellationToken);
                break;
            case "ppt": next = await OpenPowerPointAsync(lease, uri, cancellationToken); break;
            default: throw new InvalidOperationException($"不支持媒体类型 {sourceType}。");
        }

        var previous = _current;
        _current = next;
        _sourceId = sourceId;
        _generation = lease.SourceGeneration;
        if (next.Native is PdfPlaybackAdapter pdf)
        {
            _currentSlide = pdf.CurrentPage;
            _totalSlides = pdf.PageCount;
        }
        _state = Bool(lease.Args, "autoplay", true) ? "playing" : "paused";
        _window.SetSurface(next.Surface);
        if (previous is not null && !ReferenceEquals(previous, next) && previous.Kind != "web")
            await previous.DisposeAsync();
    }

    private static async Task<SurfaceResource> OpenImageAsync(string uri, CancellationToken cancellationToken)
    {
        var adapter = new ImagePlaybackAdapter();
        var path = LocalPath(uri);
        await adapter.PrepareAsync(new(0, path, "image"), path, cancellationToken);
        await adapter.OpenAsync(cancellationToken);
        return new SurfaceResource("image", new System.Windows.Controls.Image
        {
            Source = adapter.Image,
            Stretch = Stretch.Uniform,
        }, adapter.DisposeAsync);
    }

    private async Task<SurfaceResource> OpenWebAsync(
        long sourceId,
        long sourceRevision,
        string uri,
        CancellationToken cancellationToken)
    {
        var key = $"{sourceId}:{sourceRevision}:{uri}";
        if (_warmWebResources.TryGetValue(key, out var existing))
        {
            if (existing.IsHealthy) return existing;
            _warmWebResources.Remove(key);
            await existing.DisposeAsync();
        }
        var control = new WebView2();
        var userData = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "SCP-cv",
            "WebView2",
            $"player-{_windowId}");
        Directory.CreateDirectory(userData);
        var environment = await CoreWebView2Environment.CreateAsync(userDataFolder: userData);
        await control.EnsureCoreWebView2Async(environment);
        control.CoreWebView2.Settings.AreDevToolsEnabled = false;
        control.CoreWebView2.Settings.AreDefaultContextMenusEnabled = false;
        control.CoreWebView2.PermissionRequested += (_, args) => args.State = CoreWebView2PermissionState.Deny;
        var navigated = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var healthy = true;
        void Completed(object? _, CoreWebView2NavigationCompletedEventArgs args)
        {
            if (args.IsSuccess) navigated.TrySetResult();
            else navigated.TrySetException(new InvalidOperationException($"WebView2 导航失败：{args.WebErrorStatus}"));
        }
        void Failed(object? _, CoreWebView2ProcessFailedEventArgs __) => healthy = false;
        control.NavigationCompleted += Completed;
        control.CoreWebView2.ProcessFailed += Failed;
        control.Source = new Uri(uri, UriKind.Absolute);
        await navigated.Task.WaitAsync(cancellationToken);
        control.NavigationCompleted -= Completed;
        var resource = new SurfaceResource("web", control, async () =>
        {
            control.NavigationCompleted -= Completed;
            control.CoreWebView2.ProcessFailed -= Failed;
            control.Dispose();
            await ValueTask.CompletedTask;
        }, health: () => healthy);
        _warmWebResources[key] = resource;
        return resource;
    }

    private static async Task<SurfaceResource> OpenPdfAsync(
        string uri,
        int initialPage,
        CancellationToken cancellationToken)
    {
        var adapter = new PdfPlaybackAdapter();
        await adapter.OpenAsync(LocalPath(uri), Math.Max(1, initialPage), cancellationToken);
        var image = new System.Windows.Controls.Image
        {
            Source = Bitmap(await adapter.RenderPageAsync(adapter.CurrentPage, cancellationToken)),
            Stretch = Stretch.Uniform,
        };
        return new SurfaceResource("pdf", image, adapter.DisposeAsync, adapter);
    }

    private static Task<SurfaceResource> OpenVlcAsync(
        string uri,
        bool autoplay,
        CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        Core.Initialize();
        var libVlc = new LibVLC();
        var player = new VlcMediaPlayer(libVlc);
        var localPath = LocalPath(uri);
        var media = File.Exists(localPath)
            ? new Media(libVlc, Path.GetFullPath(localPath), FromType.FromPath)
            : new Media(libVlc, uri, FromType.FromLocation);
        player.Media = media;
        var view = new VideoView { MediaPlayer = player };
        if (autoplay && !player.Play()) throw new InvalidOperationException("LibVLC 无法开始播放媒体。");
        return Task.FromResult(new SurfaceResource("vlc", view, () =>
        {
            player.Stop();
            view.MediaPlayer = null;
            media.Dispose();
            player.Dispose();
            libVlc.Dispose();
            return ValueTask.CompletedTask;
        }, player));
    }

    private async Task CurrentControlAsync(
        CommandLeaseDto lease,
        string action,
        CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        if (_current?.Kind == "powerpoint")
        {
            await SendOfficeAsync(lease, "playback", new Dictionary<string, JsonElement>
            {
                ["presentation_identity"] = JsonSerializer.SerializeToElement(_officePresentationIdentity),
                ["action"] = JsonSerializer.SerializeToElement(action),
            }, cancellationToken).ConfigureAwait(false);
            return;
        }
        if (_current?.Native is not VlcMediaPlayer player) return;
        switch (action)
        {
            case "play": _ = player.Play(); break;
            case "pause": player.Pause(); break;
            case "stop": player.Stop(); break;
        }
        await Task.CompletedTask;
    }

    private async Task SeekAsync(long positionMs, CancellationToken cancellationToken)
    {
        if (_current?.Native is VlcMediaPlayer player) player.Time = Math.Max(0, positionMs);
        else if (_current?.Native is PdfPlaybackAdapter pdf) await NavigateAsync(null, (int)positionMs, cancellationToken);
    }

    private async Task NavigateAsync(CommandLeaseDto? lease, int page, CancellationToken cancellationToken)
    {
        if (_current?.Kind == "powerpoint")
        {
            if (lease is null) throw new InvalidOperationException("PowerPoint 导航缺少命令租约。");
            var result = await SendOfficeAsync(lease, "navigate", new Dictionary<string, JsonElement>
            {
                ["presentation_identity"] = JsonSerializer.SerializeToElement(_officePresentationIdentity),
                ["action"] = JsonSerializer.SerializeToElement(lease.Command.Trim().ToLowerInvariant()),
                ["target_slide"] = JsonSerializer.SerializeToElement(page),
            }, cancellationToken).ConfigureAwait(false);
            _currentSlide = Int(result.Result, "current_slide", page);
            return;
        }
        if (_current?.Native is not PdfPlaybackAdapter pdf) return;
        page = Math.Clamp(page, 1, pdf.PageCount);
        var bytes = await pdf.RenderPageAsync(page, cancellationToken);
        ((System.Windows.Controls.Image)_current.Surface).Source = Bitmap(bytes);
        _currentSlide = page;
        _totalSlides = pdf.PageCount;
    }

    private void SetVolume(int volume)
    {
        if (_current?.Native is VlcMediaPlayer player) player.Volume = Math.Clamp(volume, 0, 100);
    }

    private void SetMute(bool muted)
    {
        if (_current?.Native is VlcMediaPlayer player) player.Mute = muted;
    }

    private void SetLoop(bool enabled)
    {
        if (_current?.Native is VlcMediaPlayer player)
            player.Media?.AddOption(enabled ? ":input-repeat=65535" : ":input-repeat=0");
    }

    private async Task CloseAsync(CommandLeaseDto lease, CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        if (_current?.Kind == "powerpoint" && _officePresentationIdentity != 0)
        {
            await ClosePowerPointAsync(lease, "close", cancellationToken).ConfigureAwait(false);
        }
        if (_current is not null && _current.Kind != "web") await _current.DisposeAsync();
        _current = null;
        _sourceId = 0;
        _state = "idle";
        _currentSlide = 0;
        _totalSlides = 0;
        _window.SetSurface(new Grid { Background = WpfBrushes.Black });
    }

    private void ShowWindowId()
    {
        _window.SetSurface(new TextBlock
        {
            Text = _windowId.ToString(System.Globalization.CultureInfo.InvariantCulture),
            Foreground = WpfBrushes.White,
            FontSize = 240,
            HorizontalAlignment = WpfHorizontalAlignment.Center,
            VerticalAlignment = VerticalAlignment.Center,
        });
    }

    private JsonElement Snapshot()
    {
        var position = _current?.Native is VlcMediaPlayer player ? Math.Max(0, player.Time) : 0;
        var duration = _current?.Native is VlcMediaPlayer mediaPlayer ? Math.Max(0, mediaPlayer.Length) : 0;
        return JsonSerializer.SerializeToElement(new
        {
            source_generation = _generation,
            source_id = _sourceId == 0 ? (long?)null : _sourceId,
            playback_state = _state,
            playback_mode = _current?.Kind switch { "pdf" => "pdf", "powerpoint" => "powerpoint", _ => "" },
            adapter_kind = _current?.Kind ?? string.Empty,
            current_slide = _currentSlide,
            total_slides = _totalSlides,
            position_ms = position,
            duration_ms = duration,
            error_message = string.Empty,
        });
    }

    private static BitmapImage Bitmap(byte[] bytes)
    {
        using var stream = new MemoryStream(bytes);
        var bitmap = new BitmapImage();
        bitmap.BeginInit();
        bitmap.CacheOption = BitmapCacheOption.OnLoad;
        bitmap.StreamSource = stream;
        bitmap.EndInit();
        bitmap.Freeze();
        return bitmap;
    }

    private static string InferType(string uri)
    {
        var extension = Path.GetExtension(LocalPath(uri)).ToLowerInvariant();
        return extension switch
        {
            ".png" or ".jpg" or ".jpeg" or ".bmp" or ".gif" => "image",
            ".pdf" or ".ppt" or ".pptx" => "ppt",
            _ when Uri.TryCreate(uri, UriKind.Absolute, out var parsed) && parsed.Scheme is "http" or "https" => "web",
            _ => "video",
        };
    }

    private static string LocalPath(string uri) =>
        uri.StartsWith("file://", StringComparison.OrdinalIgnoreCase) ? new Uri(uri).LocalPath : uri;

    private static string String(Dictionary<string, JsonElement> args, string key, string? fallback = null) =>
        args.TryGetValue(key, out var value) && value.ValueKind == JsonValueKind.String
            ? value.GetString() ?? fallback ?? string.Empty
            : fallback ?? throw new InvalidDataException($"缺少字符串参数 {key}。");

    private static long Long(Dictionary<string, JsonElement> args, string key, long fallback = 0) =>
        args.TryGetValue(key, out var value) && value.TryGetInt64(out var parsed) ? parsed : fallback;

    private static int Int(Dictionary<string, JsonElement> args, string key, int fallback) =>
        args.TryGetValue(key, out var value) && value.TryGetInt32(out var parsed) ? parsed : fallback;

    private static bool Bool(Dictionary<string, JsonElement> args, string key, bool fallback) =>
        args.TryGetValue(key, out var value) && value.ValueKind is JsonValueKind.True or JsonValueKind.False
            ? value.GetBoolean()
            : fallback;

    private sealed class SurfaceResource(
        string kind,
        FrameworkElement surface,
        Func<ValueTask> dispose,
        object? native = null,
        Func<bool>? health = null) : IAsyncDisposable
    {
        public string Kind { get; } = kind;
        public FrameworkElement Surface { get; } = surface;
        public object? Native { get; } = native;
        public bool IsHealthy => health?.Invoke() ?? true;
        public ValueTask DisposeAsync() => dispose();
    }
}
