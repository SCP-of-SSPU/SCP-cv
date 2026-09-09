using System.Buffers.Binary;
using System.Collections.Concurrent;
using System.IO.Pipes;
using System.Runtime.CompilerServices;
using System.Text.Json;
using System.Threading.Channels;
using ScpCv.Contracts.Ipc;

namespace ScpCv.Contracts.Runtime;

/// <summary>Worker 共用的双工 Named Pipe 客户端；单一 reader 按 correlation_id 路由响应与 Wake。</summary>
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

    private readonly SemaphoreSlim _connectGate = new(1, 1);
    private readonly SemaphoreSlim _sendGate = new(1, 1);
    private readonly SemaphoreSlim _inflightGate = new(64, 64);
    private readonly ConcurrentDictionary<Guid, TaskCompletionSource<IpcFrameDto>> _pending = new();
    private readonly ConcurrentDictionary<Guid, IpcFrameDto> _resultCache = new();
    private readonly Channel<IpcFrameDto> _unsolicited = Channel.CreateUnbounded<IpcFrameDto>(
        new UnboundedChannelOptions { SingleReader = false, SingleWriter = true });
    private readonly object _connectionSync = new();
    private NamedPipeClientStream? _stream;
    private CancellationTokenSource? _readerCancellation;
    private Task? _readerTask;
    private int _stopped;

    public bool IsStopped => Volatile.Read(ref _stopped) != 0;

    public async Task ConnectAsync(CancellationToken cancellationToken = default)
    {
        ThrowIfStopped();
        await _connectGate.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            ThrowIfStopped();
            lock (_connectionSync)
            {
                if (_stream is { IsConnected: true })
                {
                    return;
                }
            }

            Exception? lastError = null;
            for (var attempt = 0; !cancellationToken.IsCancellationRequested; attempt++)
            {
                ThrowIfStopped();
                var stream = new NamedPipeClientStream(
                    ".",
                    pipeName,
                    PipeDirection.InOut,
                    PipeOptions.Asynchronous | PipeOptions.CurrentUserOnly);
                try
                {
                    await stream.ConnectAsync(1000, cancellationToken).ConfigureAwait(false);
                    var readerCancellation = new CancellationTokenSource();
                    lock (_connectionSync)
                    {
                        _stream = stream;
                        _readerCancellation = readerCancellation;
                        _readerTask = ReadLoopAsync(stream, readerCancellation.Token);
                    }
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
        finally
        {
            _connectGate.Release();
        }
    }

    public async Task<IpcFrameDto> ExchangeAsync(
        IpcFrameDto request,
        CancellationToken cancellationToken = default)
    {
        ThrowIfStopped();
        request = request.MessageId == Guid.Empty ? request with { MessageId = Guid.NewGuid() } : request;
        await _inflightGate.WaitAsync(cancellationToken).ConfigureAwait(false);
        var completion = new TaskCompletionSource<IpcFrameDto>(TaskCreationOptions.RunContinuationsAsynchronously);
        if (!_pending.TryAdd(request.MessageId, completion))
        {
            _inflightGate.Release();
            throw new InvalidOperationException($"重复的 IPC message_id：{request.MessageId}。");
        }

        try
        {
            NamedPipeClientStream stream;
            lock (_connectionSync)
            {
                stream = _stream is { IsConnected: true }
                    ? _stream
                    : throw new IOException("Named Pipe 尚未连接。");
            }

            await _sendGate.WaitAsync(cancellationToken).ConfigureAwait(false);
            try
            {
                await WriteFrameAsync(stream, JsonSerializer.SerializeToUtf8Bytes(request), cancellationToken)
                    .ConfigureAwait(false);
            }
            finally
            {
                _sendGate.Release();
            }

            return await completion.Task.WaitAsync(cancellationToken).ConfigureAwait(false);
        }
        finally
        {
            _pending.TryRemove(request.MessageId, out _);
            _inflightGate.Release();
        }
    }

    public async IAsyncEnumerable<IpcFrameDto> ReadUnsolicitedAsync(
        [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        await foreach (var frame in _unsolicited.Reader.ReadAllAsync(cancellationToken).ConfigureAwait(false))
        {
            yield return frame;
        }
    }

    public void CacheCriticalResult(Guid commandId, IpcFrameDto result) =>
        _resultCache[commandId] = result;

    public bool TryGetCachedResult(Guid commandId, out IpcFrameDto? result) =>
        _resultCache.TryGetValue(commandId, out result);

    public bool AcknowledgeResult(Guid commandId) => _resultCache.TryRemove(commandId, out _);

    public async ValueTask LatchStopAsync()
    {
        if (Interlocked.Exchange(ref _stopped, 1) != 0)
        {
            return;
        }

        NamedPipeClientStream? stream;
        CancellationTokenSource? readerCancellation;
        Task? readerTask;
        lock (_connectionSync)
        {
            stream = _stream;
            readerCancellation = _readerCancellation;
            readerTask = _readerTask;
            _stream = null;
            _readerCancellation = null;
            _readerTask = null;
        }

        readerCancellation?.Cancel();
        if (stream is not null)
        {
            await stream.DisposeAsync().ConfigureAwait(false);
        }
        if (readerTask is not null)
        {
            try
            {
                await readerTask.ConfigureAwait(false);
            }
            catch (OperationCanceledException) { }
            catch (IOException) { }
        }
        readerCancellation?.Dispose();
        FailPending(new OperationCanceledException("运行组停止闩锁已设置。"));
        _unsolicited.Writer.TryComplete();
    }

    public async ValueTask DisposeAsync()
    {
        await LatchStopAsync().ConfigureAwait(false);
        _connectGate.Dispose();
        _sendGate.Dispose();
        _inflightGate.Dispose();
        GC.SuppressFinalize(this);
    }

    private async Task ReadLoopAsync(NamedPipeClientStream stream, CancellationToken cancellationToken)
    {
        Exception? failure = null;
        try
        {
            while (!cancellationToken.IsCancellationRequested && stream.IsConnected)
            {
                var payload = await ReadFrameAsync(stream, cancellationToken).ConfigureAwait(false);
                var frame = JsonSerializer.Deserialize<IpcFrameDto>(payload)
                    ?? throw new InvalidDataException("ControlHost 返回了空 IPC 帧。");
                if (frame.CorrelationId is Guid correlationId)
                {
                    if (_pending.TryGetValue(correlationId, out var completion))
                    {
                        completion.TrySetResult(frame);
                    }
                    continue;
                }

                await _unsolicited.Writer.WriteAsync(frame, cancellationToken).ConfigureAwait(false);
            }
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested) { }
        catch (Exception exception) when (exception is IOException or EndOfStreamException or InvalidDataException)
        {
            failure = exception;
        }
        finally
        {
            CancellationTokenSource? readerCancellation = null;
            lock (_connectionSync)
            {
                if (ReferenceEquals(_stream, stream))
                {
                    FailPending(failure ?? new IOException("Named Pipe 连接已关闭。"));
                    _stream = null;
                    readerCancellation = _readerCancellation;
                    _readerCancellation = null;
                    _readerTask = null;
                }
            }
            readerCancellation?.Dispose();
            await stream.DisposeAsync().ConfigureAwait(false);
        }
    }

    private void FailPending(Exception exception)
    {
        foreach (var pending in _pending.Values)
        {
            pending.TrySetException(exception);
        }
    }

    private void ThrowIfStopped()
    {
        if (IsStopped)
        {
            throw new InvalidOperationException("运行组停止闩锁已设置，拒绝自动重连或发送消息。");
        }
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
