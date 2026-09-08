using System.Diagnostics;

namespace ScpCv.Supervisor.Processes;

public sealed record OwnedProcess(string Role, int ProcessId, DateTimeOffset StartTime, int SessionId, Process Process);

public sealed class ProcessRegistry
{
    private readonly Dictionary<int, OwnedProcess> _processes = [];
    private readonly object _gate = new();

    public OwnedProcess Register(string role, Process process)
    {
        ArgumentNullException.ThrowIfNull(process);
        process.Refresh();
        var owned = new OwnedProcess(role, process.Id, new DateTimeOffset(process.StartTime.ToUniversalTime(), TimeSpan.Zero), process.SessionId, process);
        lock (_gate) _processes[process.Id] = owned;
        return owned;
    }

    public static bool StillOwns(OwnedProcess owned)
    {
        try
        {
            owned.Process.Refresh();
            return !owned.Process.HasExited && owned.Process.Id == owned.ProcessId && owned.Process.SessionId == owned.SessionId &&
                new DateTimeOffset(owned.Process.StartTime.ToUniversalTime(), TimeSpan.Zero) == owned.StartTime;
        }
        catch (InvalidOperationException) { return false; }
    }

    public IReadOnlyList<OwnedProcess> Snapshot() { lock (_gate) return _processes.Values.ToArray(); }
    public void Remove(int processId) { lock (_gate) _processes.Remove(processId); }
}
