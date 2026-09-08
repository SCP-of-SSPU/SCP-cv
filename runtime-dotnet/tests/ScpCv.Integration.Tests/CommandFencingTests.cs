using ScpCv.Domain.Model;
using ScpCv.Infrastructure.Commands;
using ScpCv.Infrastructure.Runtime;
using ScpCv.Integration.Tests.Fixtures;

namespace ScpCv.Integration.Tests;

public sealed class CommandFencingTests
{
    [Fact]
    public async Task ClaimAndRenewRejectStaleGroupOrOwnerEpoch()
    {
        await using var fixture = await ControlHostFixture.CreateAsync();
        var start = await fixture.RuntimeAuthority.BeginStartAsync(Guid.NewGuid());
        await fixture.RuntimeAuthority.ArmAsync(start.ExplicitStartRequestId!.Value, start.GroupEpoch);
        var workerId = Guid.NewGuid();
        var registration = await fixture.RuntimeAuthority.RegisterWorkerAsync(new RegisterWorker(
            CommandTargetKind.Display, 1, workerId, 10, DateTimeOffset.UtcNow, 1,
            start.GroupEpoch, "[\"video\"]"));
        await fixture.Commands.EnqueueAsync(new EnqueueCommand(
            CommandTargetKind.Display, 1, "PLAY", "{}", 1, 1));
        var leases = new CommandLeaseService(
            fixture.Commands,
            fixture.RuntimeAuthority,
            fixture.Database,
            fixture.Writes,
            fixture.TimeProvider);

        await Assert.ThrowsAsync<CommandFenceException>(() => leases.ClaimAsync(new LeaseClaimRequest(
            CommandTargetKind.Display, 1, workerId, registration.OwnerEpoch + 1, start.GroupEpoch,
            TimeSpan.FromSeconds(30))));
        await Assert.ThrowsAsync<CommandFenceException>(() => leases.ClaimAsync(new LeaseClaimRequest(
            CommandTargetKind.Display, 1, workerId, registration.OwnerEpoch, start.GroupEpoch + 1,
            TimeSpan.FromSeconds(30))));

        var claimed = await leases.ClaimAsync(new LeaseClaimRequest(
            CommandTargetKind.Display, 1, workerId, registration.OwnerEpoch, start.GroupEpoch,
            TimeSpan.FromSeconds(30)));
        Assert.NotNull(claimed);
        Assert.False(await leases.RenewAsync(
            claimed!.CommandId, claimed.ClaimToken!.Value, registration.OwnerEpoch + 1, TimeSpan.FromSeconds(30)));
        Assert.True(await leases.RenewAsync(
            claimed.CommandId, claimed.ClaimToken.Value, registration.OwnerEpoch, TimeSpan.FromSeconds(30)));
    }

    [Fact]
    public async Task ExpiredLeaseCannotBeRequeuedWithoutSupervisorExitProof()
    {
        await using var fixture = await ControlHostFixture.CreateAsync();
        var start = await fixture.RuntimeAuthority.BeginStartAsync(Guid.NewGuid());
        await fixture.RuntimeAuthority.ArmAsync(start.ExplicitStartRequestId!.Value, start.GroupEpoch);
        var workerId = Guid.NewGuid();
        var registration = await fixture.RuntimeAuthority.RegisterWorkerAsync(new RegisterWorker(
            CommandTargetKind.Display, 1, workerId, 10, DateTimeOffset.UtcNow, 1,
            start.GroupEpoch, "[]"));
        await fixture.Commands.EnqueueAsync(new EnqueueCommand(
            CommandTargetKind.Display, 1, "NEXT", "{}", 1, 1));
        var leases = new CommandLeaseService(
            fixture.Commands,
            fixture.RuntimeAuthority,
            fixture.Database,
            fixture.Writes,
            fixture.TimeProvider);
        var claimed = await leases.ClaimAsync(new LeaseClaimRequest(
            CommandTargetKind.Display, 1, workerId, registration.OwnerEpoch, start.GroupEpoch,
            TimeSpan.FromSeconds(5)));
        fixture.TimeProvider.Advance(TimeSpan.FromSeconds(6));

        Assert.Null(await leases.RequeueExpiredAsync(
            CommandTargetKind.Display, 1, start.GroupEpoch, Guid.NewGuid(), registration.OwnerEpoch + 1,
            previousOwnerExitConfirmed: false));
        Assert.NotNull(claimed);
    }
}
