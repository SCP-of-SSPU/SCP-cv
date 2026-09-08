namespace ScpCv.Domain.Rules;

public sealed record ResourceKey(long SourceId, string SourceDigest, string Kind);

public sealed record ResourceSwitchDecision(bool Accepted, bool KeepCurrent, string Code)
{
    public static ResourceSwitchDecision Reject(string code) => new(false, true, code);
    public static ResourceSwitchDecision Accept() => new(true, false, "ready");
}

public static class ResourceSwitchPolicy
{
    public static ResourceSwitchDecision Decide(
        ResourceKey? current,
        long currentGeneration,
        ResourceKey candidate,
        long candidateGeneration,
        bool candidateReady,
        bool currentHealthy)
    {
        ArgumentNullException.ThrowIfNull(candidate);
        if (candidateGeneration < currentGeneration)
            return ResourceSwitchDecision.Reject("stale_generation");
        if (current is not null && candidateGeneration == currentGeneration && current != candidate)
            return ResourceSwitchDecision.Reject("stale_key");
        if (!candidateReady)
            return ResourceSwitchDecision.Reject(currentHealthy ? "candidate_not_ready" : "no_ready_resource");
        return ResourceSwitchDecision.Accept();
    }
}
