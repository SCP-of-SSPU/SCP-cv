using System.Collections.Concurrent;
using System.Runtime.CompilerServices;
using System.Text.Json;
using System.Threading.Channels;
using ScpCv.ControlHost.Endpoints;
using ScpCv.Infrastructure.Audio;
using ScpCv.Infrastructure.Playback;

namespace ScpCv.ControlHost.Events;

public sealed class SseEventStreamOptions
{
    public TimeSpan HeartbeatInterval { get; set; } = TimeSpan.FromSeconds(30);
}

public readonly record struct SseFrame(long Id, string EventName, string Data, bool IsHeartbeat)
{
    public static SseFrame Heartbeat() => new(0, string.Empty, string.Empty, IsHeartbeat: true);
}

public sealed class SseEventHub(
    RuntimeStateService runtime,
    BackgroundAudioService audio,
    SseEventStreamOptions options)
{
    private readonly ConcurrentDictionary<Guid, Channel<long>> _subscribers = new();
    private long _revision;

    public int SubscriberCount => _subscribers.Count;

    public long PublishLatest()
    {
        var revision = Interlocked.Increment(ref _revision);
        foreach (var subscriber in _subscribers.Values)
        {
            subscriber.Writer.TryWrite(revision);
        }
        return revision;
    }

    public async IAsyncEnumerable<SseFrame> ReadAsync(
        long lastEventId,
        [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        _ = lastEventId;
        var subscriberId = Guid.NewGuid();
        var channel = Channel.CreateBounded<long>(new BoundedChannelOptions(1)
        {
            SingleReader = true,
            SingleWriter = false,
            FullMode = BoundedChannelFullMode.DropOldest,
        });
        if (!_subscribers.TryAdd(subscriberId, channel))
        {
            throw new InvalidOperationException("无法登记 SSE 订阅者。");
        }

        using var heartbeat = new PeriodicTimer(options.HeartbeatInterval);
        try
        {
            var lastSentRevision = Volatile.Read(ref _revision);
            yield return await CreateSnapshotAsync(lastSentRevision, cancellationToken).ConfigureAwait(false);
            var updateTask = channel.Reader.ReadAsync(cancellationToken).AsTask();
            var heartbeatTask = heartbeat.WaitForNextTickAsync(cancellationToken).AsTask();
            while (!cancellationToken.IsCancellationRequested)
            {
                var completed = await Task.WhenAny(updateTask, heartbeatTask).ConfigureAwait(false);
                if (completed == updateTask)
                {
                    var latestRevision = await updateTask.ConfigureAwait(false);
                    while (channel.Reader.TryRead(out var queuedRevision))
                    {
                        latestRevision = Math.Max(latestRevision, queuedRevision);
                    }
                    updateTask = channel.Reader.ReadAsync(cancellationToken).AsTask();
                    if (latestRevision <= lastSentRevision)
                    {
                        continue;
                    }

                    lastSentRevision = latestRevision;
                    yield return await CreateSnapshotAsync(latestRevision, cancellationToken).ConfigureAwait(false);
                    continue;
                }

                if (!await heartbeatTask.ConfigureAwait(false))
                {
                    yield break;
                }
                heartbeatTask = heartbeat.WaitForNextTickAsync(cancellationToken).AsTask();
                yield return SseFrame.Heartbeat();
            }
        }
        finally
        {
            if (_subscribers.TryRemove(subscriberId, out var removed))
            {
                removed.Writer.TryComplete();
            }
        }
    }

    private async Task<SseFrame> CreateSnapshotAsync(long revision, CancellationToken cancellationToken)
    {
        var sessions = await runtime.GetSessionsAsync(cancellationToken).ConfigureAwait(false);
        var backgroundAudio = await audio.GetAsync(cancellationToken).ConfigureAwait(false);
        var json = JsonSerializer.Serialize(new
        {
            sessions,
            background_audio = backgroundAudio,
        });
        return new SseFrame(revision, "playback_state", json, IsHeartbeat: false);
    }
}

public static class SseEventEndpoints
{
    public static IEndpointRouteBuilder MapSseEventEndpoints(this IEndpointRouteBuilder endpoints)
    {
        endpoints.MapGroup("/api").RequireSessionAndCsrf().MapGet("/events/", StreamAsync);
        return endpoints;
    }

    private static async Task StreamAsync(HttpContext context, SseEventHub stream)
    {
        context.Response.StatusCode = StatusCodes.Status200OK;
        context.Response.ContentType = "text/event-stream";
        context.Response.Headers.CacheControl = "no-cache";
        context.Response.Headers["X-Accel-Buffering"] = "no";
        var lastEventId = ReadLastEventId(context.Request);
        try
        {
            await foreach (var frame in stream.ReadAsync(lastEventId, context.RequestAborted).ConfigureAwait(false))
            {
                var text = frame.IsHeartbeat
                    ? ": heartbeat\n\n"
                    : $"id: {frame.Id}\nevent: {frame.EventName}\ndata: {frame.Data}\n\n";
                await context.Response.WriteAsync(text, context.RequestAborted).ConfigureAwait(false);
                await context.Response.Body.FlushAsync(context.RequestAborted).ConfigureAwait(false);
            }
        }
        catch (OperationCanceledException) when (context.RequestAborted.IsCancellationRequested)
        {
            // 客户端断开即结束流，不把正常取消记录为服务器错误。
        }
    }

    private static long ReadLastEventId(HttpRequest request)
    {
        var raw = request.Query["last_id"].FirstOrDefault();
        if (string.IsNullOrWhiteSpace(raw))
        {
            raw = request.Headers["Last-Event-ID"].FirstOrDefault();
        }
        return long.TryParse(raw, out var parsed) && parsed >= 0 ? parsed : 0;
    }
}
