using ScpCv.AudioWorker.Audio;
using ScpCv.Contracts.Ipc;
using ScpCv.Contracts.Runtime;

if (!OperatingSystem.IsWindows())
{
    Console.Error.WriteLine("AudioWorker 仅支持 Windows x64 播放主机。");
    return 2;
}

var pipeName = Option(args, "pipe-name");
var startGate = Option(args, "start-gate");
var instanceId = Guid.TryParse(Option(args, "instance-id"), out var parsedInstance)
    ? parsedInstance
    : Guid.NewGuid();
using var stop = new CancellationTokenSource();
Console.CancelKeyPress += (_, eventArgs) => { eventArgs.Cancel = true; stop.Cancel(); };
await using var audio = new VlcAudioAdapter();
var executor = new AudioCommandExecutor(audio);

if (string.IsNullOrWhiteSpace(pipeName))
{
    Console.WriteLine("AudioWorker ready (standalone diagnostics)");
    try { await Task.Delay(Timeout.InfiniteTimeSpan, stop.Token); } catch (OperationCanceledException) { }
    return 0;
}

await using var session = new RuntimeWorkerSession(pipeName, new RuntimeWorkerIdentity(
    "audio",
    instanceId,
    new IpcTargetDto { Kind = "audio", Id = 1 },
    ["libvlc", "audio_finished"]));
audio.Finished += (_, finished) => _ = NotifyFinishedAsync(session, finished, stop.Token);
try
{
    await RuntimeStartGate.WaitAsync(startGate, cancellationToken: stop.Token);
    await session.RunAsync(executor.ExecuteAsync, stop.Token);
    return 0;
}
catch (OperationCanceledException) when (stop.IsCancellationRequested)
{
    return 0;
}

static async Task NotifyFinishedAsync(
    RuntimeWorkerSession session,
    AudioFinishedEventArgs finished,
    CancellationToken cancellationToken)
{
    try
    {
        await session.SendAudioFinishedAsync(new AudioFinishedDto
        {
            EventId = finished.EventId,
            SourceId = finished.SourceId,
            SourceGeneration = finished.SourceGeneration,
        }, cancellationToken);
    }
    catch (Exception exception) when (exception is IOException or InvalidOperationException)
    {
        Console.Error.WriteLine($"AudioFinished 上报失败：{exception.Message}");
    }
    catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
    {
        // Worker 退出时取消尚未确认的自然结束事件，不让后台任务形成未观察异常。
    }
}

static string? Option(string[] values, string name)
{
    var prefix = $"--{name}=";
    var inline = values.FirstOrDefault(value => value.StartsWith(prefix, StringComparison.OrdinalIgnoreCase));
    if (inline is not null) return inline[prefix.Length..];
    var index = Array.FindIndex(values, value => string.Equals(value, $"--{name}", StringComparison.OrdinalIgnoreCase));
    return index >= 0 && index + 1 < values.Length ? values[index + 1] : null;
}
