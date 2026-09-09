using System.Diagnostics;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using ScpCv.Contracts.Ipc;

namespace ScpCv.Contracts.Runtime;

public sealed record RuntimeWorkerIdentity(
    string Role,
    Guid InstanceId,
    IpcTargetDto? Target,
    IReadOnlyList<string> Capabilities);

public sealed record WorkerExecutionResult(
    string Status,
    string ResultCode,
    JsonElement ActualState,
    IReadOnlyDictionary<string, JsonElement>? Evidence = null);

/// <summary>Worker 的通用握手、补偿领取、续租、完成确认与主动 Wake 消费循环。</summary>
public sealed class RuntimeWorkerSession(
    string pipeName,
    RuntimeWorkerIdentity identity) : IAsyncDisposable
{
    private readonly RuntimePipeClient _client = new(pipeName);
    private readonly SemaphoreSlim _readyGate = new(1, 1);
    private readonly SemaphoreSlim _wakeSignal = new(0, 1);
    private readonly CancellationTokenSource _shutdown = new();
    private long _reportSequence;
    private long _readyConnectionGeneration;
    private int _disposed;

    public long OwnerEpoch { get; private set; }
    public long GroupEpoch { get; private set; }
    public string GroupState { get; private set; } = "stopped";

    public async Task ConnectAndReadyAsync(CancellationToken cancellationToken = default)
    {
        await _readyGate.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            await _client.ConnectAsync(cancellationToken).ConfigureAwait(false);
            var connectionGeneration = _client.ConnectionGeneration;
            if (Volatile.Read(ref _readyConnectionGeneration) == connectionGeneration) return;

            using var process = Process.GetCurrentProcess();
            var hello = await _client.ExchangeAsync(Frame("hello", new HelloDto
            {
                Role = identity.Role,
                ProcessId = process.Id,
                ProcessStartTime = new DateTimeOffset(process.StartTime.ToUniversalTime(), TimeSpan.Zero).ToString("O"),
                LogonSessionId = process.SessionId,
                Capabilities = identity.Capabilities,
            }), cancellationToken).ConfigureAwait(false);
            if (!string.Equals(hello.MessageType, "welcome", StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException($"ControlHost 拒绝 {identity.Role} 握手：{hello.MessageType}");

            var welcome = hello.Payload.Deserialize<WelcomeDto>()
                ?? throw new InvalidDataException("Welcome payload 无效。");
            OwnerEpoch = hello.OwnerEpoch;
            GroupEpoch = welcome.GroupEpoch;
            GroupState = welcome.GroupState;
            var ready = await _client.ExchangeAsync(Frame("worker_ready", new WorkerReadyDto
            {
                UiReady = true,
                Dependencies = identity.Capabilities.ToDictionary(value => value, _ => "ready", StringComparer.Ordinal),
                Detail = "runtime_loop_ready",
            }), cancellationToken).ConfigureAwait(false);
            if (!string.Equals(ready.MessageType, "health_accepted", StringComparison.OrdinalIgnoreCase) ||
                !ready.Payload.TryGetProperty("accepted", out var accepted) ||
                !accepted.GetBoolean())
            {
                throw new InvalidOperationException($"ControlHost 未接受 {identity.Role} ready 状态。");
            }

            Volatile.Write(ref _readyConnectionGeneration, connectionGeneration);
        }
        finally
        {
            _readyGate.Release();
        }
    }

    public async Task RunAsync(
        Func<CommandLeaseDto, CancellationToken, Task<WorkerExecutionResult>> execute,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(execute);
        using var linked = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken, _shutdown.Token);
        var notifications = ConsumeNotificationsAsync(linked.Token);
        try
        {
            while (!linked.IsCancellationRequested)
            {
                try
                {
                    await ConnectAndReadyAsync(linked.Token).ConfigureAwait(false);
                    await ReplayCachedResultsAsync(linked.Token).ConfigureAwait(false);
                    var response = await _client.ExchangeAsync(Frame("claim_request", new ClaimRequestDto
                    {
                        GroupEpoch = GroupEpoch,
                    }), linked.Token).ConfigureAwait(false);
                    if (string.Equals(response.MessageType, "command_lease", StringComparison.OrdinalIgnoreCase))
                    {
                        var lease = response.Payload.Deserialize<CommandLeaseDto>()
                            ?? throw new InvalidDataException("CommandLease payload 无效。");
                        await ExecuteAndConfirmAsync(lease, execute, linked.Token).ConfigureAwait(false);
                        continue;
                    }
                    if (string.Equals(response.MessageType, "error", StringComparison.OrdinalIgnoreCase))
                    {
                        throw new InvalidOperationException($"Runtime claim 被拒绝：{response.Payload}");
                    }

                    await WaitForWakeOrPollAsync(linked.Token).ConfigureAwait(false);
                }
                catch (IOException) when (!linked.IsCancellationRequested)
                {
                    // 首次登记竞态或运行中断线都保持 fail closed，并由下一轮重新握手。
                }
            }
        }
        finally
        {
            _shutdown.Cancel();
            try { await notifications.ConfigureAwait(false); } catch (OperationCanceledException) { }
        }
    }

    public async Task SendAudioFinishedAsync(
        AudioFinishedDto finished,
        CancellationToken cancellationToken = default)
    {
        using var linked = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken, _shutdown.Token);
        var frame = Frame("audio_finished", finished);
        while (!linked.IsCancellationRequested)
        {
            try
            {
                await ConnectAndReadyAsync(linked.Token).ConfigureAwait(false);
                var response = await _client.ExchangeAsync(frame, linked.Token).ConfigureAwait(false);
                if (!string.Equals(response.MessageType, "event_accepted", StringComparison.OrdinalIgnoreCase) ||
                    !response.Payload.TryGetProperty("accepted", out var accepted) ||
                    !accepted.GetBoolean())
                {
                    throw new InvalidOperationException($"AudioFinished 未被接受：{response.MessageType}");
                }
                return;
            }
            catch (IOException) when (!linked.IsCancellationRequested)
            {
                // 保留同一 message_id/event_id，经重连后由 ControlHost 幂等确认。
            }
        }

        cancellationToken.ThrowIfCancellationRequested();
        throw new OperationCanceledException("AudioFinished 上报因 Worker 停止而取消。", _shutdown.Token);
    }

    public async ValueTask DisposeAsync()
    {
        if (Interlocked.Exchange(ref _disposed, 1) != 0) return;
        _shutdown.Cancel();
        await _client.DisposeAsync().ConfigureAwait(false);
        _shutdown.Dispose();
        _readyGate.Dispose();
        _wakeSignal.Dispose();
        GC.SuppressFinalize(this);
    }

    private async Task ExecuteAndConfirmAsync(
        CommandLeaseDto lease,
        Func<CommandLeaseDto, CancellationToken, Task<WorkerExecutionResult>> execute,
        CancellationToken cancellationToken)
    {
        WorkerExecutionResult result;
        try
        {
            var execution = execute(lease, cancellationToken);
            while (!execution.IsCompleted)
            {
                var completed = await Task.WhenAny(execution, Task.Delay(TimeSpan.FromSeconds(5), cancellationToken))
                    .ConfigureAwait(false);
                if (completed == execution) break;
                var renewal = await _client.ExchangeAsync(Frame("lease_renew", new LeaseRenewDto
                {
                    CommandId = lease.CommandId,
                    ClaimToken = lease.ClaimToken,
                    OwnerEpoch = lease.OwnerEpoch,
                    Stage = "executing",
                    UiHealthy = true,
                }), cancellationToken).ConfigureAwait(false);
                if (!string.Equals(renewal.MessageType, "renew_result", StringComparison.OrdinalIgnoreCase) ||
                    !renewal.Payload.Deserialize<RenewResultDto>()!.Accepted)
                {
                    throw new InvalidOperationException("命令租约续期被 fencing。" );
                }
            }
            result = await execution.ConfigureAwait(false);
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            result = new WorkerExecutionResult(
                "failed",
                $"worker_exception:{exception.GetType().Name}",
                JsonSerializer.SerializeToElement(new { playback_state = "error", error_message = exception.Message }),
                new Dictionary<string, JsonElement>
                {
                    ["exception_type"] = JsonSerializer.SerializeToElement(exception.GetType().Name),
                });
        }

        var evidence = result.Evidence?.ToDictionary(pair => pair.Key, pair => pair.Value, StringComparer.Ordinal) ?? [];
        var resultHash = ComputeHash(lease, result, evidence);
        var frame = Frame("command_result", new CommandResultDto
        {
            CommandId = lease.CommandId,
            ClaimToken = lease.ClaimToken,
            OwnerEpoch = lease.OwnerEpoch,
            Status = result.Status,
            ResultCode = result.ResultCode,
            ActualState = result.ActualState,
            Evidence = evidence,
            ResultHash = resultHash,
        });
        _client.CacheCriticalResult(lease.CommandId, frame);
        var accepted = await _client.ExchangeAsync(frame, cancellationToken).ConfigureAwait(false);
        if (string.Equals(accepted.MessageType, "result_accepted", StringComparison.OrdinalIgnoreCase) &&
            accepted.Payload.Deserialize<ResultAcceptedDto>() is { Accepted: true })
        {
            _client.AcknowledgeResult(lease.CommandId);
        }
        else
        {
            throw new InvalidOperationException($"CommandResult 未被接受：{accepted.MessageType}");
        }

        await _client.ExchangeAsync(Frame("state_report", new StateReportDto
        {
            SourceGeneration = lease.SourceGeneration,
            ReportSequence = Interlocked.Increment(ref _reportSequence),
            ObservedAt = DateTimeOffset.UtcNow.ToString("O"),
            State = result.ActualState,
        }), cancellationToken).ConfigureAwait(false);
    }

    private async Task ConsumeNotificationsAsync(CancellationToken cancellationToken)
    {
        await foreach (var frame in _client.ReadUnsolicitedAsync(cancellationToken).ConfigureAwait(false))
        {
            if (string.Equals(frame.MessageType, "wake", StringComparison.OrdinalIgnoreCase))
            {
                if (_wakeSignal.CurrentCount == 0) _wakeSignal.Release();
            }
            else if (string.Equals(frame.MessageType, "shutdown_request", StringComparison.OrdinalIgnoreCase))
            {
                _shutdown.Cancel();
                return;
            }
        }
    }

    private async Task WaitForWakeOrPollAsync(CancellationToken cancellationToken)
    {
        _ = await _wakeSignal.WaitAsync(TimeSpan.FromSeconds(1), cancellationToken).ConfigureAwait(false);
    }

    private async Task ReplayCachedResultsAsync(CancellationToken cancellationToken)
    {
        foreach (var cached in _client.GetCachedResults())
        {
            var response = await _client.ExchangeAsync(cached.Value, cancellationToken).ConfigureAwait(false);
            if (string.Equals(response.MessageType, "result_accepted", StringComparison.OrdinalIgnoreCase) &&
                response.Payload.Deserialize<ResultAcceptedDto>() is { Accepted: true })
            {
                _client.AcknowledgeResult(cached.Key);
                continue;
            }

            throw new InvalidOperationException($"缓存 CommandResult 未被接受：{response.MessageType}");
        }
    }

    private IpcFrameDto Frame<T>(string messageType, T payload) => new()
    {
        MessageType = messageType,
        MessageId = Guid.NewGuid(),
        InstanceId = identity.InstanceId,
        OwnerEpoch = OwnerEpoch,
        Target = identity.Target,
        Payload = JsonSerializer.SerializeToElement(payload),
    };

    private static string ComputeHash(
        CommandLeaseDto lease,
        WorkerExecutionResult result,
        IReadOnlyDictionary<string, JsonElement> evidence)
    {
        var json = JsonSerializer.Serialize(new
        {
            lease.CommandId,
            result.Status,
            result.ResultCode,
            result.ActualState,
            evidence,
        });
        return Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(json))).ToLowerInvariant();
    }
}
