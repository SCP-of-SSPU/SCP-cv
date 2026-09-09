using System.IO.Pipes;
using System.Text.Json;
using ScpCv.Contracts.Ipc;
using ScpCv.Contracts.Runtime;
using ScpCv.ControlHost.Ipc;

namespace ScpCv.Integration.Tests;

public sealed class RuntimeWorkerSessionTests
{
    [Fact]
    public async Task LostResultAcknowledgementReconnectsAndReplaysWithoutExecutingAgain()
    {
        var pipeName = $"scp-cv-session-test-{Guid.NewGuid():N}";
        var instanceId = Guid.NewGuid();
        var commandId = Guid.NewGuid();
        var claimToken = Guid.NewGuid();
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(15));
        var firstResult = new TaskCompletionSource<IpcFrameDto>(TaskCreationOptions.RunContinuationsAsynchronously);
        var replayedResult = new TaskCompletionSource<IpcFrameDto>(TaskCreationOptions.RunContinuationsAsynchronously);

        var serverTask = Task.Run(async () =>
        {
            await using (var first = CreateServer(pipeName))
            {
                await first.WaitForConnectionAsync(timeout.Token);
                await AcceptWorkerAsync(first, timeout.Token);
                var claim = await ReadAsync(first, timeout.Token);
                Assert.Equal("claim_request", claim.MessageType);
                await WriteAsync(first, Response(claim, "command_lease", new CommandLeaseDto
                {
                    CommandId = commandId,
                    TargetSequence = 1,
                    Command = "PLAY",
                    ClaimToken = claimToken,
                    OwnerEpoch = 7,
                    GroupEpoch = 3,
                    SourceGeneration = 11,
                    LeaseExpiresAt = DateTimeOffset.UtcNow.AddSeconds(30).ToString("O"),
                }, ownerEpoch: 7), timeout.Token);
                firstResult.SetResult(await ReadAsync(first, timeout.Token));
                // 模拟命令已经落地，但 ResultAccepted 在传输前连接丢失。
            }

            await using var second = CreateServer(pipeName);
            await second.WaitForConnectionAsync(timeout.Token);
            await AcceptWorkerAsync(second, timeout.Token);
            var replay = await ReadAsync(second, timeout.Token);
            replayedResult.SetResult(replay);
            await WriteAsync(second, Response(replay, "result_accepted", new ResultAcceptedDto
            {
                CommandId = commandId,
                Accepted = true,
                Duplicate = true,
            }, ownerEpoch: 7), timeout.Token);

            var nextClaim = await ReadAsync(second, timeout.Token);
            Assert.Equal("claim_request", nextClaim.MessageType);
            await WriteAsync(second, Response(nextClaim, "no_work", new NoWorkDto
            {
                Reason = "empty",
                RetryAfterMs = 1000,
            }, ownerEpoch: 7), timeout.Token);
        }, timeout.Token);

        var executionCount = 0;
        await using var session = CreateSession(pipeName, instanceId);
        var run = session.RunAsync((_, _) =>
        {
            Interlocked.Increment(ref executionCount);
            return Task.FromResult(new WorkerExecutionResult(
                "completed",
                "ok",
                JsonSerializer.SerializeToElement(new { source_generation = 11, playback_state = "playing" })));
        }, timeout.Token);

        var original = await firstResult.Task.WaitAsync(timeout.Token);
        var replayed = await replayedResult.Task.WaitAsync(timeout.Token);
        await serverTask;
        timeout.Cancel();
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => run);

        Assert.Equal(1, executionCount);
        Assert.Equal("command_result", original.MessageType);
        Assert.Equal(original.MessageId, replayed.MessageId);
        Assert.Equal(
            original.Payload.Deserialize<CommandResultDto>()!.ResultHash,
            replayed.Payload.Deserialize<CommandResultDto>()!.ResultHash);
    }

    [Fact]
    public async Task LostAudioEventAcknowledgementReusesMessageAndEventIdentityAfterReconnect()
    {
        var pipeName = $"scp-cv-session-test-{Guid.NewGuid():N}";
        var instanceId = Guid.NewGuid();
        var eventId = Guid.NewGuid();
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(15));
        var firstEvent = new TaskCompletionSource<IpcFrameDto>(TaskCreationOptions.RunContinuationsAsynchronously);
        var replayedEvent = new TaskCompletionSource<IpcFrameDto>(TaskCreationOptions.RunContinuationsAsynchronously);

        var serverTask = Task.Run(async () =>
        {
            await using (var first = CreateServer(pipeName))
            {
                await first.WaitForConnectionAsync(timeout.Token);
                await AcceptWorkerAsync(first, timeout.Token);
                firstEvent.SetResult(await ReadAsync(first, timeout.Token));
            }

            await using var second = CreateServer(pipeName);
            await second.WaitForConnectionAsync(timeout.Token);
            await AcceptWorkerAsync(second, timeout.Token);
            var replay = await ReadAsync(second, timeout.Token);
            replayedEvent.SetResult(replay);
            await WriteAsync(second, Response(replay, "event_accepted", new
            {
                accepted = true,
                event_id = eventId,
            }, ownerEpoch: 7), timeout.Token);
        }, timeout.Token);

        await using var session = CreateSession(pipeName, instanceId);
        await session.SendAudioFinishedAsync(new AudioFinishedDto
        {
            EventId = eventId,
            SourceId = 9,
            SourceGeneration = 12,
        }, timeout.Token);
        await serverTask;

        var original = await firstEvent.Task.WaitAsync(timeout.Token);
        var replayed = await replayedEvent.Task.WaitAsync(timeout.Token);
        Assert.Equal("audio_finished", original.MessageType);
        Assert.Equal(original.MessageId, replayed.MessageId);
        Assert.Equal(eventId, replayed.Payload.Deserialize<AudioFinishedDto>()!.EventId);
    }

    private static RuntimeWorkerSession CreateSession(string pipeName, Guid instanceId) => new(
        pipeName,
        new RuntimeWorkerIdentity(
            "audio",
            instanceId,
            new IpcTargetDto { Kind = "audio", Id = 1 },
            ["test"]));

    private static async Task AcceptWorkerAsync(Stream server, CancellationToken cancellationToken)
    {
        var hello = await ReadAsync(server, cancellationToken);
        Assert.Equal("hello", hello.MessageType);
        await WriteAsync(server, Response(hello, "welcome", new WelcomeDto
        {
            ServiceEpoch = 1,
            GroupEpoch = 3,
            GroupState = "armed",
            AcceptedCapabilities = ["test"],
        }, ownerEpoch: 7), cancellationToken);

        var ready = await ReadAsync(server, cancellationToken);
        Assert.Equal("worker_ready", ready.MessageType);
        await WriteAsync(server, Response(ready, "health_accepted", new { accepted = true }, ownerEpoch: 7), cancellationToken);
    }

    private static NamedPipeServerStream CreateServer(string pipeName) => new(
        pipeName,
        PipeDirection.InOut,
        1,
        PipeTransmissionMode.Byte,
        PipeOptions.Asynchronous | PipeOptions.CurrentUserOnly);

    private static IpcFrameDto Response<T>(
        IpcFrameDto request,
        string type,
        T payload,
        long ownerEpoch) => new()
    {
        MessageType = type,
        MessageId = Guid.NewGuid(),
        CorrelationId = request.MessageId,
        InstanceId = Guid.Empty,
        OwnerEpoch = ownerEpoch,
        Target = request.Target,
        Payload = JsonSerializer.SerializeToElement(payload),
    };

    private static Task WriteAsync(
        Stream stream,
        IpcFrameDto frame,
        CancellationToken cancellationToken) =>
        IpcFrameCodec.WritePayloadAsync(stream, JsonSerializer.SerializeToUtf8Bytes(frame), cancellationToken).AsTask();

    private static async Task<IpcFrameDto> ReadAsync(Stream stream, CancellationToken cancellationToken)
    {
        var bytes = await IpcFrameCodec.ReadPayloadAsync(stream, TimeSpan.FromSeconds(5), cancellationToken);
        return JsonSerializer.Deserialize<IpcFrameDto>(bytes)!;
    }
}
