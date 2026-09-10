using ScpCv.Domain.Model;
using ScpCv.Domain.Rules;
using ScpCv.Contracts.Ipc;
using ScpCv.PowerPointHost.Interop;
using ScpCv.PowerPointHost.Sta;

namespace ScpCv.Integration.Tests;

public sealed class OfficeOperationTests
{
    [Fact]
    public void StaDequeueRevalidatesAllEpochsBeforeComCall()
    {
        var now = DateTimeOffset.UtcNow;
        var context = new OfficeDispatchContext(
            RuntimeGroupState.Armed, 4, 4, 8, 8, 12, 12,
            now.AddSeconds(1), now, OperationStatus.Queued);

        var result = OfficeOperationPolicy.AuthorizeBeforeStaCall(context);

        Assert.True(result.Allowed);
    }

    [Theory]
    [InlineData(RuntimeGroupState.Draining, "group_not_armed")]
    [InlineData(RuntimeGroupState.Armed, "group_epoch_stale")]
    public void StaleAuthorityOrDrainingGroupStopsOperationBeforeSta(
        RuntimeGroupState state,
        string expectedCode)
    {
        var now = DateTimeOffset.UtcNow;
        var result = OfficeOperationPolicy.AuthorizeBeforeStaCall(new OfficeDispatchContext(
            state, 4, state == RuntimeGroupState.Armed ? 3 : 4,
            8, 8, 12, 12, now.AddSeconds(1), now, OperationStatus.Queued));

        Assert.False(result.Allowed);
        Assert.Equal(expectedCode, result.Code);
    }

    [Fact]
    public void TimeoutAndCompletedInflightAreNotRetriedAsNewComCalls()
    {
        var now = DateTimeOffset.UtcNow;
        var expired = OfficeOperationPolicy.AuthorizeBeforeStaCall(new OfficeDispatchContext(
            RuntimeGroupState.Armed, 4, 4, 8, 8, 12, 12, now, now, OperationStatus.Running));
        var completed = OfficeOperationPolicy.AuthorizeBeforeStaCall(new OfficeDispatchContext(
            RuntimeGroupState.Armed, 4, 4, 8, 8, 12, 12, now.AddSeconds(1), now, OperationStatus.Succeeded));

        Assert.Equal("deadline_expired", expired.Code);
        Assert.Equal("operation_not_dispatchable", completed.Code);
    }

    [Fact]
    public async Task CompletedOperationIdIsServedFromStaResultCache()
    {
        using var dispatcher = new OfficeStaDispatcher();
        var calls = 0;
        var operationId = Guid.NewGuid();
        var first = await dispatcher.InvokeAsync(operationId, _ => Interlocked.Increment(ref calls));
        var second = await dispatcher.InvokeAsync(operationId, _ => Interlocked.Increment(ref calls));

        Assert.Equal(1, calls);
        Assert.Equal(first, second);
    }

    [Fact]
    public async Task OfficeHostCachesStableResultAndRejectsSameIdWithDifferentRequest()
    {
        using var dispatcher = new OfficeStaDispatcher();
        using var adapter = new PowerPointComAdapter(dispatcher);
        var executor = new PowerPointOfficeRequestExecutor(adapter, groupEpoch: 4, hostEpoch: 8);
        var operationId = Guid.NewGuid();
        var request = new OfficeRequestDto
        {
            OfficeOperationId = operationId,
            GroupEpoch = 4,
            HostEpoch = 8,
            SlotEpoch = 12,
            Deadline = DateTimeOffset.UtcNow.AddSeconds(5).ToString("O"),
            Operation = "unsupported-test-operation",
        };

        var first = await executor.ExecuteAsync(request);
        var duplicate = await executor.ExecuteAsync(request);
        var conflict = await executor.ExecuteAsync(request with { Operation = "different-operation" });

        Assert.Equal("unsupported_operation", first.ErrorCode);
        Assert.Equal(first.ResultFingerprint, duplicate.ResultFingerprint);
        Assert.Equal("office_operation_conflict", conflict.ErrorCode);
    }

    [Theory]
    [InlineData(3, 8, 12, "group_epoch_stale")]
    [InlineData(4, 7, 12, "host_epoch_stale")]
    [InlineData(4, 8, 0, "slot_epoch_stale")]
    public async Task OfficeHostRejectsStaleAuthorityBeforeSta(
        long groupEpoch,
        long hostEpoch,
        long slotEpoch,
        string expectedCode)
    {
        using var dispatcher = new OfficeStaDispatcher();
        using var adapter = new PowerPointComAdapter(dispatcher);
        var executor = new PowerPointOfficeRequestExecutor(adapter, groupEpoch: 4, hostEpoch: 8);

        var result = await executor.ExecuteAsync(new OfficeRequestDto
        {
            OfficeOperationId = Guid.NewGuid(),
            GroupEpoch = groupEpoch,
            HostEpoch = hostEpoch,
            SlotEpoch = slotEpoch,
            Deadline = DateTimeOffset.UtcNow.AddSeconds(5).ToString("O"),
            Operation = "open",
        });

        Assert.Equal(expectedCode, result.ErrorCode);
    }
}
