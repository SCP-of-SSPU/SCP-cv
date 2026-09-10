using System.Collections.Concurrent;
using System.Diagnostics;
using System.IO;
using ScpCv.PowerPointHost.Sta;

namespace ScpCv.PowerPointHost.Interop;

public sealed record PowerPointOpenResult(
    bool Succeeded,
    string Code,
    long PresentationIdentity,
    nint SlideShowWindowHandle,
    int SlideCount,
    int ProcessId = 0,
    DateTimeOffset ProcessStart = default);

public sealed record PowerPointNavigationResult(bool Succeeded, int CurrentSlide);

/// <summary>所有 COM 对象只在 OfficeStaDispatcher 所在线程创建、访问和释放。</summary>
public sealed class PowerPointComAdapter(OfficeStaDispatcher sta) : IDisposable
{
    private readonly ConcurrentDictionary<long, (dynamic Presentation, string Path)> _presentations = new();
    private dynamic? _application;
    private bool _createdApplication;
    private long _nextIdentity;
    private int _disposed;

    public static bool IsAvailable =>
        OperatingSystem.IsWindows() && Type.GetTypeFromProgID("PowerPoint.Application") is not null;

    public Task<PowerPointOpenResult> OpenAsync(Guid operationId, string path, CancellationToken cancellationToken = default) =>
        sta.InvokeAsync(operationId, _ => OpenCore(path), cancellationToken);

    public Task<PowerPointNavigationResult> NavigateAsync(
        Guid operationId,
        long identity,
        string action,
        int slide,
        CancellationToken cancellationToken = default) =>
        sta.InvokeAsync(operationId, _ =>
        {
            if (!_presentations.TryGetValue(identity, out var item)) return new PowerPointNavigationResult(false, 0);
            var count = (int)item.Presentation.Slides.Count;
            dynamic view = item.Presentation.SlideShowWindow.View;
            switch (action.Trim().ToLowerInvariant())
            {
                case "next":
                    try { view.GotoNextClick(); } catch { if ((int)view.CurrentShowPosition < count) view.Next(); }
                    break;
                case "prev":
                    try { view.GotoPreClick(); } catch { if ((int)view.CurrentShowPosition > 1) view.Previous(); }
                    break;
                case "goto" when slide >= 1 && slide <= count:
                    view.GotoSlide(slide);
                    break;
                default:
                    return new PowerPointNavigationResult(false, (int)view.CurrentShowPosition);
            }
            return new PowerPointNavigationResult(true, (int)view.CurrentShowPosition);
        }, cancellationToken);

    public Task<bool> ControlPlaybackAsync(
        Guid operationId,
        long identity,
        string action,
        CancellationToken cancellationToken = default) =>
        sta.InvokeAsync(operationId, _ =>
        {
            if (!_presentations.TryGetValue(identity, out var item)) return false;
            try
            {
                dynamic view = item.Presentation.SlideShowWindow.View;
                switch (action.Trim().ToLowerInvariant())
                {
                    case "play": view.State = 1 /* ppSlideShowRunning */; break;
                    case "pause": view.State = 2 /* ppSlideShowPaused */; break;
                    case "stop": view.Exit(); break;
                    default: return false;
                }
                return true;
            }
            catch
            {
                return false;
            }
        }, cancellationToken);

    public Task<bool> ControlMediaAsync(
        Guid operationId,
        long identity,
        string action,
        string? mediaId = null,
        int? mediaIndex = null,
        CancellationToken cancellationToken = default) =>
        sta.InvokeAsync(operationId, _ =>
        {
            if (!_presentations.TryGetValue(identity, out var item)) return false;
            try
            {
                dynamic view = item.Presentation.SlideShowWindow.View;
                dynamic? player = ResolveMediaPlayer(item.Presentation, view, mediaId, mediaIndex);

                if (player is null) return false;
                switch (action.Trim().ToLowerInvariant())
                {
                    case "play": player.Play(); break;
                    case "pause": player.Pause(); break;
                    case "stop": player.Stop(); break;
                    case "toggle":
                        try { if ((int)player.State == 1) player.Pause(); else player.Play(); }
                        catch { player.Play(); }
                        break;
                    default: return false;
                }

                return true;
            }
            catch
            {
                return false;
            }
        }, cancellationToken);

    public Task<bool> CloseAsync(Guid operationId, long identity, CancellationToken cancellationToken = default) =>
        sta.InvokeAsync(operationId, _ => CloseCore(identity), cancellationToken);

    public Task<bool> ExportPdfAsync(Guid operationId, long identity, string outputPath, CancellationToken cancellationToken = default) =>
        sta.InvokeAsync(operationId, _ =>
        {
            if (!_presentations.TryGetValue(identity, out var item)) return false;
            item.Presentation.SaveAs(outputPath, 32 /* ppSaveAsPDF */);
            return File.Exists(outputPath);
        }, cancellationToken);

    public void Dispose()
    {
        if (Interlocked.Exchange(ref _disposed, 1) == 0)
        {
            try
            {
                sta.InvokeAsync(Guid.NewGuid(), _ =>
                {
                    foreach (var identity in _presentations.Keys.ToArray()) CloseCore(identity);
                    try
                    {
                        // 只有本 Host 创建且当前没有用户后来加入的文稿时才退出 Application。
                        if (_createdApplication && _application is not null && (int)_application.Presentations.Count == 0)
                            _application.Quit();
                    }
                    catch { }
                    if (_application is not null) MarshalFinalRelease(_application);
                    _application = null;
                    _createdApplication = false;
                    return true;
                }).GetAwaiter().GetResult();
            }
            catch { /* STA/COM 失控时由 OwnershipGuard 保留证据，不强杀用户 Office。 */ }
        }

        GC.SuppressFinalize(this);
    }

    private PowerPointOpenResult OpenCore(string path)
    {
        if (!File.Exists(path)) return new(false, "source_missing", 0, 0, 0);
        if (!_presentations.IsEmpty) return new(false, "office_slot_busy", 0, 0, 0);
        dynamic? openingPresentation = null;
        try
        {
            if (_application is null)
            {
                var applicationType = Type.GetTypeFromProgID("PowerPoint.Application")
                    ?? throw new InvalidOperationException("未安装 PowerPoint COM Automation 类型。");
                _application = Activator.CreateInstance(applicationType)
                    ?? throw new InvalidOperationException("无法创建 PowerPoint COM Application。");
                if ((int)_application.Presentations.Count != 0)
                {
                    // 无法证明当前 Application 是本系统独占的，不接管用户文稿。
                    MarshalFinalRelease(_application);
                    _application = null;
                    return new(false, "office_not_exclusive", 0, 0, 0);
                }
                _createdApplication = true;
            }
            _application.Visible = true;
            dynamic presentation = _application.Presentations.Open(path, WithWindow: -1);
            openingPresentation = presentation;
            var identity = Interlocked.Increment(ref _nextIdentity);
            presentation.SlideShowSettings.Run();
            dynamic window = presentation.SlideShowWindow;
            var handle = new nint((long)window.HWND);
            var slides = (int)presentation.Slides.Count;
            if (GetWindowThreadProcessId(handle, out var processId) == 0 || processId == 0)
            {
                presentation.Close();
                MarshalFinalRelease(presentation);
                return new(false, "office_process_unavailable", 0, 0, 0);
            }
            using var process = processId == 0 ? null : Process.GetProcessById((int)processId);
            var processStart = process is null
                ? default
                : new DateTimeOffset(process.StartTime.ToUniversalTime(), TimeSpan.Zero);
            _presentations[identity] = (presentation, path);
            openingPresentation = null;
            return new(true, "ok", identity, handle, slides, (int)processId, processStart);
        }
        catch (Exception exception)
        {
            if (openingPresentation is not null)
            {
                try { openingPresentation.Close(); } catch { }
                MarshalFinalRelease(openingPresentation);
            }
            return new(false, $"com_open_failed:{exception.GetType().Name}", 0, 0, 0);
        }
    }

    private bool CloseCore(long identity)
    {
        if (!_presentations.TryGetValue(identity, out var item)) return true;
        try
        {
            item.Presentation.Close();
            _presentations.TryRemove(identity, out _);
            MarshalFinalRelease(item.Presentation);
            return true;
        }
        catch { return false; }
    }

    private static void MarshalFinalRelease(object value)
    {
        try
        {
            if (System.Runtime.InteropServices.Marshal.IsComObject(value))
                System.Runtime.InteropServices.Marshal.FinalReleaseComObject(value);
        }
        catch { }
    }

    private static dynamic? ResolveMediaPlayer(
        dynamic presentation,
        dynamic view,
        string? mediaId,
        int? mediaIndex)
    {
        var candidates = new List<int>();
        if (int.TryParse(mediaId, out var parsed) && parsed > 0) candidates.Add(parsed);
        try
        {
            dynamic slide = presentation.Slides(view.CurrentShowPosition);
            for (var index = 1; index <= (int)slide.Shapes.Count; index++)
            {
                dynamic shape = slide.Shapes(index);
                try
                {
                    _ = shape.MediaFormat;
                    var shapeId = (int)shape.Id;
                    if (!candidates.Contains(shapeId)) candidates.Add(shapeId);
                }
                catch { }
            }
        }
        catch { }

        if (mediaIndex is > 0 && mediaIndex <= candidates.Count)
        {
            var preferred = candidates[mediaIndex.Value - 1];
            candidates.Remove(preferred);
            candidates.Insert(0, preferred);
        }
        foreach (var candidate in candidates)
        {
            try { return view.Player(candidate); } catch { }
        }
        return null;
    }

    [System.Runtime.InteropServices.DllImport("user32.dll")]
    private static extern uint GetWindowThreadProcessId(nint hWnd, out uint processId);
}
