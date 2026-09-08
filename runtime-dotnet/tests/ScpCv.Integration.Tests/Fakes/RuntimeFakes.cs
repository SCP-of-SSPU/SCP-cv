using System.Collections.Concurrent;
using ScpCv.Domain.Model;
using ScpCv.Infrastructure.Commands;
using ScpCv.Infrastructure.Runtime;

namespace ScpCv.Integration.Tests.Fakes;

public sealed class DeterministicTimeProvider(DateTimeOffset initialTime) : TimeProvider
{
    private long _utcTicks = initialTime.UtcTicks;

    public override DateTimeOffset GetUtcNow() =>
        new(Interlocked.Read(ref _utcTicks), TimeSpan.Zero);

    public void Advance(TimeSpan duration)
    {
        ArgumentOutOfRangeException.ThrowIfLessThan(duration, TimeSpan.Zero);
        Interlocked.Add(ref _utcTicks, duration.Ticks);
    }
}

public sealed class FakeRuntimeWorker(Guid instanceId, long ownerEpoch)
{
    private readonly ConcurrentDictionary<Guid, int> _executions = new();

    public Guid InstanceId { get; } = instanceId;
    public long OwnerEpoch { get; } = ownerEpoch;

    public int ExecutionCount(Guid commandId) =>
        _executions.TryGetValue(commandId, out var count) ? count : 0;

    public CompleteCommand Execute(CommandRecord command, string resultHash = "fake:ok")
    {
        ArgumentNullException.ThrowIfNull(command);
        if (command.ClaimToken is null || command.ConsumerInstanceId != InstanceId || command.OwnerEpoch != OwnerEpoch)
        {
            throw new InvalidOperationException("Fake Worker 只能执行绑定到自身 token/epoch 的租约。");
        }

        _executions.AddOrUpdate(command.CommandId, 1, static (_, count) => checked(count + 1));
        return new CompleteCommand(
            command.CommandId,
            command.ClaimToken.Value,
            OwnerEpoch,
            CommandStatus.Completed,
            "ok",
            resultHash,
            "{\"fake\":true}");
    }
}

public sealed class FakeOfficeHost
{
    private readonly ConcurrentDictionary<Guid, CompleteOfficeOperation> _results = new();
    private readonly ConcurrentDictionary<Guid, int> _executions = new();

    public CompleteOfficeOperation Execute(RegisterOfficeOperation request, string resultFingerprint = "fake:office-ok")
    {
        ArgumentNullException.ThrowIfNull(request);
        var result = new CompleteOfficeOperation(
            request.OperationId,
            request.HostEpoch,
            request.SlotEpoch,
            OperationStatus.Succeeded,
            resultFingerprint,
            string.Empty);
        var existing = _results.GetOrAdd(request.OperationId, result);
        if (existing != result)
        {
            throw new OfficeOperationConflictException("Fake Office 收到相同 operation_id 的不同请求结果。");
        }

        _executions.AddOrUpdate(request.OperationId, 1, static (_, count) => checked(count + 1));
        return existing;
    }

    public int ExecutionCount(Guid operationId) =>
        _executions.TryGetValue(operationId, out var count) ? count : 0;
}

public sealed class FakeDeviceAdapter
{
    private readonly ConcurrentDictionary<string, string> _states = new(StringComparer.Ordinal);

    public bool FailNextOperation { get; set; }

    public string GetState(string deviceName) =>
        _states.TryGetValue(deviceName, out var state) ? state : "off";

    public void SetState(string deviceName, string state)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(deviceName);
        if (FailNextOperation)
        {
            FailNextOperation = false;
            throw new InvalidOperationException("deterministic fake device failure");
        }

        _states[deviceName] = state;
    }
}
