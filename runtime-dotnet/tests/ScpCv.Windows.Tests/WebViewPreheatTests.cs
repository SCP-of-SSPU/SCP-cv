using ScpCv.Domain.Rules;
using ScpCv.PlayerWorker.Adapters;

namespace ScpCv.Windows.Tests;

public sealed class WebViewPreheatTests
{
    [Fact]
    public async Task HealthyResourceIsReusedWithoutSecondNavigation()
    {
        var factoryCalls = 0;
        var pool = new WebViewPlaybackAdapter(key =>
        {
            Interlocked.Increment(ref factoryCalls);
            return Task.FromResult<IWebViewSession>(new FakeWebViewSession());
        });
        var key = new ResourceKey(1, "a", "web");
        await pool.PrepareAsync(key, "https://example.test", true);
        await pool.PrepareAsync(key, "https://example.test", true);

        Assert.Equal(1, factoryCalls);
        Assert.Equal(1, pool.NavigationCount);
        await pool.DisposeAsync();
    }

    [Fact]
    public async Task RendererFailureMakesResourceUnavailableAndBudgetRejects()
    {
        var sessions = new List<FakeWebViewSession>();
        var pool = new WebViewPlaybackAdapter(_ =>
        {
            var item = new FakeWebViewSession();
            sessions.Add(item);
            return Task.FromResult<IWebViewSession>(item);
        }, maxPreheated: 1);
        var first = await pool.PrepareAsync(new ResourceKey(1, "a", "web"), "https://a.test", true);
        Assert.NotNull(first);
        sessions[0].MarkProcessFailed();
        Assert.False(pool.IsHealthy(new ResourceKey(1, "a", "web")));
        Assert.Null(await pool.PrepareAsync(new ResourceKey(2, "b", "web"), "https://b.test", true));
        await pool.DisposeAsync();
    }

    private sealed class FakeWebViewSession : IWebViewSession
    {
        public int NavigationCount { get; private set; }
        public bool IsHealthy { get; private set; } = true;
        public Task NavigateAsync(string uri, CancellationToken cancellationToken) { NavigationCount++; return Task.CompletedTask; }
        public void MarkProcessFailed() => IsHealthy = false;
        public ValueTask DisposeAsync() { IsHealthy = false; return ValueTask.CompletedTask; }
    }
}
