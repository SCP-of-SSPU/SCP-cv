using ScpCv.Domain.Model;
using ScpCv.Infrastructure.Commands;
using ScpCv.Infrastructure.Runtime;
using ScpCv.Integration.Tests.Fixtures;

namespace ScpCv.Integration.Tests;

/// <summary>SC-002/003 的可重复 simulation 故障注入样本，不依赖真实播放器。</summary>
public sealed class ReliabilityAcceptanceTests
{
    [Fact]
    public async Task LostAckAndStaleOwnerNeverReplayExternalCommand()
    {
        await using var fixture = await ControlHostFixture.CreateAsync();
        var start = await fixture.RuntimeAuthority.BeginStartAsync(Guid.NewGuid());
        await fixture.RuntimeAuthority.ArmAsync(start.ExplicitStartRequestId!.Value, start.GroupEpoch);
        var worker = Guid.NewGuid();
        var owner = await fixture.RuntimeAuthority.RegisterWorkerAsync(new RegisterWorker(
            CommandTargetKind.Display, 1, worker, 500, DateTimeOffset.UtcNow, 1, start.GroupEpoch, "[]"));
        var lease = new CommandLeaseService(fixture.Commands, fixture.RuntimeAuthority, fixture.Database, fixture.Writes, fixture.TimeProvider);

        for (var index = 0; index < 100; index++)
        {
            await fixture.Commands.EnqueueAsync(new EnqueueCommand(CommandTargetKind.Display, 1, "NEXT", "{}", 1, index + 1));
            var claimed = await lease.ClaimAsync(new LeaseClaimRequest(CommandTargetKind.Display, 1, worker, owner.OwnerEpoch, start.GroupEpoch, TimeSpan.FromSeconds(10)));
            Assert.NotNull(claimed);
            var accepted = await new CommandResultService(fixture.Commands).AcceptAsync(new CompleteCommand(
                claimed!.CommandId, claimed.ClaimToken!.Value, owner.OwnerEpoch,
                CommandStatus.Uncertain, "execution_uncertain", $"uncertain:{index}", "{\"reason\":\"ack_lost\"}"));
            Assert.True(accepted.Accepted);
            Assert.Null(await lease.ClaimAsync(new LeaseClaimRequest(CommandTargetKind.Display, 1, worker, owner.OwnerEpoch, start.GroupEpoch, TimeSpan.FromSeconds(1))));
        }
    }
}
