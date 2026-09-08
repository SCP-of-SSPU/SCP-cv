namespace ScpCv.Domain.Commands;

/// <summary>单实例背景音频的有序合并规则。</summary>
public static class AudioCommandPolicy
{
    private static readonly HashSet<string> CoalescingCommands =
        new HashSet<string>(StringComparer.Ordinal) { "SEEK", "SET_LOOP", "SET_VOLUME", "SET_MUTE" };

    public static CommandPolicyDecision Evaluate(
        string command,
        IEnumerable<PendingCommand> pending)
    {
        var normalized = Normalize(command);
        ArgumentNullException.ThrowIfNull(pending);

        // OPEN 是有序播放意图，不能清掉队列中的控制命令或已排队的 OPEN。
        var superseded = CoalescingCommands.Contains(normalized)
            ? pending
                .Where(item => string.Equals(Normalize(item.Command), normalized, StringComparison.Ordinal))
                .Select(item => item.CommandId)
                .ToHashSet()
            : new HashSet<Guid>();

        return new CommandPolicyDecision(normalized, superseded);
    }

    private static string Normalize(string command)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(command);
        return command.Trim().ToUpperInvariant();
    }
}
