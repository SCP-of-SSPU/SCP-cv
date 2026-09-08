using System.Net.Http.Headers;
using Microsoft.EntityFrameworkCore;
using ScpCv.Domain.Model;
using ScpCv.Infrastructure.Persistence;

namespace ScpCv.Infrastructure.Streams;

public sealed record StreamProbeResult(long StreamId, bool Online, DateTimeOffset CheckedAt, string Error);

/// <summary>MediaMTX/HTTP 流发现与周期探测；不持有跨进程播放器对象。</summary>
public sealed class StreamDiscoveryService(
    IDbContextFactory<ControlDbContext> contextFactory,
    IHttpClientFactory httpClientFactory,
    TimeProvider? timeProvider = null)
{
    private readonly TimeProvider _timeProvider = timeProvider ?? TimeProvider.System;

    public async Task<IReadOnlyList<StreamProbeResult>> ProbeActiveAsync(CancellationToken cancellationToken = default)
    {
        await using var database = await contextFactory.CreateDbContextAsync(cancellationToken).ConfigureAwait(false);
        var streams = await database.StreamSources.Where(stream => stream.IsActive).ToListAsync(cancellationToken).ConfigureAwait(false);
        var results = new List<StreamProbeResult>(streams.Count);
        foreach (var stream in streams)
        {
            var result = await ProbeAsync(stream, cancellationToken).ConfigureAwait(false);
            stream.IsOnline = result.Online;
            stream.LastSeenAt = result.Online ? result.CheckedAt : stream.LastSeenAt;
            stream.State = result.Online ? "online" : "offline";
            stream.ErrorMessage = result.Error;
            results.Add(result);
        }

        await database.SaveChangesAsync(cancellationToken).ConfigureAwait(false);
        return results;
    }

    private async Task<StreamProbeResult> ProbeAsync(StreamSource stream, CancellationToken cancellationToken)
    {
        var now = _timeProvider.GetUtcNow();
        if (!Uri.TryCreate(stream.Url, UriKind.Absolute, out var uri)) return new(stream.Id, false, now, "invalid_url");
        try
        {
            using var request = new HttpRequestMessage(HttpMethod.Head, uri);
            using var response = await httpClientFactory.CreateClient("stream-probe").SendAsync(request, HttpCompletionOption.ResponseHeadersRead, cancellationToken).ConfigureAwait(false);
            return new(stream.Id, response.IsSuccessStatusCode, now, response.IsSuccessStatusCode ? string.Empty : $"http_{(int)response.StatusCode}");
        }
        catch (Exception exception) when (exception is HttpRequestException or TaskCanceledException)
        {
            return new(stream.Id, false, now, exception.GetType().Name);
        }
    }
}
