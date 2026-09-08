using System.Buffers.Binary;
using System.Collections.Concurrent;
using System.IO.Pipes;
using System.Text.Json;
using ScpCv.Contracts.Ipc;

namespace ScpCv.Contracts.Runtime;

/// <summary>Worker 共用的单连接 Named Pipe 客户端；停止闩锁一旦设置便不因重连解除。</summary>
public sealed class RuntimePipeClient(string pipeName) : IAsyncDisposable
{
    private static readonly TimeSpan[] RetrySchedule =
    [
        TimeSpan.FromMilliseconds(250),
        TimeSpan.FromMilliseconds(500),
        TimeSpan.FromSeconds(1),
        TimeSpan.FromSeconds(2),
        TimeSpan.FromSeconds(5),
    ];

    private readonly SemaphoreSlim _exchangeGate = new(1, 1);
    private readonly ConcurrentDictionary<Guid, IpcFrameDto> _resultCache = new();
    private NamedPipeClientStream? _stream;
    private int _stopped;

    public bool IsStopped => Volatile.Read(ref _stopped) != 0;

    public async Task ConnectAsync(CancellationToken cancellationToken = default)
    {
        if (IsStopped)
        {
            throw new InvalidOperationException("运行组停止闩锁已设置，拒绝自动重连。");
        }

        Exception? lastError = null;
        for (var attempt = 0; !cancellationToken.IsCancellationRequested; attempt++)
        {
            var stream = new NamedPipeClientStream(
                ".",
                pipeName,
                PipeDirection.InOut,
                PipeOptions.Asynchronous | PipeOptions.CurrentUserOnly);
            try
            {
                await stream.ConnectAsync(1000, cancellationToken).ConfigureAwait(false);
                _stream = stream;
                return;
            }
            catch (Exception exception) when (exception is IOException or TimeoutException)
            {
                lastError = exception;
                await stream.DisposeAsync().ConfigureAwait(false);
                var baseDelay = RetrySchedule[Math.Min(attempt, RetrySchedule.Length - 1)];
                var jitter = TimeSpan.FromMilliseconds(Random.Shared.Next(0, 101));
                await Task.Delay(baseDelay + jitter, cancellationToken).ConfigureAwait(false);
            }
        }

        throw new OperationCanceledException("连接 ControlHost Named Pipe 已取消。", lastError, cancellationToken);
    }

    public async Task<IpcFrameDto> ExchangeAsync(
        IpcFrameDto request,
        CancellationToken cancellationToken = default)
    {
        if (IsStopped)
        {
            throw new InvalidOperationException("运行组停止闩锁已设置。");
        }

        await _exchangeGate.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            var stream = _stream is { IsConnected: true }
                ? _stream
                : throw new IOException("Named Pipe 尚未连接。");
            var bytes = JsonSerializer.SerializeToUtf8Bytes(request);
            await WriteFrameAsync(stream, bytes, cancellationToken).ConfigureAwait(false);
            var response = await ReadFrameAsync(stream, cancellationToken).ConfigureAwait(false);
            return JsonSerializer.Deserialize<IpcFrameDto>(response)
                ?? throw new InvalidDataException("ControlHost 返回了空 IPC 帧。");
        }
        finally
        {
            _exchangeGate.Release();
        }
    }

    public void CacheCriticalResult(Guid commandId, IpcFrameDto result) =>
        _resultCache[commandId] = result;

    public bool TryGetCachedResult(Guid commandId, out IpcFrameDto? result) =>
        _resultCache.TryGetValue(commandId, out result);

    public bool AcknowledgeResult(Guid commandId) => _resultCache.TryRemove(commandId, out _);

    public async ValueTask LatchStopAsync()
    {
        Interlocked.Exchange(ref _stopped, 1);
        var stream = Interlocked.Exchange(ref _stream, null);
        if (stream is not null)
        {
            await stream.DisposeAsync().ConfigureAwait(false);
        }
    }

    public async ValueTask DisposeAsync()
    {
        await LatchStopAsync().ConfigureAwait(false);
        _exchangeGate.Dispose();
        GC.SuppressFinalize(this);
    }

    private static async Task WriteFrameAsync(Stream stream, byte[] payload, CancellationToken cancellationToken)
    {
        if (payload.Length is 0 or > IpcProtocol.MaximumFrameBytes)
        {
            throw new InvalidDataException("IPC payload 长度无效。");
        }

        var prefix = new byte[sizeof(uint)];
        BinaryPrimitives.WriteUInt32LittleEndian(prefix, (uint)payload.Length);
        await stream.WriteAsync(prefix, cancellationToken).ConfigureAwait(false);
        await stream.WriteAsync(payload, cancellationToken).ConfigureAwait(false);
        await stream.FlushAsync(cancellationToken).ConfigureAwait(false);
    }

    private static async Task<byte[]> ReadFrameAsync(Stream stream, CancellationToken cancellationToken)
    {
        var prefix = new byte[sizeof(uint)];
        await stream.ReadExactlyAsync(prefix, cancellationToken).ConfigureAwait(false);
        var length = BinaryPrimitives.ReadUInt32LittleEndian(prefix);
        if (length is 0 or > IpcProtocol.MaximumFrameBytes)
        {
            throw new InvalidDataException("IPC response 长度无效。");
        }

        var payload = new byte[length];
        await stream.ReadExactlyAsync(payload, cancellationToken).ConfigureAwait(false);
        return payload;
    }
}
