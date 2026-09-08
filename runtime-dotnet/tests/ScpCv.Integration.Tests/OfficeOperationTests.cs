using ScpCv.Domain.Model;
using ScpCv.Domain.Rules;
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
}
