using System.Diagnostics;
using System.Text.Json;
using ScpCv.Contracts.Ipc;
using ScpCv.Contracts.Runtime;
using ScpCv.PowerPointHost.Interop;
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

    var ready = hello with
    {
        MessageType = "worker_ready",
        MessageId = Guid.NewGuid(),
        OwnerEpoch = welcome.OwnerEpoch,
        Payload = JsonSerializer.SerializeToElement(new WorkerReadyDto
        {
            UiReady = true,
            Dependencies = new Dictionary<string, string>
            {
                ["sta"] = "ready",
                ["powerpoint.com"] = "ready",
                ["hwnd"] = "ready",
            },
            Detail = "office_sta_host_ready",
        }),
    };
    var accepted = await client.ExchangeAsync(ready, stop.Token);
    if (!string.Equals(accepted.MessageType, "health_accepted", StringComparison.OrdinalIgnoreCase) ||
        !accepted.Payload.TryGetProperty("accepted", out var acceptedValue) ||
        !acceptedValue.GetBoolean())
        throw new InvalidOperationException("ControlHost 未接受 PowerPointHost ready 状态。");

    // OfficeRequest 的派发/结果合同接线属于 T125；在此之前保持 STA 宿主和握手长连接，
    // 不以启动进程存活冒充 COM 放映已成功。
    await foreach (var frame in client.ReadUnsolicitedAsync(stop.Token).ConfigureAwait(false))
    {
        if (string.Equals(frame.MessageType, "shutdown_request", StringComparison.OrdinalIgnoreCase)) break;
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
