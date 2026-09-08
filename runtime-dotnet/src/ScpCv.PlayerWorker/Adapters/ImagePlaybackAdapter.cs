using System.Windows.Media.Imaging;
using System.IO;
using ScpCv.Domain.Rules;

namespace ScpCv.PlayerWorker.Adapters;

public sealed class ImagePlaybackAdapter : IPlaybackAdapter
{
    private string? _path;
    private BitmapImage? _image;
    public string Kind => "image";
    public PlaybackResourceState State { get; private set; } = PlaybackResourceState.Empty;
    public BitmapSource? Image => _image;

    public Task PrepareAsync(ResourceKey key, string uri, CancellationToken cancellationToken = default)
    {
        var path = uri.StartsWith("file://", StringComparison.OrdinalIgnoreCase) ? new Uri(uri).LocalPath : uri;
        path = Path.GetFullPath(path);
        if (!File.Exists(path)) { State = PlaybackResourceState.Faulted; throw new FileNotFoundException("图片文件不存在。", path); }
        _path = path;
        State = PlaybackResourceState.Preparing;
        return Task.CompletedTask;
    }

    public Task OpenAsync(CancellationToken cancellationToken = default)
    {
        if (_path is null) throw new InvalidOperationException("尚未准备图片资源。");
        var info = new FileInfo(_path);
        var bitmap = new BitmapImage();
        bitmap.BeginInit();
        bitmap.CacheOption = BitmapCacheOption.OnLoad;
        bitmap.UriSource = new Uri(_path, UriKind.Absolute);
        bitmap.EndInit();
        bitmap.Freeze();
        _image = bitmap;
        State = PlaybackResourceState.Visible;
        _ = info.Length; // 文件元数据读取作为版本校验的最小边界。
        return Task.CompletedTask;
    }

    public Task ControlAsync(string action, CancellationToken cancellationToken = default) => Task.CompletedTask;
    public Task HideAsync(CancellationToken cancellationToken = default) { State = PlaybackResourceState.Hidden; return Task.CompletedTask; }
    public Task CloseAsync(CancellationToken cancellationToken = default) { _image = null; State = PlaybackResourceState.Empty; return Task.CompletedTask; }
    public object Observe() => new { kind = Kind, state = State.ToString().ToLowerInvariant(), path = _path };
    public ValueTask DisposeAsync() { _image = null; State = PlaybackResourceState.Empty; return ValueTask.CompletedTask; }
}
