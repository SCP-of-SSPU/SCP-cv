using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.Extensions.DependencyInjection;
using ScpCv.ControlHost.Events;
using ScpCv.Infrastructure.Audio;
using ScpCv.Infrastructure.Playback;

namespace ScpCv.ControlHost.Tests;

public sealed class SseEventStreamTests
{
    private const string InitialPassword = "Old-password-123";

    [Fact]
    public async Task SubscriptionStartsWithFullSnapshotAndCoalescesToLatestUpdate()
    {
        using var factory = new ControlHostApplicationFactory();
        using var client = factory.CreateHttpsClient();
        var stream = factory.Services.GetRequiredService<SseEventHub>();
        var runtime = factory.Services.GetRequiredService<RuntimeStateService>();
        using var cancellation = new CancellationTokenSource(TimeSpan.FromSeconds(5));
        await using var events = stream.ReadAsync(lastEventId: 99, cancellation.Token).GetAsyncEnumerator();

        Assert.True(await events.MoveNextAsync());
        Assert.Equal("playback_state", events.Current.EventName);
        using (var initial = JsonDocument.Parse(events.Current.Data))
        {
            Assert.Equal(4, initial.RootElement.GetProperty("sessions").GetArrayLength());
            Assert.Equal(JsonValueKind.Object, initial.RootElement.GetProperty("background_audio").ValueKind);
        }

        await runtime.SetSystemVolumeAsync(31, muted: false, cancellation.Token);
        stream.PublishLatest();
        await runtime.SetSystemVolumeAsync(32, muted: false, cancellation.Token);
        var latestRevision = stream.PublishLatest();

        Assert.True(await events.MoveNextAsync());
        Assert.Equal(latestRevision, events.Current.Id);

        await events.DisposeAsync();
        Assert.Equal(0, stream.SubscriberCount);
    }

    [Fact]
    public async Task ReconnectAlwaysReceivesFreshSnapshotInsteadOfHistoricalReplay()
    {
        using var factory = new ControlHostApplicationFactory();
        var stream = factory.Services.GetRequiredService<SseEventHub>();
        var runtime = factory.Services.GetRequiredService<RuntimeStateService>();
        var oldRevision = stream.PublishLatest();
        await runtime.SetRuntimeModeAsync("double");
        var currentRevision = stream.PublishLatest();
        using var cancellation = new CancellationTokenSource(TimeSpan.FromSeconds(5));
        await using var events = stream.ReadAsync(oldRevision, cancellation.Token).GetAsyncEnumerator();

        Assert.True(await events.MoveNextAsync());
        Assert.Equal(currentRevision, events.Current.Id);
        using var snapshot = JsonDocument.Parse(events.Current.Data);
        var thirdWindow = snapshot.RootElement.GetProperty("sessions").EnumerateArray()
            .Single(session => session.GetProperty("window_id").GetInt32() == 3);
        Assert.True(thirdWindow.GetProperty("is_muted").GetBoolean());
    }

    [Fact]
    public async Task IdleSubscriptionEmitsHeartbeat()
    {
        using var factory = new ControlHostApplicationFactory();
        var stream = new SseEventHub(
            factory.Services.GetRequiredService<RuntimeStateService>(),
            factory.Services.GetRequiredService<BackgroundAudioService>(),
            new SseEventStreamOptions { HeartbeatInterval = TimeSpan.FromMilliseconds(10) });
        using var cancellation = new CancellationTokenSource(TimeSpan.FromSeconds(2));
        await using var events = stream.ReadAsync(0, cancellation.Token).GetAsyncEnumerator();

        Assert.True(await events.MoveNextAsync());
        Assert.False(events.Current.IsHeartbeat);
        Assert.True(await events.MoveNextAsync());
        Assert.True(events.Current.IsHeartbeat);
    }

    [Fact]
    public async Task EndpointRequiresSessionAndUsesSseHeadersAndInitialEvent()
    {
        using var factory = new ControlHostApplicationFactory();
        using var client = factory.CreateHttpsClient();

        using (var anonymous = await client.GetAsync("/api/events/"))
        {
            Assert.Equal(HttpStatusCode.Unauthorized, anonymous.StatusCode);
        }

        await AuthenticateAsync(client);
        using var cancellation = new CancellationTokenSource(TimeSpan.FromSeconds(5));
        using var request = new HttpRequestMessage(HttpMethod.Get, "/api/events/?last_id=123");
        using var response = await client.SendAsync(
            request,
            HttpCompletionOption.ResponseHeadersRead,
            cancellation.Token);
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("text/event-stream", response.Content.Headers.ContentType?.MediaType);
        Assert.Equal("no-cache", response.Headers.CacheControl?.ToString());
        Assert.Equal("no", response.Headers.GetValues("X-Accel-Buffering").Single());
        using var reader = new StreamReader(await response.Content.ReadAsStreamAsync(cancellation.Token));
        Assert.StartsWith("id: ", await reader.ReadLineAsync(cancellation.Token), StringComparison.Ordinal);
        Assert.Equal("event: playback_state", await reader.ReadLineAsync(cancellation.Token));
        Assert.StartsWith("data: {", await reader.ReadLineAsync(cancellation.Token), StringComparison.Ordinal);
    }

    private static async Task AuthenticateAsync(HttpClient client)
    {
        using var response = await client.PostAsJsonAsync(
            "/api/auth/login/",
            new { username = "operator", password = InitialPassword });
        response.EnsureSuccessStatusCode();
    }
}
