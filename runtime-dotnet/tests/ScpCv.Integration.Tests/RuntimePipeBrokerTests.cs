using System.Diagnostics;
using System.IO.Pipes;
using System.Text.Json;
using Microsoft.Extensions.Logging.Abstractions;
using ScpCv.Contracts.Ipc;
using ScpCv.ControlHost.Events;
using ScpCv.ControlHost.Ipc;
using ScpCv.Domain.Model;
using ScpCv.Infrastructure.Audio;
using ScpCv.Infrastructure.Commands;
using ScpCv.Infrastructure.Playback;
using ScpCv.Integration.Tests.Fixtures;

namespace ScpCv.Integration.Tests;

public sealed class RuntimePipeBrokerTests
{
    [Fact]
    public async Task WorkerHandshakeReturnsOwnerEpochAndSupportsHealthClaimAndWake()
    {
        await using var fixture = await ControlHostFixture.CreateAsync();
        var startRequest = Guid.NewGuid();
        var starting = await fixture.RuntimeAuthority.BeginStartAsync(startRequest);
        await fixture.RuntimeAuthority.ArmAsync(startRequest, starting.GroupEpoch);

        using var process = Process.GetCurrentProcess();
        var registry = new RegisteredProcessRegistry();
        var server = new NamedPipeServer(Guid.NewGuid(), process.SessionId, registry);
        using var broker = CreateBroker(fixture, registry, server);
        await broker.StartAsync(CancellationToken.None);

        var instanceId = Guid.NewGuid();
        registry.Register(CurrentIdentity(process, "player-1", instanceId));
        await using var client = await ConnectAsync(server.PipeName);

        await WriteAsync(client, Frame("hello", instanceId, 0, DisplayTarget(1), new HelloDto
        {
            Role = "player-1",
            ProcessId = process.Id,
            ProcessStartTime = UtcStart(process).ToString("O"),
            LogonSessionId = process.SessionId,
            Capabilities = ["image"],
        }));
        var welcome = await ReadAsync(client);

        Assert.Equal("welcome", welcome.MessageType);
        Assert.True(welcome.OwnerEpoch > 0);
        var welcomePayload = welcome.Payload.Deserialize<WelcomeDto>();
        Assert.NotNull(welcomePayload);
        Assert.Equal(starting.GroupEpoch, welcomePayload.GroupEpoch);
        Assert.Equal("armed", welcomePayload.GroupState);

        await WriteAsync(client, Frame("worker_ready", instanceId, welcome.OwnerEpoch, DisplayTarget(1), new WorkerReadyDto
        {
            UiReady = true,
            Dependencies = new Dictionary<string, string> { ["wpf"] = "ready" },
        }));
        var ready = await ReadAsync(client);
        Assert.Equal("health_accepted", ready.MessageType);
        Assert.True(ready.Payload.GetProperty("accepted").GetBoolean());

        await WriteAsync(client, Frame("claim_request", instanceId, welcome.OwnerEpoch, DisplayTarget(1), new ClaimRequestDto
        {
            GroupEpoch = starting.GroupEpoch,
        }));
        var noWork = await ReadAsync(client);
        Assert.Equal("no_work", noWork.MessageType);

        await broker.WakeAsync(new CommandWakeSignal(CommandTargetKind.Display, 1, 42));
        var wake = await ReadAsync(client);
        Assert.Equal("wake", wake.MessageType);
        Assert.Null(wake.CorrelationId);
        Assert.Equal(42, wake.Payload.Deserialize<WakeDto>()!.HighestSequence);

        await broker.StopAsync(CancellationToken.None);
    }

    [Fact]
    public async Task BrokerKeepsIndependentConcurrentPlayerConnections()
    {
        await using var fixture = await ControlHostFixture.CreateAsync();
        var startRequest = Guid.NewGuid();
        var starting = await fixture.RuntimeAuthority.BeginStartAsync(startRequest);
        await fixture.RuntimeAuthority.ArmAsync(startRequest, starting.GroupEpoch);

        var registry = new RegisteredProcessRegistry();
        using var process = Process.GetCurrentProcess();
        var server = new NamedPipeServer(Guid.NewGuid(), process.SessionId, registry);
        using var broker = CreateBroker(fixture, registry, server);
        await broker.StartAsync(CancellationToken.None);

        var firstId = Guid.NewGuid();
        registry.Register(CurrentIdentity(process, "player-1", firstId));
        await using var first = await ConnectAsync(server.PipeName);
        await WriteHelloAsync(first, process, "player-1", firstId, DisplayTarget(1));
        Assert.Equal("welcome", (await ReadAsync(first)).MessageType);

        var secondId = Guid.NewGuid();
        registry.Register(CurrentIdentity(process, "player-2", secondId));
        await using var second = await ConnectAsync(server.PipeName);
        await WriteHelloAsync(second, process, "player-2", secondId, DisplayTarget(2));
        Assert.Equal("welcome", (await ReadAsync(second)).MessageType);

        await broker.WakeAsync(new CommandWakeSignal(CommandTargetKind.Display, 1, 11));
        await broker.WakeAsync(new CommandWakeSignal(CommandTargetKind.Display, 2, 22));
        Assert.Equal(11, (await ReadAsync(first)).Payload.Deserialize<WakeDto>()!.HighestSequence);
        Assert.Equal(22, (await ReadAsync(second)).Payload.Deserialize<WakeDto>()!.HighestSequence);

        await broker.StopAsync(CancellationToken.None);
    }

    [Fact]
    public async Task SupervisorCanRegisterOnlyAnExistingMatchingChildProcess()
    {
        await using var fixture = await ControlHostFixture.CreateAsync();
        var registry = new RegisteredProcessRegistry();
        using var current = Process.GetCurrentProcess();
        var server = new NamedPipeServer(Guid.NewGuid(), current.SessionId, registry);
        using var broker = CreateBroker(fixture, registry, server);
        await broker.StartAsync(CancellationToken.None);

        var supervisorId = Guid.NewGuid();
        registry.Register(CurrentIdentity(current, "supervisor", supervisorId));
        await using var client = await ConnectAsync(server.PipeName);
        await WriteHelloAsync(client, current, "supervisor", supervisorId, target: null);
        Assert.Equal("welcome", (await ReadAsync(client)).MessageType);

        using var child = Process.Start(new ProcessStartInfo
        {
            FileName = "powershell.exe",
            ArgumentList = { "-NoProfile", "-Command", "Start-Sleep -Seconds 30" },
            UseShellExecute = false,
            CreateNoWindow = true,
        })!;
        try
        {
            var childId = Guid.NewGuid();
            var valid = Frame("register_process", supervisorId, 0, null, new RegisterProcessDto
            {
                Role = "audio",
                ProcessId = child.Id,
                ProcessStartTime = UtcStart(child).ToString("O"),
                LogonSessionId = child.SessionId,
                InstanceId = childId,
            });
            await WriteAsync(client, valid);
            var accepted = (await ReadAsync(client)).Payload.Deserialize<RegistrationResultDto>();
            Assert.NotNull(accepted);
            Assert.True(accepted.Accepted);
            Assert.True(registry.TryGet(child.Id, out var registered));
            Assert.Equal(childId, registered!.InstanceId);

            await WriteAsync(client, Frame("register_process", supervisorId, 0, null, new RegisterProcessDto
            {
                Role = "audio",
                ProcessId = child.Id,
                ProcessStartTime = UtcStart(child).AddSeconds(1).ToString("O"),
                LogonSessionId = child.SessionId,
                InstanceId = Guid.NewGuid(),
            }));
            var rejected = (await ReadAsync(client)).Payload.Deserialize<RegistrationResultDto>();
            Assert.NotNull(rejected);
            Assert.False(rejected.Accepted);
            Assert.Equal("process_identity_mismatch", rejected.Reason);
        }
        finally
        {
            if (!child.HasExited)
            {
                child.Kill(entireProcessTree: true);
                await child.WaitForExitAsync();
            }
        }

        await broker.StopAsync(CancellationToken.None);
    }

    private static RuntimePipeBroker CreateBroker(
        ControlHostFixture fixture,
        RegisteredProcessRegistry registry,
        NamedPipeServer server)
    {
        var commandCoordinator = new CommandCoordinator(fixture.Commands, new NullCommandWakeNotifier());
        var runtime = new RuntimeStateService(fixture.Database, fixture.Writes, commandCoordinator, fixture.TimeProvider);
        var audio = new BackgroundAudioService(fixture.Database, fixture.Writes, commandCoordinator, fixture.TimeProvider);
        var events = new SseEventHub(runtime, audio, new SseEventStreamOptions());
        var projections = new RuntimeProjectionPublisher(fixture.Writes, events, fixture.TimeProvider);
        var leases = new CommandLeaseService(
            fixture.Commands,
            fixture.RuntimeAuthority,
            fixture.Database,
            fixture.Writes,
            fixture.TimeProvider);
        var dispatcher = new RuntimeMessageDispatcher(
            leases,
            new CommandResultService(fixture.Commands),
            projections);
        return new RuntimePipeBroker(
            server,
            registry,
            dispatcher,
            fixture.RuntimeAuthority,
            NullLogger<RuntimePipeBroker>.Instance);
    }

    private static RegisteredProcessIdentity CurrentIdentity(Process process, string role, Guid instanceId) =>
        new(process.Id, UtcStart(process), process.SessionId, role, instanceId);

    private static DateTimeOffset UtcStart(Process process) =>
        new(process.StartTime.ToUniversalTime(), TimeSpan.Zero);

    private static IpcTargetDto DisplayTarget(int id) => new() { Kind = "display", Id = id };

    private static IpcFrameDto Frame<T>(string type, Guid instanceId, long ownerEpoch, IpcTargetDto? target, T payload) => new()
    {
        MessageType = type,
        MessageId = Guid.NewGuid(),
        InstanceId = instanceId,
        OwnerEpoch = ownerEpoch,
        Target = target,
        Payload = JsonSerializer.SerializeToElement(payload),
    };

    private static async Task<NamedPipeClientStream> ConnectAsync(string pipeName)
    {
        var client = new NamedPipeClientStream(".", pipeName, PipeDirection.InOut, PipeOptions.Asynchronous);
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(5));
        await client.ConnectAsync(timeout.Token);
        return client;
    }

    private static Task WriteHelloAsync(
        Stream stream,
        Process process,
        string role,
        Guid instanceId,
        IpcTargetDto? target) =>
        WriteAsync(stream, Frame("hello", instanceId, 0, target, new HelloDto
        {
            Role = role,
            ProcessId = process.Id,
            ProcessStartTime = UtcStart(process).ToString("O"),
            LogonSessionId = process.SessionId,
        }));

    private static Task WriteAsync(Stream stream, IpcFrameDto frame) =>
        IpcFrameCodec.WritePayloadAsync(stream, JsonSerializer.SerializeToUtf8Bytes(frame)).AsTask();

    private static async Task<IpcFrameDto> ReadAsync(Stream stream)
    {
        var bytes = await IpcFrameCodec.ReadPayloadAsync(stream, TimeSpan.FromSeconds(5));
        return JsonSerializer.Deserialize<IpcFrameDto>(bytes)
            ?? throw new InvalidDataException("Broker 返回空 IPC 帧。");
    }
}
