using ScpCv.AudioWorker.Audio;

if (!OperatingSystem.IsWindows())
{
    Console.Error.WriteLine("AudioWorker 仅支持 Windows x64 播放主机。");
    return;
}

using var stop = new CancellationTokenSource();
Console.CancelKeyPress += (_, args) => { args.Cancel = true; stop.Cancel(); };
await using var audio = new VlcAudioAdapter();
audio.Finished += (_, finished) => Console.WriteLine($"audio_finished source_id={finished.SourceId} source_generation={finished.SourceGeneration}");
Console.WriteLine("AudioWorker ready");
try { await Task.Delay(Timeout.InfiniteTimeSpan, stop.Token); } catch (OperationCanceledException) { }
