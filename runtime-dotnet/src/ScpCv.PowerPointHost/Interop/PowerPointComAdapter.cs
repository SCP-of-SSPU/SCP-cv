using System.Collections.Concurrent;
using System.IO;
using ScpCv.PowerPointHost.Sta;

namespace ScpCv.PowerPointHost.Interop;

public sealed record PowerPointOpenResult(
    bool Succeeded,
    string Code,
    long PresentationIdentity,
    nint SlideShowWindowHandle,
    int SlideCount);

/// <summary>所有 COM 对象只在 OfficeStaDispatcher 所在线程创建、访问和释放。</summary>
public sealed class PowerPointComAdapter(OfficeStaDispatcher sta) : IDisposable
{
    private readonly ConcurrentDictionary<long, (dynamic Presentation, string Path)> _presentations = new();
    private dynamic? _application;
    private long _nextIdentity;
    private int _disposed;

    public Task<PowerPointOpenResult> OpenAsync(Guid operationId, string path, CancellationToken cancellationToken = default) =>
        sta.InvokeAsync(operationId, _ => OpenCore(path), cancellationToken);

    public Task<bool> NavigateAsync(Guid operationId, long identity, int slide, CancellationToken cancellationToken = default) =>
        sta.InvokeAsync(operationId, _ =>
        {
            if (!_presentations.TryGetValue(identity, out var item)) return false;
            var count = (int)item.Presentation.Slides.Count;
            if (slide < 1 || slide > count) return false;
            item.Presentation.SlideShowWindow.View.GotoSlide(slide);
            return true;
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
                    try { _application?.Quit(); } catch { }
                    _application = null;
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
        try
        {
            if (_application is null)
            {
                var applicationType = Type.GetTypeFromProgID("PowerPoint.Application")
                    ?? throw new InvalidOperationException("未安装 PowerPoint COM Automation 类型。");
                _application = Activator.CreateInstance(applicationType)
                    ?? throw new InvalidOperationException("无法创建 PowerPoint COM Application。");
            }
            _application.Visible = true;
            dynamic presentation = _application.Presentations.Open(path, WithWindow: -1);
            var identity = Interlocked.Increment(ref _nextIdentity);
            presentation.SlideShowSettings.Run();
            dynamic window = presentation.SlideShowWindow;
            var handle = new nint((long)window.HWND);
            var slides = (int)presentation.Slides.Count;
            _presentations[identity] = (presentation, path);
            return new(true, "ok", identity, handle, slides);
        }
        catch (Exception exception)
        {
            return new(false, $"com_open_failed:{exception.GetType().Name}", 0, 0, 0);
        }
    }

    private bool CloseCore(long identity)
    {
        if (!_presentations.TryRemove(identity, out var item)) return true;
        try
        {
            item.Presentation.Close();
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
}
