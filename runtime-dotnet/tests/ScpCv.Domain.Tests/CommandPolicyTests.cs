using ScpCv.Domain.Commands;

namespace ScpCv.Domain.Tests;

public sealed class CommandPolicyTests
{
    [Fact]
    public void DisplayOpenReplacesAllPendingDisplayIntents()
    {
        var first = new PendingCommand(Guid.NewGuid(), "PLAY");
        var second = new PendingCommand(Guid.NewGuid(), "SET_VOLUME");

        var result = DisplayCommandPolicy.Evaluate(" open ", [first, second]);

        Assert.Equal("OPEN", result.NormalizedCommand);
        Assert.Equal(
            new[] { first.CommandId, second.CommandId }.OrderBy(id => id),
            result.SupersededCommandIds.OrderBy(id => id));
    }

    [Fact]
    public void DisplayCoalescingOnlyReplacesSamePendingControl()
    {
        var seek = new PendingCommand(Guid.NewGuid(), "SEEK");
        var volume = new PendingCommand(Guid.NewGuid(), "SET_VOLUME");

        var result = DisplayCommandPolicy.Evaluate("SET_VOLUME", [seek, volume]);

        Assert.Equal([volume.CommandId], result.SupersededCommandIds);
    }

    [Fact]
    public void DisplayResetAndCloseHaveReplacementSemantics()
    {
        var pending = new[] { new PendingCommand(Guid.NewGuid(), "NEXT") };

        Assert.Single(DisplayCommandPolicy.Evaluate("RESET_PPT", pending).SupersededCommandIds);
        Assert.Single(DisplayCommandPolicy.Evaluate("CLOSE", pending).SupersededCommandIds);
    }

    [Fact]
    public void AudioOpenDoesNotClearPendingQueue()
    {
        var pending = new[]
        {
            new PendingCommand(Guid.NewGuid(), "OPEN"),
            new PendingCommand(Guid.NewGuid(), "NEXT"),
            new PendingCommand(Guid.NewGuid(), "SET_VOLUME"),
        };

        var result = AudioCommandPolicy.Evaluate("OPEN", pending);

        Assert.Empty(result.SupersededCommandIds);
    }

    [Fact]
    public void AudioControlUpdatesCoalesceInOrderByCommandKind()
    {
        var oldVolume = new PendingCommand(Guid.NewGuid(), "SET_VOLUME");
        var next = new PendingCommand(Guid.NewGuid(), "NEXT");

        var result = AudioCommandPolicy.Evaluate("SET_VOLUME", [oldVolume, next]);

        Assert.Equal([oldVolume.CommandId], result.SupersededCommandIds);
    }
}
