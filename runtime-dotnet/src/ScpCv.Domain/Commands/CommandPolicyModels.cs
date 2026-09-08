namespace ScpCv.Domain.Commands;

/// <summary>策略计算所需的最小 pending 命令投影，避免 Domain 依赖 EF/基础设施。</summary>
public sealed record PendingCommand(Guid CommandId, string Command);

public sealed record CommandPolicyDecision(
    string NormalizedCommand,
    IReadOnlySet<Guid> SupersededCommandIds);
