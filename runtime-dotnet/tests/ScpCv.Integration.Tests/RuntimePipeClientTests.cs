using System.IO.Pipes;
using System.Text.Json;
using ScpCv.Contracts.Ipc;
using ScpCv.Contracts.Runtime;
using ScpCv.ControlHost.Ipc;

namespace ScpCv.Integration.Tests;

public sealed class RuntimePipeClientTests
{
    [Fact]
    public async Task UnsolicitedWakeCannotBeMistakenForRequestResponse()
    {
        var pipeName = $"scp-cv-client-test-{Guid.NewGuid():N}";
        await using var server = CreateServer(pipeName);
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(5));
        var serverTask = Task.Run(async () =>
        {
            await server.WaitForConnectionAsync(timeout.Token);
            var request = await ReadAsync(server, timeout.Token);
            await WriteAsync(server, Frame("wake", null, new WakeDto { HighestSequence = 9 }), timeout.Token);
            await WriteAsync(server, Frame("no_work", request.MessageId, new NoWorkDto { Reason = "empty" }), timeout.Token);
        }, timeout.Token);

        await using var client = new RuntimePipeClient(pipeName);
        await client.ConnectAsync(timeout.Token);
        var exchange = client.ExchangeAsync(Frame("claim_request", null, new ClaimRequestDto { GroupEpoch = 1 }), timeout.Token);
        var wake = await client.ReadUnsolicitedAsync(timeout.Token).FirstAsync(timeout.Token);
        var response = await exchange;

        Assert.Equal("wake", wake.MessageType);
        Assert.Equal(9, wake.Payload.Deserialize<WakeDto>()!.HighestSequence);
        Assert.Equal("no_work", response.MessageType);
        await serverTask;
    }

    [Fact]
    public async Task ConcurrentExchangesAreMatchedByCorrelationIdWhenResponsesAreReversed()
    {
        var pipeName = $"scp-cv-client-test-{Guid.NewGuid():N}";
        await using var server = CreateServer(pipeName);
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(5));
        var serverTask = Task.Run(async () =>
        {
            await server.WaitForConnectionAsync(timeout.Token);
            var first = await ReadAsync(server, timeout.Token);
            var second = await ReadAsync(server, timeout.Token);
            await WriteAsync(server, Frame("reply-2", second.MessageId, new { }), timeout.Token);
            await WriteAsync(server, Frame("reply-1", first.MessageId, new { }), timeout.Token);
        }, timeout.Token);

        await using var client = new RuntimePipeClient(pipeName);
        await client.ConnectAsync(timeout.Token);
        var firstRequest = Frame("request-1", null, new { });
        var secondRequest = Frame("request-2", null, new { });
        var firstExchange = client.ExchangeAsync(firstRequest, timeout.Token);
        var secondExchange = client.ExchangeAsync(secondRequest, timeout.Token);

        Assert.Equal("reply-1", (await firstExchange).MessageType);
        Assert.Equal("reply-2", (await secondExchange).MessageType);
        await serverTask;
    }

    private static NamedPipeServerStream CreateServer(string pipeName) => new(
        pipeName,
        PipeDirection.InOut,
        1,
        PipeTransmissionMode.Byte,
        PipeOptions.Asynchronous | PipeOptions.CurrentUserOnly);

    private static IpcFrameDto Frame<T>(string type, Guid? correlationId, T payload) => new()
    {
        MessageType = type,
        MessageId = Guid.NewGuid(),
        CorrelationId = correlationId,
        InstanceId = Guid.NewGuid(),
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
