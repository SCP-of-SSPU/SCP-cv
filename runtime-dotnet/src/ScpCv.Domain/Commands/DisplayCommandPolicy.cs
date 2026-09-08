namespace ScpCv.Domain.Commands;

/// <summary>四个显示窗口的意图合并规则。</summary>
public static class DisplayCommandPolicy
{
    private static readonly HashSet<string> ReplacementCommands =
        new HashSet<string>(StringComparer.Ordinal) { "OPEN", "CLOSE", "RESET_PPT" };

    private static readonly HashSet<string> CoalescingCommands =
        new HashSet<string>(StringComparer.Ordinal) { "SEEK", "SET_LOOP", "SET_VOLUME", "SET_MUTE" };

    public static CommandPolicyDecision Evaluate(
        string command,
        IEnumerable<PendingCommand> pending)
    {
        var normalized = Normalize(command);
        ArgumentNullException.ThrowIfNull(pending);

        var superseded = ReplacementCommands.Contains(normalized)
            ? pending.Select(item => item.CommandId).ToHashSet()
            : CoalescingCommands.Contains(normalized)
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
