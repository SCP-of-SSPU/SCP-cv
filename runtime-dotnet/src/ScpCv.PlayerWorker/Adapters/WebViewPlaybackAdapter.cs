using ScpCv.Domain.Rules;

namespace ScpCv.PlayerWorker.Adapters;

public interface IWebViewSession : IAsyncDisposable
{
    int NavigationCount { get; }
    bool IsHealthy { get; }
    Task NavigateAsync(string uri, CancellationToken cancellationToken);
    void MarkProcessFailed();
}

/// <summary>每个 PlayerWorker 独立 UDF 的 WebView2 资源池；健康资源切换不重复导航。</summary>
public sealed class WebViewPlaybackAdapter(
    Func<ResourceKey, Task<IWebViewSession>> sessionFactory,
    int maxPreheated = 4)
{
    private readonly Dictionary<ResourceKey, IWebViewSession> _sessions = [];
    private readonly object _gate = new();

    public int NavigationCount
    {
        get { lock (_gate) return _sessions.Values.Sum(session => session.NavigationCount); }
    }

    public async Task<IWebViewSession?> PrepareAsync(
        ResourceKey key,
        string uri,
        bool keepAlive,
        CancellationToken cancellationToken = default)
    {
        IWebViewSession? existing;
        lock (_gate) _sessions.TryGetValue(key, out existing);
        if (existing is { IsHealthy: true }) return existing;
        if (!keepAlive && _sessions.Count >= 1) return null;
        if (_sessions.Count >= maxPreheated) return null;

        var created = await sessionFactory(key).ConfigureAwait(false);
        await created.NavigateAsync(uri, cancellationToken).ConfigureAwait(false);
        lock (_gate) _sessions[key] = created;
        return created;
    }

    public bool Hide(ResourceKey key) => IsHealthy(key);
    public bool IsHealthy(ResourceKey key)
    {
        lock (_gate) return _sessions.TryGetValue(key, out var session) && session.IsHealthy;
    }

    public async ValueTask DisposeAsync()
    {
        IWebViewSession[] sessions;
        lock (_gate) { sessions = _sessions.Values.ToArray(); _sessions.Clear(); }
        foreach (var session in sessions) await session.DisposeAsync().ConfigureAwait(false);
    }
}
