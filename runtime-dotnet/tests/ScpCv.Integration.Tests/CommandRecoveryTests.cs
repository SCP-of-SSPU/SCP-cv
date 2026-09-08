using Microsoft.EntityFrameworkCore;
using ScpCv.Domain.Model;
using ScpCv.Infrastructure.Commands;
using ScpCv.Infrastructure.Runtime;
using ScpCv.Integration.Tests.Fixtures;

namespace ScpCv.Integration.Tests;

public sealed class CommandRecoveryTests
{
    [Fact]
    public async Task DuplicateResultIsAcknowledgedWithoutSecondExecution()
    {
        await using var fixture = await ControlHostFixture.CreateAsync();
        var start = await fixture.RuntimeAuthority.BeginStartAsync(Guid.NewGuid());
        await fixture.RuntimeAuthority.ArmAsync(start.ExplicitStartRequestId!.Value, start.GroupEpoch);
        var workerId = Guid.NewGuid();
        var registration = await fixture.RuntimeAuthority.RegisterWorkerAsync(new RegisterWorker(
            CommandTargetKind.Display, 1, workerId, 11, DateTimeOffset.UtcNow, 1,
            start.GroupEpoch, "[]"));
        await fixture.Commands.EnqueueAsync(new EnqueueCommand(
            CommandTargetKind.Display, 1, "PLAY", "{}", 1, 1));
        var claimed = await fixture.Commands.ClaimAsync(new ClaimCommand(
            CommandTargetKind.Display, 1, workerId, registration.OwnerEpoch, start.GroupEpoch,
            TimeSpan.FromSeconds(30)));
        Assert.NotNull(claimed);
        var result = new CompleteCommand(
            claimed!.CommandId, claimed.ClaimToken!.Value, registration.OwnerEpoch,
            CommandStatus.Completed, "ok", "", "{\"actual\":\"playing\"}");
        var service = new CommandResultService(fixture.Commands);

        var accepted = await service.AcceptAsync(result);
        var duplicate = await service.AcceptAsync(result);

        Assert.True(accepted.Accepted);
        Assert.False(accepted.Duplicate);
        Assert.True(duplicate.Accepted);
        Assert.True(duplicate.Duplicate);
    }

    [Fact]
    public async Task UncertainResultIsPersistedAndDoesNotBecomeAReplayableCommand()
    {
        await using var fixture = await ControlHostFixture.CreateAsync();
        var start = await fixture.RuntimeAuthority.BeginStartAsync(Guid.NewGuid());
        await fixture.RuntimeAuthority.ArmAsync(start.ExplicitStartRequestId!.Value, start.GroupEpoch);
        var workerId = Guid.NewGuid();
        var registration = await fixture.RuntimeAuthority.RegisterWorkerAsync(new RegisterWorker(
            CommandTargetKind.Display, 1, workerId, 12, DateTimeOffset.UtcNow, 1,
            start.GroupEpoch, "[]"));
        await fixture.Commands.EnqueueAsync(new EnqueueCommand(
            CommandTargetKind.Display, 1, "NEXT", "{}", 1, 1));
        var claimed = await fixture.Commands.ClaimAsync(new ClaimCommand(
            CommandTargetKind.Display, 1, workerId, registration.OwnerEpoch, start.GroupEpoch,
            TimeSpan.FromSeconds(30)));
        var result = new CompleteCommand(
            claimed!.CommandId, claimed.ClaimToken!.Value, registration.OwnerEpoch,
            CommandStatus.Uncertain, "execution_uncertain", "uncertain:1", "{\"reason\":\"ack_lost\"}");

        await fixture.Commands.CompleteAsync(result);

        await using var context = fixture.Database.CreateDbContext();
        var persisted = await context.CommandRecords.FindAsync(claimed.Id);
        Assert.NotNull(persisted);
        Assert.Equal(CommandStatus.Uncertain, persisted!.Status);
        Assert.Empty(await context.CommandRecords.Where(item => item.Status == CommandStatus.Pending).ToListAsync());
    }
}
