using System.Buffers.Binary;
using System.Diagnostics;
using System.IO.Pipes;
using System.Text;
using ScpCv.Contracts.Ipc;
using ScpCv.ControlHost.Ipc;

namespace ScpCv.Integration.Tests;

public sealed class IpcFramingTests
{
    [Fact]
    public async Task FrameRoundTripUsesLittleEndianLengthAndHandlesPartialReads()
    {
        var payload = Encoding.UTF8.GetBytes("{\"message_type\":\"Hello\"}");
        await using var encoded = new MemoryStream();
        await IpcFrameCodec.WritePayloadAsync(encoded, payload);
        var bytes = encoded.ToArray();

        Assert.Equal(payload.Length, BinaryPrimitives.ReadInt32LittleEndian(bytes.AsSpan(0, sizeof(uint))));
        await using var partial = new ChunkedReadStream(bytes, maximumChunkSize: 2);
        var decoded = await IpcFrameCodec.ReadPayloadAsync(partial, IpcProtocol.FrameReadTimeout);
        Assert.Equal(payload, decoded);
    }

    [Theory]
    [InlineData(0)]
    [InlineData(IpcProtocol.MaximumFrameBytes + 1)]
    public async Task InvalidFrameLengthIsRejectedBeforePayloadAllocation(int length)
    {
        var prefix = new byte[sizeof(uint)];
        BinaryPrimitives.WriteUInt32LittleEndian(prefix, (uint)length);
        await using var stream = new MemoryStream(prefix);

        await Assert.ThrowsAsync<InvalidDataException>(async () =>
            await IpcFrameCodec.ReadPayloadAsync(stream, TimeSpan.FromSeconds(1)));
    }

    [Fact]
    public async Task TruncatedFrameFailsInsteadOfReturningPartialJson()
    {
        var bytes = new byte[sizeof(uint) + 2];
        BinaryPrimitives.WriteUInt32LittleEndian(bytes.AsSpan(0, sizeof(uint)), 5);
        await using var stream = new MemoryStream(bytes);

        await Assert.ThrowsAsync<EndOfStreamException>(async () =>
            await IpcFrameCodec.ReadPayloadAsync(stream, TimeSpan.FromSeconds(1)));
    }

    [Fact]
    public async Task FrameReadTimeoutIsEnforced()
    {
        await using var stream = new NeverCompletingReadStream();

        await Assert.ThrowsAsync<TimeoutException>(async () =>
            await IpcFrameCodec.ReadPayloadAsync(stream, TimeSpan.FromMilliseconds(100)));
    }

    [Fact]
    public async Task NamedPipeAcceptsOnlyRegisteredMatchingLocalProcess()
    {
        using var process = Process.GetCurrentProcess();
        var instanceId = Guid.NewGuid();
        var registry = new RegisteredProcessRegistry();
        registry.Register(new RegisteredProcessIdentity(
            process.Id,
            new DateTimeOffset(process.StartTime.ToUniversalTime(), TimeSpan.Zero),
            process.SessionId,
            "player",
            instanceId));
        var server = new NamedPipeServer(Guid.NewGuid(), process.SessionId, registry);
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(5));
        var accept = server.AcceptAsync("player", instanceId, timeout.Token);
        await using var client = new NamedPipeClientStream(
            ".",
            server.PipeName,
            PipeDirection.InOut,
            PipeOptions.Asynchronous);

        await client.ConnectAsync(timeout.Token);
        await using var connection = await accept;

        Assert.Equal(process.Id, connection.Identity.ProcessId);
        Assert.Equal(instanceId, connection.Identity.InstanceId);
        Assert.True(connection.Stream.IsConnected);
    }

    private sealed class ChunkedReadStream(byte[] bytes, int maximumChunkSize) : Stream
    {
        private readonly MemoryStream _inner = new(bytes);

        public override bool CanRead => true;
        public override bool CanSeek => false;
        public override bool CanWrite => false;
        public override long Length => _inner.Length;
        public override long Position { get => _inner.Position; set => throw new NotSupportedException(); }
        public override void Flush() => throw new NotSupportedException();
        public override int Read(byte[] buffer, int offset, int count) =>
            _inner.Read(buffer, offset, Math.Min(count, maximumChunkSize));
        public override ValueTask<int> ReadAsync(Memory<byte> buffer, CancellationToken cancellationToken = default) =>
            _inner.ReadAsync(buffer[..Math.Min(buffer.Length, maximumChunkSize)], cancellationToken);
        public override long Seek(long offset, SeekOrigin origin) => throw new NotSupportedException();
        public override void SetLength(long value) => throw new NotSupportedException();
        public override void Write(byte[] buffer, int offset, int count) => throw new NotSupportedException();

        protected override void Dispose(bool disposing)
        {
            if (disposing)
            {
                _inner.Dispose();
            }

            base.Dispose(disposing);
        }
    }

    private sealed class NeverCompletingReadStream : Stream
    {
        public override bool CanRead => true;
        public override bool CanSeek => false;
        public override bool CanWrite => false;
        public override long Length => throw new NotSupportedException();
        public override long Position { get => throw new NotSupportedException(); set => throw new NotSupportedException(); }
        public override void Flush() => throw new NotSupportedException();
        public override int Read(byte[] buffer, int offset, int count) => throw new NotSupportedException();
        public override async ValueTask<int> ReadAsync(
            Memory<byte> buffer,
            CancellationToken cancellationToken = default)
        {
            await Task.Delay(Timeout.InfiniteTimeSpan, cancellationToken);
            return 0;
        }

        public override long Seek(long offset, SeekOrigin origin) => throw new NotSupportedException();
        public override void SetLength(long value) => throw new NotSupportedException();
        public override void Write(byte[] buffer, int offset, int count) => throw new NotSupportedException();
    }
}
