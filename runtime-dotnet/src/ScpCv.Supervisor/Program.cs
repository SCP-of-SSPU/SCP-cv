using System.Diagnostics;
using System.Text.Json;
using ScpCv.Contracts.Ipc;
using ScpCv.Contracts.Runtime;
using ScpCv.Supervisor.Processes;
using ScpCv.Supervisor.Runtime;

if (!OperatingSystem.IsWindows())
{
    Console.Error.WriteLine("Supervisor 仅支持 Windows x64 交互桌面。");
    return 2;
}

var action = GetOption(args, "action") ?? args.FirstOrDefault()?.ToLowerInvariant() ?? "status";
var runtimeRoot = Path.GetFullPath(GetOption(args, "runtime-root") ?? Path.Combine(AppContext.BaseDirectory, "runtime"));
var statePath = Path.GetFullPath(GetOption(args, "state") ?? Path.Combine(AppContext.BaseDirectory, "runtime-processes.json"));
var mediaMtxPath = GetOption(args, "mediamtx");
var controlPipe = GetOption(args, "control-pipe");

try
{
    return action switch
    {
        "start" => await StartAsync(runtimeRoot, statePath, mediaMtxPath, controlPipe),
        "stop" => await StopAsync(statePath),
        "restart" => await RestartAsync(runtimeRoot, statePath, mediaMtxPath, controlPipe),
        "status" => await StatusAsync(statePath),
        _ => Fail($"未知 Supervisor 动作：{action}。可用值：start、stop、restart、status。"),
    };
}
catch (Exception exception) when (exception is not OperationCanceledException)
{
    Console.Error.WriteLine($"Supervisor {action} 失败：{exception.Message}");
    return 1;
}

static async Task<int> StartAsync(string runtimeRoot, string statePath, string? mediaMtxPath, string? controlPipe)
{
    var existing = await ReadStateAsync(statePath);
    if (existing.Any(IsAlive))
    {
        Console.WriteLine("Supervisor 已有受管运行时，未重复启动。");
        return 0;
    }

    var registry = new ProcessRegistry();
    var owned = new RuntimeLauncher(registry).Start(runtimeRoot, mediaMtxPath);
    await using var control = string.IsNullOrWhiteSpace(controlPipe)
        ? null
        : await RegisterWithControlHostAsync(controlPipe, owned);
    await WriteStateAsync(statePath, owned);
    Console.WriteLine(JsonSerializer.Serialize(owned.Select(ToState), GetJsonOptions()));

    using var stop = new CancellationTokenSource();
    var failure = new TaskCompletionSource<string>(TaskCreationOptions.RunContinuationsAsynchronously);
    foreach (var process in owned)
    {
        process.Process.EnableRaisingEvents = true;
        process.Process.Exited += (_, _) =>
        {
            if (!stop.IsCancellationRequested) failure.TrySetResult(process.Role);
        };
    }

    Console.CancelKeyPress += (_, eventArgs) => { eventArgs.Cancel = true; stop.Cancel(); };
    var completed = await Task.WhenAny(failure.Task, Task.Delay(Timeout.InfiniteTimeSpan, stop.Token));
    if (completed == failure.Task)
    {
        Console.Error.WriteLine($"受管进程 {failure.Task.Result} 退出，触发整组协作停止。");
    }

    await new ShutdownCoordinator(registry).StopAsync();
    DeleteStateIfSafe(statePath);
    return completed == failure.Task ? 1 : 0;
}

static async Task<int> StopAsync(string statePath)
{
    var state = await ReadStateAsync(statePath);
    var registry = new ProcessRegistry();
    foreach (var item in state)
    {
        if (TryAttach(item, out var process)) registry.Register(item.Role, process);
    }

    await new ShutdownCoordinator(registry).StopAsync();
    DeleteStateIfSafe(statePath);
    Console.WriteLine("Supervisor 已完成受管进程停止请求。");
    return 0;
}

static async Task<int> RestartAsync(string runtimeRoot, string statePath, string? mediaMtxPath, string? controlPipe)
{
    await StopAsync(statePath);
    return await StartAsync(runtimeRoot, statePath, mediaMtxPath, controlPipe);
}

static async Task<RuntimePipeClient> RegisterWithControlHostAsync(
    string pipeName,
    IReadOnlyList<OwnedProcess> owned)
{
    var client = new RuntimePipeClient(pipeName);
    try
    {
        await client.ConnectAsync();
        var instanceId = Guid.NewGuid();
        using var process = Process.GetCurrentProcess();
        var hello = Frame("hello", instanceId, null, new HelloDto
        {
            Role = "supervisor",
            ProcessId = process.Id,
            ProcessStartTime = UtcStart(process).ToString("O"),
            LogonSessionId = process.SessionId,
            Capabilities = ["process_registry", "shutdown"],
        });
        var welcome = await client.ExchangeAsync(hello);
        if (!string.Equals(welcome.MessageType, "welcome", StringComparison.OrdinalIgnoreCase))
            throw new InvalidOperationException("ControlHost 未接受 Supervisor 握手。");

        foreach (var child in owned)
        {
            using var childProcess = Process.GetProcessById(child.ProcessId);
            var result = await client.ExchangeAsync(Frame("register_process", instanceId, null, new RegisterProcessDto
            {
                Role = child.Role,
                ProcessId = child.ProcessId,
                ProcessStartTime = child.StartTime.ToString("O"),
                LogonSessionId = child.SessionId,
                InstanceId = Guid.NewGuid(),
            }));
            var registration = result.Payload.Deserialize<RegistrationResultDto>();
            if (registration is not { Accepted: true })
                throw new InvalidOperationException($"ControlHost 拒绝登记 {child.Role}：{registration?.Reason}");
        }

        return client;
    }
    catch
    {
        await client.DisposeAsync();
        throw;
    }
}

static DateTimeOffset UtcStart(Process process) =>
    new(process.StartTime.ToUniversalTime(), TimeSpan.Zero);

static IpcFrameDto Frame<T>(string type, Guid instanceId, IpcTargetDto? target, T payload) => new()
{
    MessageType = type,
    MessageId = Guid.NewGuid(),
    InstanceId = instanceId,
    Target = target,
    Payload = JsonSerializer.SerializeToElement(payload),
};

static async Task<int> StatusAsync(string statePath)
{
    var state = await ReadStateAsync(statePath);
    Console.WriteLine(JsonSerializer.Serialize(state.Select(item => new
    {
        role = item.Role,
        process_id = item.ProcessId,
        process_start_time = item.StartTime,
        session_id = item.SessionId,
        alive = IsAlive(item),
    }), GetJsonOptions()));
    return 0;
}

static bool TryAttach(SupervisorProcessState item, out Process process)
{
    process = null!;
    try
    {
        process = Process.GetProcessById(item.ProcessId);
        var startTime = new DateTimeOffset(process.StartTime.ToUniversalTime(), TimeSpan.Zero);
        if (startTime != item.StartTime || process.SessionId != item.SessionId || process.HasExited)
        {
            process.Dispose();
            process = null!;
            return false;
        }

        return true;
    }
    catch (ArgumentException) { return false; }
    catch (InvalidOperationException) { return false; }
}

static bool IsAlive(SupervisorProcessState item)
{
    return TryAttach(item, out var process) && DisposeAfter(process);
}

static bool DisposeAfter(Process process)
{
    process.Dispose();
    return true;
}

static SupervisorProcessState ToState(OwnedProcess process) => new(process.Role, process.ProcessId, process.StartTime, process.SessionId);

static async Task<SupervisorProcessState[]> ReadStateAsync(string statePath)
{
    if (!File.Exists(statePath)) return [];
    await using var stream = File.OpenRead(statePath);
    return await JsonSerializer.DeserializeAsync<SupervisorProcessState[]>(stream, GetJsonOptions()) ?? [];
}

static async Task WriteStateAsync(string statePath, IReadOnlyList<OwnedProcess> processes)
{
    var parent = Path.GetDirectoryName(statePath);
    if (!string.IsNullOrWhiteSpace(parent)) Directory.CreateDirectory(parent);
    await using var stream = File.Create(statePath);
    await JsonSerializer.SerializeAsync(stream, processes.Select(ToState).ToArray(), GetJsonOptions());
}

static void DeleteStateIfSafe(string statePath)
{
    if (File.Exists(statePath)) File.Delete(statePath);
}

static string? GetOption(string[] values, string name)
{
    var prefix = $"--{name}=";
    var inline = values.FirstOrDefault(value => value.StartsWith(prefix, StringComparison.OrdinalIgnoreCase));
    if (inline is not null) return inline[prefix.Length..];
    var index = Array.FindIndex(values, value => string.Equals(value, $"--{name}", StringComparison.OrdinalIgnoreCase));
    return index >= 0 && index + 1 < values.Length ? values[index + 1] : null;
}

static int Fail(string message)
{
    Console.Error.WriteLine(message);
    return 2;
}

static JsonSerializerOptions GetJsonOptions() => new(JsonSerializerDefaults.Web) { WriteIndented = true };

internal sealed record SupervisorProcessState(string Role, int ProcessId, DateTimeOffset StartTime, int SessionId);
