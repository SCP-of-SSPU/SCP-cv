using System.Buffers.Binary;
using System.Collections.Concurrent;
using System.Diagnostics;
using System.IO.Pipes;
using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;
using ScpCv.Contracts.Ipc;

namespace ScpCv.ControlHost.Ipc;

public static class IpcFrameCodec
{
    public static async ValueTask<byte[]> ReadPayloadAsync(
        Stream stream,
        TimeSpan timeout,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(stream);
        ArgumentOutOfRangeException.ThrowIfLessThanOrEqual(timeout, TimeSpan.Zero);
        using var timeoutSource = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        timeoutSource.CancelAfter(timeout);
        try
        {
            var prefix = new byte[sizeof(uint)];
            await ReadExactlyAsync(stream, prefix, timeoutSource.Token).ConfigureAwait(false);
            var length = BinaryPrimitives.ReadUInt32LittleEndian(prefix);
            if (length is 0 or > IpcProtocol.MaximumFrameBytes)
            {
                throw new InvalidDataException(
                    $"IPC 帧长度必须在 1..{IpcProtocol.MaximumFrameBytes} 字节之间，实际为 {length}。");
            }

            var payload = new byte[(int)length];
            await ReadExactlyAsync(stream, payload, timeoutSource.Token).ConfigureAwait(false);
            return payload;
        }
        catch (OperationCanceledException exception) when (!cancellationToken.IsCancellationRequested)
        {
            throw new TimeoutException($"读取 IPC 帧超过 {timeout.TotalSeconds:0.###} 秒。", exception);
        }
    }

    public static async ValueTask WritePayloadAsync(
        Stream stream,
        ReadOnlyMemory<byte> payload,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(stream);
        if (payload.Length is 0 or > IpcProtocol.MaximumFrameBytes)
        {
            throw new InvalidDataException(
                $"IPC 帧长度必须在 1..{IpcProtocol.MaximumFrameBytes} 字节之间，实际为 {payload.Length}。");
        }

        var prefix = new byte[sizeof(uint)];
        BinaryPrimitives.WriteUInt32LittleEndian(prefix, (uint)payload.Length);
        await stream.WriteAsync(prefix, cancellationToken).ConfigureAwait(false);
        await stream.WriteAsync(payload, cancellationToken).ConfigureAwait(false);
        await stream.FlushAsync(cancellationToken).ConfigureAwait(false);
    }

    private static async ValueTask ReadExactlyAsync(
        Stream stream,
        Memory<byte> destination,
        CancellationToken cancellationToken)
    {
        var offset = 0;
        while (offset < destination.Length)
        {
            var bytesRead = await stream.ReadAsync(destination[offset..], cancellationToken).ConfigureAwait(false);
            if (bytesRead == 0)
            {
                throw new EndOfStreamException("IPC 帧在完整读取前已断开。");
            }

            offset += bytesRead;
        }
    }
}

public sealed record RegisteredProcessIdentity(
    int ProcessId,
    DateTimeOffset ProcessStartTime,
    int LogonSessionId,
    string Role,
    Guid InstanceId);

public interface IRegisteredProcessRegistry
{
    void Register(RegisteredProcessIdentity identity);
    bool TryGet(int processId, out RegisteredProcessIdentity? identity);
}

public sealed class RegisteredProcessRegistry : IRegisteredProcessRegistry
{
    private readonly ConcurrentDictionary<int, RegisteredProcessIdentity> _processes = new();

    public void Register(RegisteredProcessIdentity identity)
    {
        ArgumentNullException.ThrowIfNull(identity);
        _processes[identity.ProcessId] = identity;
    }

    public bool Remove(int processId, DateTimeOffset processStartTime) =>
        _processes.TryGetValue(processId, out var existing) &&
        existing.ProcessStartTime == processStartTime &&
        _processes.TryRemove(new KeyValuePair<int, RegisteredProcessIdentity>(processId, existing));

    public bool TryGet(int processId, out RegisteredProcessIdentity? identity) =>
        _processes.TryGetValue(processId, out identity);
}

public sealed class VerifiedNamedPipeConnection(
    NamedPipeServerStream stream,
    RegisteredProcessIdentity identity) : IAsyncDisposable
{
    public NamedPipeServerStream Stream { get; } = stream;
    public RegisteredProcessIdentity Identity { get; } = identity;

    public ValueTask DisposeAsync() => Stream.DisposeAsync();
}

public sealed partial class NamedPipeServer(
    Guid installationId,
    int logonSessionId,
    IRegisteredProcessRegistry processRegistry)
{
    private const int FirstPipeInstanceFlag = 0x0008_0000;
    private int _firstInstance = 1;

    public string PipeName { get; } = $"scp-cv.{installationId:N}.{logonSessionId}.runtime.v1";

    public async Task<VerifiedNamedPipeConnection> AcceptAsync(
        string expectedRole,
        Guid expectedInstanceId,
        CancellationToken cancellationToken = default)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(expectedRole);
        if (!OperatingSystem.IsWindows())
        {
            throw new PlatformNotSupportedException("SCP-cv Named Pipe server 仅支持 Windows。");
        }

        var stream = CreateStream();
        try
        {
            await stream.WaitForConnectionAsync(cancellationToken).ConfigureAwait(false);
            var identity = VerifyClient(stream, expectedRole, expectedInstanceId);
            return new VerifiedNamedPipeConnection(stream, identity);
        }
        catch
        {
            await stream.DisposeAsync().ConfigureAwait(false);
            throw;
        }
    }

    public async Task<NamedPipeServerStream> AcceptAsync(CancellationToken cancellationToken = default)
    {
        if (!OperatingSystem.IsWindows())
        {
            throw new PlatformNotSupportedException("SCP-cv Named Pipe server 仅支持 Windows。");
        }

        var stream = CreateStream();
        try
        {
            await stream.WaitForConnectionAsync(cancellationToken).ConfigureAwait(false);
            return stream;
        }
        catch
        {
            await stream.DisposeAsync().ConfigureAwait(false);
            throw;
        }
    }

    public RegisteredProcessIdentity VerifyClient(
        NamedPipeServerStream stream,
        string expectedRole,
        Guid expectedInstanceId) =>
        VerifyClientIdentity(stream, expectedRole, expectedInstanceId);

    private NamedPipeServerStream CreateStream()
    {
        var firstInstance = Interlocked.Exchange(ref _firstInstance, 0) == 1;
        return
        new(
            pipeName: PipeName,
            direction: PipeDirection.InOut,
            maxNumberOfServerInstances: NamedPipeServerStream.MaxAllowedServerInstances,
            transmissionMode: PipeTransmissionMode.Byte,
            options: PipeOptions.Asynchronous | PipeOptions.CurrentUserOnly | (firstInstance ? (PipeOptions)FirstPipeInstanceFlag : 0),
            inBufferSize: 64 * 1024,
            outBufferSize: 64 * 1024);
    }

    private RegisteredProcessIdentity VerifyClientIdentity(
        NamedPipeServerStream stream,
        string expectedRole,
        Guid expectedInstanceId)
    {
        if (!GetNamedPipeClientProcessId(stream.SafePipeHandle, out var rawProcessId) || rawProcessId > int.MaxValue)
        {
            throw CreateIdentityError("无法取得本机管道客户端 PID");
        }

        var processId = (int)rawProcessId;
        if (!ProcessIdToSessionId(rawProcessId, out var rawSessionId) || rawSessionId > int.MaxValue)
        {
            throw CreateIdentityError("无法取得本机管道客户端登录会话");
        }

        using var process = Process.GetProcessById(processId);
        var actualStartTime = new DateTimeOffset(process.StartTime.ToUniversalTime(), TimeSpan.Zero);
        if (!processRegistry.TryGet(processId, out var registered) || registered is null)
        {
            // Supervisor 是唯一允许由 ControlHost 启动后首次 bootstrap 的角色；
            // 其余 Worker 必须先由已认证 Supervisor 登记，避免同用户任意进程冒充。
            var executableName = Path.GetFileNameWithoutExtension(process.MainModule?.FileName ?? string.Empty);
            if (!string.Equals(expectedRole, "supervisor", StringComparison.Ordinal) ||
                !string.Equals(executableName, "ScpCv.Supervisor", StringComparison.OrdinalIgnoreCase) ||
                (int)rawSessionId != logonSessionId)
            {
                throw CreateIdentityError("客户端进程未由 Supervisor 登记");
            }

            registered = new RegisteredProcessIdentity(
                processId,
                actualStartTime,
                (int)rawSessionId,
                expectedRole,
                expectedInstanceId);
            processRegistry.Register(registered);
        }

        if (registered.ProcessStartTime != actualStartTime ||
            registered.LogonSessionId != (int)rawSessionId ||
            registered.LogonSessionId != logonSessionId ||
            !string.Equals(registered.Role, expectedRole, StringComparison.Ordinal) ||
            registered.InstanceId != expectedInstanceId)
        {
            throw CreateIdentityError("客户端 PID/start-time/session/role/instance 身份不匹配");
        }

        return registered;
    }

    private static UnauthorizedAccessException CreateIdentityError(string reason) =>
        new($"拒绝 Named Pipe 客户端：{reason}。");

    [LibraryImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static partial bool GetNamedPipeClientProcessId(SafePipeHandle pipe, out uint clientProcessId);

    [LibraryImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static partial bool ProcessIdToSessionId(uint processId, out uint sessionId);
}
