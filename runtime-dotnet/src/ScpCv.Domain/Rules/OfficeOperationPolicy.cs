using ScpCv.Domain.Model;

namespace ScpCv.Domain.Rules;

public sealed record OfficeDispatchContext(
    RuntimeGroupState GroupState,
    long GroupEpoch,
    long RequestedGroupEpoch,
    long HostEpoch,
    long RequestedHostEpoch,
    long SlotEpoch,
    long RequestedSlotEpoch,
    DateTimeOffset Deadline,
    DateTimeOffset Now,
    OperationStatus Status);

public sealed record OfficeDispatchDecision(bool Allowed, string Code);

public static class OfficeOperationPolicy
{
    public static OfficeDispatchDecision AuthorizeBeforeStaCall(OfficeDispatchContext context)
    {
        ArgumentNullException.ThrowIfNull(context);
        if (context.Status is not (OperationStatus.Queued or OperationStatus.Running))
            return new OfficeDispatchDecision(false, "operation_not_dispatchable");
        if (context.GroupState != RuntimeGroupState.Armed)
            return new OfficeDispatchDecision(false, "group_not_armed");
        if (context.GroupEpoch != context.RequestedGroupEpoch)
            return new OfficeDispatchDecision(false, "group_epoch_stale");
        if (context.HostEpoch != context.RequestedHostEpoch)
            return new OfficeDispatchDecision(false, "host_epoch_stale");
        if (context.SlotEpoch != context.RequestedSlotEpoch)
            return new OfficeDispatchDecision(false, "slot_epoch_stale");
        if (context.Now >= context.Deadline)
            return new OfficeDispatchDecision(false, "deadline_expired");
        return new OfficeDispatchDecision(true, "authorized");
    }
}
