using System.Diagnostics;
using System.IO;
using System.Text.Json;
using ScpCv.Contracts.Ipc;
using ScpCv.Contracts.Runtime;
using ScpCv.PowerPointHost.Interop;
using ScpCv.PowerPointHost.Ownership;
using ScpCv.PowerPointHost.Sta;

if (!OperatingSystem.IsWindows())
{
    Console.Error.WriteLine("PowerPointHost 仅支持 Windows x64 交互桌面。");
    return 2;
}

var pipeName = Option(args, "pipe-name");
var instanceId = Guid.TryParse(Option(args, "instance-id"), out var parsed)
    ? parsed
    : Guid.NewGuid();
using var stop = new CancellationTokenSource();
Console.CancelKeyPress += (_, eventArgs) => { eventArgs.Cancel = true; stop.Cancel(); };

if (string.IsNullOrWhiteSpace(pipeName))
{
    Console.WriteLine("PowerPointHost ready (standalone diagnostics)");
    try { await Task.Delay(Timeout.InfiniteTimeSpan, stop.Token); } catch (OperationCanceledException) { }
    return 0;
}

await using var client = new RuntimePipeClient(pipeName);
using var sta = new OfficeStaDispatcher();
using var office = new PowerPointComAdapter(sta);
try
{
    await client.ConnectAsync(stop.Token);
    using var process = Process.GetCurrentProcess();
    var hello = new IpcFrameDto
    {
        MessageType = "hello",
        MessageId = Guid.NewGuid(),
        InstanceId = instanceId,
        Payload = JsonSerializer.SerializeToElement(new HelloDto
        {
            Role = "office",
            ProcessId = process.Id,
            ProcessStartTime = UtcStart(process).ToString("O"),
            LogonSessionId = process.SessionId,
            Capabilities = ["sta", "powerpoint.com", "hwnd", "office_operation_dedup"],
        }),
    };
    var welcome = await client.ExchangeAsync(hello, stop.Token);
    if (!string.Equals(welcome.MessageType, "welcome", StringComparison.OrdinalIgnoreCase))
        throw new InvalidOperationException($"ControlHost 拒绝 PowerPointHost 握手：{welcome.MessageType}");

    using var ownership = new PowerPointOwnershipGuard(
        "Global\\SCP-cv.PowerPointHost",
        welcome.OwnerEpoch);
    if (!ownership.TryAcquire(TimeSpan.Zero))
        throw new InvalidOperationException("已有 PowerPointHost 持有唯一 Office 槽位。");
    var welcomePayload = welcome.Payload.Deserialize<WelcomeDto>()
        ?? throw new InvalidDataException("Welcome payload 无效。");
    var executor = new PowerPointOfficeRequestExecutor(office, welcomePayload.GroupEpoch, welcome.OwnerEpoch, opened =>
    {
        if (opened.ProcessId <= 0) return;
        try
        {
            using var process = Process.GetProcessById(opened.ProcessId);
            ownership.RegisterOwnedProcess(process);
        }
        catch (Exception exception)
        {
            Console.Error.WriteLine($"无法登记 PowerPoint 进程证据：{exception.Message}");
        }
    });

    var powerPointAvailable = PowerPointComAdapter.IsAvailable;
    var ready = hello with
    {
        MessageType = "worker_ready",
        MessageId = Guid.NewGuid(),
        OwnerEpoch = welcome.OwnerEpoch,
        Payload = JsonSerializer.SerializeToElement(new WorkerReadyDto
        {
            UiReady = powerPointAvailable,
            Dependencies = new Dictionary<string, string>
            {
                ["sta"] = "ready",
                ["powerpoint.com"] = powerPointAvailable ? "ready" : "unavailable",
                ["hwnd"] = "ready",
            },
            Detail = powerPointAvailable ? "office_sta_host_ready" : "powerpoint_com_unavailable",
        }),
    };
    var accepted = await client.ExchangeAsync(ready, stop.Token);
    if (!string.Equals(accepted.MessageType, "health_accepted", StringComparison.OrdinalIgnoreCase) ||
        !accepted.Payload.TryGetProperty("accepted", out var acceptedValue) ||
        !acceptedValue.GetBoolean())
        throw new InvalidOperationException("ControlHost 未接受 PowerPointHost ready 状态。");

    await foreach (var frame in client.ReadUnsolicitedAsync(stop.Token).ConfigureAwait(false))
    {
        if (string.Equals(frame.MessageType, "shutdown_request", StringComparison.OrdinalIgnoreCase)) break;
        if (!string.Equals(frame.MessageType, "office_request", StringComparison.OrdinalIgnoreCase)) continue;

        var request = frame.Payload.Deserialize<OfficeRequestDto>()
            ?? throw new InvalidDataException("OfficeRequest payload 无效。");
        var result = await executor.ExecuteAsync(request, stop.Token).ConfigureAwait(false);
        var response = new IpcFrameDto
        {
            MessageType = "office_result",
            MessageId = Guid.NewGuid(),
            CorrelationId = frame.MessageId,
            InstanceId = instanceId,
            OwnerEpoch = welcome.OwnerEpoch,
            Payload = JsonSerializer.SerializeToElement(result),
        };
        var acceptedResult = await client.ExchangeAsync(response, stop.Token).ConfigureAwait(false);
        if (!string.Equals(acceptedResult.MessageType, "office_result_accepted", StringComparison.OrdinalIgnoreCase))
            throw new InvalidOperationException($"ControlHost 未接受 OfficeResult：{acceptedResult.MessageType}");
    }

    return 0;
}
catch (OperationCanceledException) when (stop.IsCancellationRequested)
{
    return 0;
}
catch (Exception exception)
{
    Console.Error.WriteLine($"PowerPointHost 失败：{exception.Message}");
    return 1;
}

static string? Option(string[] values, string name)
{
    var prefix = $"--{name}=";
    var inline = values.FirstOrDefault(value => value.StartsWith(prefix, StringComparison.OrdinalIgnoreCase));
    if (inline is not null) return inline[prefix.Length..];
    var index = Array.FindIndex(values, value => string.Equals(value, $"--{name}", StringComparison.OrdinalIgnoreCase));
    return index >= 0 && index + 1 < values.Length ? values[index + 1] : null;
}

static DateTimeOffset UtcStart(Process process) =>
    new(process.StartTime.ToUniversalTime(), TimeSpan.Zero);
