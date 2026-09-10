using System.Collections.Concurrent;
using System.Diagnostics;
using System.IO.Pipes;
using System.Text.Json;
using ScpCv.Contracts.Ipc;
using ScpCv.Domain.Model;
using ScpCv.Infrastructure.Commands;
using ScpCv.Infrastructure.Presentations;
using ScpCv.Infrastructure.Runtime;

namespace ScpCv.ControlHost.Ipc;

/// <summary>ControlHost 托管的并发本机管道 broker；持久命令仍是真源，Wake 仅为提示。</summary>
public interface IRuntimeReadinessGate
{
    Task<RuntimeReadinessResult> WaitForRuntimeReadyAsync(
        long groupEpoch,
        TimeSpan timeout,
        CancellationToken cancellationToken = default);
}

public sealed partial class RuntimePipeBroker(
    NamedPipeServer server,
    RegisteredProcessRegistry processRegistry,
    RuntimeMessageDispatcher dispatcher,
    RuntimeAuthorityRepository authority,
    ILogger<RuntimePipeBroker> logger,
    PresentationCoordinator? presentations = null) : BackgroundService, ICommandWakeNotifier, IRuntimeReadinessGate
{
    private static readonly string[] RequiredRuntimeRoles =
        ["player-1", "player-2", "player-3", "player-4", "audio", "office"];
    private readonly ConcurrentDictionary<string, RuntimeConnection> _connections = new(StringComparer.Ordinal);
    private readonly ConcurrentDictionary<Guid, OfficePendingRequest> _officePending = new();
    private readonly ConcurrentDictionary<Guid, OfficeCachedResult> _officeResults = new();
    private readonly Dictionary<string, ReadyWorker> _readyWorkers = new(StringComparer.Ordinal);
    private readonly PresentationCoordinator _presentations = presentations ?? new PresentationCoordinator();
    private readonly object _readinessSync = new();
    private TaskCompletionSource _readinessChanged = NewReadinessSignal();
    private long _officeHostEpoch;

    public string PipeName => server.PipeName;

    public RuntimeReadinessResult GetRuntimeReadiness(long groupEpoch)
    {
        lock (_readinessSync)
        {
            var missing = MissingRoles(groupEpoch);
            return new RuntimeReadinessResult(missing.Length == 0, missing);
        }
    }

    public async Task<RuntimeReadinessResult> WaitForRuntimeReadyAsync(
        long groupEpoch,
        TimeSpan timeout,
        CancellationToken cancellationToken = default)
    {
        ArgumentOutOfRangeException.ThrowIfLessThanOrEqual(timeout, TimeSpan.Zero);
        var started = Stopwatch.StartNew();
        while (true)
        {
            Task changed;
            string[] missing;
            lock (_readinessSync)
            {
                missing = MissingRoles(groupEpoch);
                if (missing.Length == 0) return new RuntimeReadinessResult(true, []);
                changed = _readinessChanged.Task;
            }

            var remaining = timeout - started.Elapsed;
            if (remaining <= TimeSpan.Zero) return new RuntimeReadinessResult(false, missing);
            try
            {
                await changed.WaitAsync(remaining, cancellationToken).ConfigureAwait(false);
            }
            catch (TimeoutException)
            {
                lock (_readinessSync) missing = MissingRoles(groupEpoch);
                return new RuntimeReadinessResult(false, missing);
            }
        }
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        while (!stoppingToken.IsCancellationRequested)
        {
            NamedPipeServerStream stream;
            try
            {
                stream = await server.AcceptAsync(stoppingToken).ConfigureAwait(false);
            }
            catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested)
            {
                break;
            }
            catch (Exception exception)
            {
                LogAcceptFailed(logger, exception);
                await Task.Delay(TimeSpan.FromMilliseconds(250), stoppingToken).ConfigureAwait(false);
                continue;
            }

            _ = HandleConnectionAsync(stream, stoppingToken);
        }
    }

    public async ValueTask WakeAsync(CommandWakeSignal signal, CancellationToken cancellationToken = default)
    {
        var key = signal.TargetKind == CommandTargetKind.Display ? $"player-{signal.TargetId}" : "audio";
        if (!_connections.TryGetValue(key, out var connection)) return;
        var frame = new IpcFrameDto
        {
            MessageType = "wake",
            MessageId = Guid.NewGuid(),
            InstanceId = Guid.Empty,
            OwnerEpoch = connection.OwnerEpoch,
            Target = new IpcTargetDto { Kind = signal.TargetKind.ToString().ToLowerInvariant(), Id = signal.TargetId },
            Payload = JsonSerializer.SerializeToElement(new WakeDto { HighestSequence = signal.HighestSequence }),
        };
        try
        {
            await connection.SendAsync(frame, cancellationToken).ConfigureAwait(false);
        }
        catch (Exception exception) when (exception is IOException or ObjectDisposedException)
        {
            _connections.TryRemove(new KeyValuePair<string, RuntimeConnection>(key, connection));
            RemoveReady(connection.Identity.Role, connection.Identity.InstanceId);
        }
    }

    private async Task HandleConnectionAsync(NamedPipeServerStream stream, CancellationToken stoppingToken)
    {
        RuntimeConnection? connection = null;
        try
        {
            var helloFrame = await ReadFrameAsync(stream, IpcProtocol.HandshakeTimeout, stoppingToken).ConfigureAwait(false);
            if (helloFrame.ProtocolVersion != IpcProtocol.Version || !string.Equals(helloFrame.MessageType, "hello", StringComparison.OrdinalIgnoreCase))
            {
                await SendErrorAsync(stream, helloFrame, "invalid_handshake", stoppingToken).ConfigureAwait(false);
                return;
            }

            var hello = helloFrame.Payload.Deserialize<HelloDto>() ?? throw new InvalidDataException("Hello payload 无效。");
            var identity = server.VerifyClient(stream, hello.Role, helloFrame.InstanceId);
            ValidateHello(identity, hello);
            var target = ResolveTarget(identity.Role, helloFrame.Target);
            var group = await authority.GetGroupAsync(stoppingToken).ConfigureAwait(false);
            var ownerEpoch = 0L;
            if (target is not null && group.State is RuntimeGroupState.Starting or RuntimeGroupState.Armed)
            {
                var ownership = await authority.RegisterWorkerAsync(new RegisterWorker(
                    target.Value.Kind,
                    target.Value.Id,
                    identity.InstanceId,
                    identity.ProcessId,
                    identity.ProcessStartTime,
                    identity.LogonSessionId,
                    group.GroupEpoch,
                    JsonSerializer.Serialize(hello.Capabilities),
                    PreviousOwnerExitConfirmed: true), stoppingToken).ConfigureAwait(false);
                ownerEpoch = ownership.OwnerEpoch;
            }
            else if (string.Equals(identity.Role, "office", StringComparison.Ordinal) &&
                     group.State is RuntimeGroupState.Starting or RuntimeGroupState.Armed)
            {
                // Office 没有 display target，仍须有独立 host epoch；旧 Host 的迟到结果因此会被 fencing。
                ownerEpoch = Interlocked.Increment(ref _officeHostEpoch);
                _presentations.FenceHost(ownerEpoch);
            }

            connection = new RuntimeConnection(stream, identity, target, ownerEpoch, group.GroupEpoch);
            if (_connections.TryGetValue(identity.Role, out var old))
            {
                RemoveReady(old.Identity.Role, old.Identity.InstanceId);
                await old.DisposeAsync().ConfigureAwait(false);
            }
            _connections[identity.Role] = connection;
            var welcome = Response(helloFrame, "welcome", new WelcomeDto
            {
                ServiceEpoch = Environment.TickCount64,
                GroupEpoch = group.GroupEpoch,
                GroupState = group.State.ToString().ToLowerInvariant(),
                AcceptedCapabilities = hello.Capabilities,
            }) with { OwnerEpoch = ownerEpoch };
            await connection.SendAsync(welcome, stoppingToken).ConfigureAwait(false);

            while (!stoppingToken.IsCancellationRequested && stream.IsConnected)
            {
                var frame = await ReadFrameAsync(stream, IpcProtocol.FrameReadTimeout, stoppingToken).ConfigureAwait(false);
                // 同一 Worker 执行长 Office 子操作时仍须能发送 LeaseRenew。
                // 单 reader 只拆帧；处理和响应可并发，实际写入由 RuntimeConnection 串行化。
                _ = DispatchAndRespondAsync(connection, frame, stoppingToken);
            }
        }
        catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested) { }
        catch (EndOfStreamException) { }
        catch (TimeoutException exception)
        {
            LogClientTimeout(logger, exception);
        }
        catch (Exception exception)
        {
            LogClientRejected(logger, exception);
        }
        finally
        {
            if (connection is not null)
            {
                _connections.TryRemove(new KeyValuePair<string, RuntimeConnection>(connection.Identity.Role, connection));
                RemoveReady(connection.Identity.Role, connection.Identity.InstanceId);
                await connection.DisposeAsync().ConfigureAwait(false);
            }
            else
            {
                await stream.DisposeAsync().ConfigureAwait(false);
            }
        }
    }

    private async Task DispatchAndRespondAsync(
        RuntimeConnection connection,
        IpcFrameDto frame,
        CancellationToken cancellationToken)
    {
        try
        {
            var response = await DispatchAuthenticatedAsync(connection, frame, cancellationToken).ConfigureAwait(false);
            await connection.SendAsync(response, cancellationToken).ConfigureAwait(false);
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested) { }
        catch (Exception exception) when (exception is IOException or ObjectDisposedException)
        {
            LogDispatchResponseFailed(logger, frame.MessageId, exception);
        }
        catch (Exception exception)
        {
            LogDispatchFailed(logger, frame.MessageId, exception);
            try
            {
                await connection.SendAsync(Response(frame, "error", new ErrorMessageDto
                {
                    Code = "dispatch_failed",
                    Stage = "dispatch",
                    Retryable = false,
                    Detail = exception.Message,
                }), cancellationToken).ConfigureAwait(false);
            }
            catch (Exception sendException) when (sendException is IOException or ObjectDisposedException)
            {
                LogDispatchResponseFailed(logger, frame.MessageId, sendException);
            }
        }
    }

    private async Task<IpcFrameDto> DispatchAuthenticatedAsync(
        RuntimeConnection connection,
        IpcFrameDto frame,
        CancellationToken cancellationToken)
    {
        if (frame.InstanceId != connection.Identity.InstanceId)
            return Response(frame, "error", new ErrorMessageDto { Code = "instance_fenced", Stage = "dispatch", Detail = "instance_id 与握手身份不匹配" });

        var messageType = frame.MessageType.Trim().ToLowerInvariant();
        if (messageType == "register_process")
        {
            if (!string.Equals(connection.Identity.Role, "supervisor", StringComparison.Ordinal))
                return Response(frame, "registration_result", new RegistrationResultDto { Accepted = false, Reason = "role_forbidden" });
            return RegisterChild(frame);
        }

        if (messageType is "health_report" or "worker_ready")
        {
            var workerReady = messageType == "worker_ready"
                ? frame.Payload.Deserialize<WorkerReadyDto>()
                : null;
            var uiHealthy = workerReady?.UiReady ??
                (frame.Payload.Deserialize<HealthReportDto>()?.UiHealthy ?? false);
            bool accepted;
            if (connection.Target is not null)
            {
                accepted = await authority.RecordHeartbeatAsync(
                    connection.Target.Value.Kind,
                    connection.Target.Value.Id,
                    connection.Identity.InstanceId,
                    connection.OwnerEpoch,
                    uiHealthy,
                    cancellationToken).ConfigureAwait(false);
            }
            else if (string.Equals(connection.Identity.Role, "office", StringComparison.Ordinal))
            {
                var group = await authority.GetGroupAsync(cancellationToken).ConfigureAwait(false);
                accepted = group.GroupEpoch == connection.GroupEpoch &&
                    group.State is RuntimeGroupState.Starting or RuntimeGroupState.Armed;
            }
            else
            {
                return Response(frame, "error", new ErrorMessageDto { Code = "invalid_target", Stage = "heartbeat" });
            }

            if (workerReady is not null)
            {
                var dependenciesReady = workerReady.Dependencies is { Count: > 0 } dependencies &&
                    dependencies.Values.All(value => string.Equals(value, "ready", StringComparison.OrdinalIgnoreCase));
                UpdateReady(connection, accepted && uiHealthy && dependenciesReady);
            }
            return Response(frame, "health_accepted", new { accepted });
        }

        if (messageType == "office_result" && string.Equals(connection.Identity.Role, "office", StringComparison.Ordinal))
        {
            return await CompleteOfficeResultAsync(connection, frame, cancellationToken).ConfigureAwait(false);
        }

        if (messageType == "office_request" && connection.Target is not null)
        {
            return await ForwardOfficeRequestAsync(connection, frame, cancellationToken).ConfigureAwait(false);
        }

        if (connection.Target is null)
            return Response(frame, "error", new ErrorMessageDto { Code = "invalid_target", Stage = "dispatch" });
        return await dispatcher.DispatchAsync(frame, cancellationToken).ConfigureAwait(false);
    }


    private IpcFrameDto RegisterChild(IpcFrameDto frame)
    {
        var request = frame.Payload.Deserialize<RegisterProcessDto>() ?? new RegisterProcessDto();
        if (!TryValidateChild(request, out var identity, out var reason))
            return Response(frame, "registration_result", new RegistrationResultDto { Accepted = false, Reason = reason });
        processRegistry.Register(identity!);
        return Response(frame, "registration_result", new RegistrationResultDto { Accepted = true, Reason = "registered" });
    }

    private static bool TryValidateChild(RegisterProcessDto request, out RegisteredProcessIdentity? identity, out string reason)
    {
        identity = null;
        reason = "invalid_process";
        if (!IsKnownRole(request.Role) || request.ProcessId <= 0 || request.InstanceId == Guid.Empty ||
            !DateTimeOffset.TryParse(request.ProcessStartTime, out var claimedStart)) return false;
        try
        {
            using var process = Process.GetProcessById(request.ProcessId);
            var actualStart = new DateTimeOffset(process.StartTime.ToUniversalTime(), TimeSpan.Zero);
            if (process.HasExited || process.SessionId != request.LogonSessionId || actualStart != claimedStart)
            {
                reason = "process_identity_mismatch";
                return false;
            }
            identity = new RegisteredProcessIdentity(request.ProcessId, actualStart, process.SessionId, request.Role, request.InstanceId);
            reason = "registered";
            return true;
        }
        catch (ArgumentException) { return false; }
        catch (InvalidOperationException) { return false; }
    }

    private static void ValidateHello(RegisteredProcessIdentity identity, HelloDto hello)
    {
        if (hello.ProcessId != identity.ProcessId || hello.LogonSessionId != identity.LogonSessionId ||
            !DateTimeOffset.TryParse(hello.ProcessStartTime, out var start) || start != identity.ProcessStartTime)
            throw new UnauthorizedAccessException("Hello 中的 PID/start-time/session 与 OS 已登记身份不匹配。");
    }

    private static (CommandTargetKind Kind, int Id)? ResolveTarget(string role, IpcTargetDto? target)
    {
        if (role.StartsWith("player-", StringComparison.Ordinal) && int.TryParse(role[7..], out var windowId) && windowId is >= 1 and <= 4 &&
            target?.Kind.Equals("display", StringComparison.OrdinalIgnoreCase) == true && target.Id == windowId)
            return (CommandTargetKind.Display, windowId);
        if (role == "audio" && target?.Kind.Equals("audio", StringComparison.OrdinalIgnoreCase) == true && target.Id == 1)
            return (CommandTargetKind.Audio, 1);
        if (role is "office" or "supervisor" && target is null) return null;
        throw new UnauthorizedAccessException("角色与命令目标不匹配。");
    }

    private static bool IsKnownRole(string role) => role is "audio" or "office" or "supervisor" or "player-1" or "player-2" or "player-3" or "player-4";

    private string[] MissingRoles(long groupEpoch) =>
        RequiredRuntimeRoles
            .Where(role => !_readyWorkers.TryGetValue(role, out var ready) || ready.GroupEpoch != groupEpoch)
            .ToArray();

    private void UpdateReady(RuntimeConnection connection, bool ready)
    {
        TaskCompletionSource changed;
        lock (_readinessSync)
        {
            if (ready)
            {
                _readyWorkers[connection.Identity.Role] = new ReadyWorker(
                    connection.Identity.InstanceId,
                    connection.GroupEpoch);
            }
            else if (_readyWorkers.TryGetValue(connection.Identity.Role, out var existing) &&
                     existing.InstanceId == connection.Identity.InstanceId)
            {
                _readyWorkers.Remove(connection.Identity.Role);
            }
            changed = _readinessChanged;
            _readinessChanged = NewReadinessSignal();
        }
        changed.TrySetResult();
    }

    private void RemoveReady(string role, Guid instanceId)
    {
        TaskCompletionSource? changed = null;
        lock (_readinessSync)
        {
            if (_readyWorkers.TryGetValue(role, out var existing) && existing.InstanceId == instanceId)
            {
                _readyWorkers.Remove(role);
                changed = _readinessChanged;
                _readinessChanged = NewReadinessSignal();
            }
        }
        changed?.TrySetResult();
    }

    private static TaskCompletionSource NewReadinessSignal() =>
        new(TaskCreationOptions.RunContinuationsAsynchronously);

    private static async Task<IpcFrameDto> ReadFrameAsync(Stream stream, TimeSpan timeout, CancellationToken cancellationToken)
    {
        var payload = await IpcFrameCodec.ReadPayloadAsync(stream, timeout, cancellationToken).ConfigureAwait(false);
        return JsonSerializer.Deserialize<IpcFrameDto>(payload) ?? throw new InvalidDataException("IPC 帧 JSON 无效。");
    }

    private static async Task SendErrorAsync(Stream stream, IpcFrameDto request, string code, CancellationToken cancellationToken)
    {
        var frame = Response(request, "error", new ErrorMessageDto { Code = code, Stage = "handshake", Retryable = false });
        await IpcFrameCodec.WritePayloadAsync(stream, JsonSerializer.SerializeToUtf8Bytes(frame), cancellationToken).ConfigureAwait(false);
    }

    private static IpcFrameDto Response<T>(IpcFrameDto request, string messageType, T payload) => new()
    {
        MessageType = messageType,
        MessageId = Guid.NewGuid(),
        CorrelationId = request.MessageId,
        InstanceId = Guid.Empty,
        OwnerEpoch = request.OwnerEpoch,
        Target = request.Target,
        Payload = JsonSerializer.SerializeToElement(payload),
    };

    private sealed class RuntimeConnection(
        NamedPipeServerStream stream,
        RegisteredProcessIdentity identity,
        (CommandTargetKind Kind, int Id)? target,
        long ownerEpoch,
        long groupEpoch) : IAsyncDisposable
    {
        private readonly SemaphoreSlim _sendGate = new(1, 1);
        public RegisteredProcessIdentity Identity { get; } = identity;
        public (CommandTargetKind Kind, int Id)? Target { get; } = target;
        public long OwnerEpoch { get; } = ownerEpoch;
        public long GroupEpoch { get; } = groupEpoch;

        public async Task SendAsync(IpcFrameDto frame, CancellationToken cancellationToken)
        {
            await _sendGate.WaitAsync(cancellationToken).ConfigureAwait(false);
            try
            {
                await IpcFrameCodec.WritePayloadAsync(stream, JsonSerializer.SerializeToUtf8Bytes(frame), cancellationToken).ConfigureAwait(false);
            }
            finally
            {
                _sendGate.Release();
            }
        }

        public async ValueTask DisposeAsync()
        {
            await stream.DisposeAsync().ConfigureAwait(false);
            _sendGate.Dispose();
        }
    }

    [LoggerMessage(EventId = 2201, Level = LogLevel.Error, Message = "接受 Runtime Named Pipe 连接失败")]
    private static partial void LogAcceptFailed(ILogger logger, Exception exception);

    [LoggerMessage(EventId = 2202, Level = LogLevel.Warning, Message = "Runtime 管道客户端超时断开")]
    private static partial void LogClientTimeout(ILogger logger, Exception exception);

    [LoggerMessage(EventId = 2203, Level = LogLevel.Warning, Message = "Runtime 管道客户端被拒绝或异常断开")]
    private static partial void LogClientRejected(ILogger logger, Exception exception);

    [LoggerMessage(EventId = 2204, Level = LogLevel.Warning, Message = "Office 操作 {operationId} 无法记录不确定结果")]
    private static partial void LogOfficeCompletionFailed(ILogger logger, Guid operationId, Exception exception);

    [LoggerMessage(EventId = 2205, Level = LogLevel.Warning, Message = "Runtime IPC 消息 {messageId} 的响应发送失败")]
    private static partial void LogDispatchResponseFailed(ILogger logger, Guid messageId, Exception exception);

    [LoggerMessage(EventId = 2206, Level = LogLevel.Warning, Message = "Runtime IPC 消息 {messageId} 的派发失败")]
    private static partial void LogDispatchFailed(ILogger logger, Guid messageId, Exception exception);

    private sealed record ReadyWorker(Guid InstanceId, long GroupEpoch);
}

public sealed record RuntimeReadinessResult(bool Ready, IReadOnlyList<string> MissingRoles);
