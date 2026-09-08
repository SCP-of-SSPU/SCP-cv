using System.Collections.Concurrent;
using System.IO;
using Windows.Data.Pdf;
using Windows.Storage;
using Windows.Storage.Streams;

namespace ScpCv.PlayerWorker.Adapters;

/// <summary>Windows.Data.Pdf 后端；对外页码始终从 1 开始，并只缓存当前页及相邻页。</summary>
public sealed class PdfPlaybackAdapter : IAsyncDisposable
{
    private readonly SemaphoreSlim _gate = new(1, 1);
    private readonly ConcurrentDictionary<int, byte[]> _renderedPages = new();
    private PdfDocument? _document;
    private int _disposed;

    public int PageCount => checked((int)(_document?.PageCount ?? 0));
    public int CurrentPage { get; private set; }

    public async Task OpenAsync(string path, int initialPage = 1, CancellationToken cancellationToken = default)
    {
        ObjectDisposedException.ThrowIf(Volatile.Read(ref _disposed) != 0, this);
        if (!OperatingSystem.IsWindows()) throw new PlatformNotSupportedException("PDF 放映只支持 Windows 播放端。");
        var fullPath = Path.GetFullPath(path);
        if (!File.Exists(fullPath)) throw new FileNotFoundException("PDF 文件不存在。", fullPath);

        await _gate.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            var file = await StorageFile.GetFileFromPathAsync(fullPath).AsTask(cancellationToken).ConfigureAwait(false);
            _document = await PdfDocument.LoadFromFileAsync(file).AsTask(cancellationToken).ConfigureAwait(false);
            _renderedPages.Clear();
            ValidatePage(initialPage);
            CurrentPage = initialPage;
        }
        finally
        {
            _gate.Release();
        }

        await RenderPageAsync(initialPage, cancellationToken).ConfigureAwait(false);
    }

    public async Task<byte[]> RenderPageAsync(int pageNumber, CancellationToken cancellationToken = default)
    {
        ObjectDisposedException.ThrowIf(Volatile.Read(ref _disposed) != 0, this);
        if (_renderedPages.TryGetValue(pageNumber, out var cached)) return cached;

        await _gate.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            ValidatePage(pageNumber);
            var bytes = await RenderCoreAsync(pageNumber, cancellationToken).ConfigureAwait(false);
            _renderedPages[pageNumber] = bytes;
            CurrentPage = pageNumber;

            foreach (var neighbor in new[] { pageNumber - 1, pageNumber + 1 }.Where(page => page >= 1 && page <= PageCount))
            {
                if (!_renderedPages.ContainsKey(neighbor))
                {
                    _renderedPages[neighbor] = await RenderCoreAsync(neighbor, cancellationToken).ConfigureAwait(false);
                }
            }

            foreach (var stale in _renderedPages.Keys.Where(page => Math.Abs(page - pageNumber) > 1))
            {
                _renderedPages.TryRemove(stale, out _);
            }

            return bytes;
        }
        finally
        {
            _gate.Release();
        }
    }

    public ValueTask DisposeAsync()
    {
        if (Interlocked.Exchange(ref _disposed, 1) == 0)
        {
            _document = null;
            _renderedPages.Clear();
            _gate.Dispose();
        }

        GC.SuppressFinalize(this);
        return ValueTask.CompletedTask;
    }

    private async Task<byte[]> RenderCoreAsync(int pageNumber, CancellationToken cancellationToken)
    {
        using var page = _document!.GetPage(checked((uint)(pageNumber - 1)));
        using var stream = new InMemoryRandomAccessStream();
        await page.RenderToStreamAsync(stream).AsTask(cancellationToken).ConfigureAwait(false);
        stream.Seek(0);
        using var reader = new DataReader(stream.GetInputStreamAt(0));
        var length = checked((uint)stream.Size);
        await reader.LoadAsync(length).AsTask(cancellationToken).ConfigureAwait(false);
        var bytes = new byte[checked((int)length)];
        reader.ReadBytes(bytes);
        return bytes;
    }

    private void ValidatePage(int pageNumber)
    {
        if (_document is null) throw new InvalidOperationException("尚未打开 PDF 文档。");
        if (pageNumber < 1 || pageNumber > PageCount)
            throw new ArgumentOutOfRangeException(nameof(pageNumber), $"页码必须位于 1 到 {PageCount} 之间。");
    }
}
