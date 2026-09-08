using ScpCv.Supervisor.Processes;
using ScpCv.Supervisor.Runtime;

var action = args.FirstOrDefault()?.ToLowerInvariant() ?? "status";
var registry = new ProcessRegistry();
var shutdown = new ShutdownCoordinator(registry);
if (action == "stop")
{
    await shutdown.StopAsync();
    return;
}

Console.WriteLine($"Supervisor {action}: interactive Windows session required for worker launch.");
