using System.Diagnostics;
using System.IO.Pipes;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
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
    public async Task AudioFinishedIsAcceptedAndDeduplicatedThroughBrokerAfterServiceRestart()
    {
        await using var fixture = await ControlHostFixture.CreateAsync();
        var coordinator = new CommandCoordinator(fixture.Commands, new NullCommandWakeNotifier());
        var setupAudio = new BackgroundAudioService(fixture.Database, fixture.Writes, coordinator, fixture.TimeProvider);
        var (firstSourceId, secondSourceId) = await SeedAudioSourcesAsync(fixture);
        await setupAudio.SetPlaylistAsync([firstSourceId, secondSourceId]);
        await setupAudio.PlaySourceAsync(firstSourceId);
        await fixture.Writes.ExecuteAsync(async (database, cancellationToken) =>
        {
            var state = await database.BackgroundAudioStates.SingleAsync(cancellationToken);
            state.PlaybackState = PlaybackState.Playing;
        });

        var startRequest = Guid.NewGuid();
        var starting = await fixture.RuntimeAuthority.BeginStartAsync(startRequest);
        await fixture.RuntimeAuthority.ArmAsync(startRequest, starting.GroupEpoch);
        using var process = Process.GetCurrentProcess();
        var registry = new RegisteredProcessRegistry();
        var server = new NamedPipeServer(Guid.NewGuid(), process.SessionId, registry);
        using var broker = CreateBroker(fixture, registry, server);
        await broker.StartAsync(CancellationToken.None);

        var instanceId = Guid.NewGuid();
        registry.Register(CurrentIdentity(process, "audio", instanceId));
        await using var client = await ConnectAsync(server.PipeName);
        await WriteHelloAsync(client, process, "audio", instanceId, new IpcTargetDto { Kind = "audio", Id = 1 });
        var welcome = await ReadAsync(client);
        await WriteAsync(client, Frame("worker_ready", instanceId, welcome.OwnerEpoch, new IpcTargetDto { Kind = "audio", Id = 1 }, new WorkerReadyDto
        {
            UiReady = true,
            Dependencies = new Dictionary<string, string> { ["libvlc"] = "ready" },
        }));
        Assert.Equal("health_accepted", (await ReadAsync(client)).MessageType);

        var eventId = Guid.NewGuid();
        var finished = Frame("audio_finished", instanceId, welcome.OwnerEpoch, new IpcTargetDto { Kind = "audio", Id = 1 }, new AudioFinishedDto
        {
            EventId = eventId,
            SourceId = firstSourceId,
            SourceGeneration = 1,
        });
        await WriteAsync(client, finished);
        Assert.Equal("event_accepted", (await ReadAsync(client)).MessageType);
        await WriteAsync(client, finished with { MessageId = Guid.NewGuid() });
        Assert.Equal("event_accepted", (await ReadAsync(client)).MessageType);

        await using var check = fixture.Database.CreateDbContext();
        Assert.Equal(secondSourceId, (await check.BackgroundAudioStates.SingleAsync()).CurrentSourceId);
        Assert.Single(await check.CommandRecords.Where(item => item.TriggerEventId == eventId).ToArrayAsync());
        await broker.StopAsync(CancellationToken.None);
    }

    [Fact]
    public async Task RuntimeReadinessRequiresEveryWorkerRoleInTheCurrentStartingEpoch()
    {
        await using var fixture = await ControlHostFixture.CreateAsync();
        var starting = await fixture.RuntimeAuthority.BeginStartAsync(Guid.NewGuid());
        using var process = Process.GetCurrentProcess();
        var registry = new RegisteredProcessRegistry();
        var server = new NamedPipeServer(Guid.NewGuid(), process.SessionId, registry);
        using var broker = CreateBroker(fixture, registry, server);
        await broker.StartAsync(CancellationToken.None);

        var before = await broker.WaitForRuntimeReadyAsync(starting.GroupEpoch, TimeSpan.FromMilliseconds(100));
        Assert.False(before.Ready);
        Assert.Equal(6, before.MissingRoles.Count);

        var clients = new List<NamedPipeClientStream>();
        NamedPipeClientStream? officeClient = null;
        IpcFrameDto? officeWelcome = null;
        Guid officeInstanceId = Guid.Empty;
        try
        {
            foreach (var role in new[] { "player-1", "player-2", "player-3", "player-4", "audio", "office" })
            {
                var instanceId = Guid.NewGuid();
                registry.Register(CurrentIdentity(process, role, instanceId));
                var client = await ConnectAsync(server.PipeName);
                clients.Add(client);
                var target = role.StartsWith("player-", StringComparison.Ordinal)
                    ? DisplayTarget(int.Parse(role[7..], System.Globalization.CultureInfo.InvariantCulture))
                    : role == "audio" ? new IpcTargetDto { Kind = "audio", Id = 1 } : null;
                await WriteHelloAsync(client, process, role, instanceId, target);
                var welcome = await ReadAsync(client);
                Assert.Equal("starting", welcome.Payload.Deserialize<WelcomeDto>()!.GroupState);
                var initiallyReady = role != "office";
                await WriteAsync(client, Frame("worker_ready", instanceId, welcome.OwnerEpoch, target, new WorkerReadyDto
                {
                    UiReady = initiallyReady,
                    Dependencies = new Dictionary<string, string> { [role] = "ready" },
                }));
                var accepted = await ReadAsync(client);
                Assert.True(accepted.Payload.GetProperty("accepted").GetBoolean());
                if (role == "office")
                {
                    officeClient = client;
                    officeWelcome = welcome;
                    officeInstanceId = instanceId;
                }
            }

            var missingOffice = await broker.WaitForRuntimeReadyAsync(starting.GroupEpoch, TimeSpan.FromMilliseconds(100));
            Assert.False(missingOffice.Ready);
            Assert.Equal(["office"], missingOffice.MissingRoles);

            Assert.NotNull(officeClient);
            Assert.NotNull(officeWelcome);
            await WriteAsync(officeClient, Frame("worker_ready", officeInstanceId, officeWelcome.OwnerEpoch, null, new WorkerReadyDto
            {
                UiReady = true,
                Dependencies = new Dictionary<string, string> { ["office"] = "ready" },
            }));
            Assert.True((await ReadAsync(officeClient)).Payload.GetProperty("accepted").GetBoolean());

            var ready = await broker.WaitForRuntimeReadyAsync(starting.GroupEpoch, TimeSpan.FromSeconds(2));
            Assert.True(ready.Ready);
            Assert.Empty(ready.MissingRoles);

            var staleEpoch = await broker.WaitForRuntimeReadyAsync(starting.GroupEpoch + 1, TimeSpan.FromMilliseconds(100));
            Assert.False(staleEpoch.Ready);
            Assert.Equal(6, staleEpoch.MissingRoles.Count);

            await officeClient.DisposeAsync();
            for (var attempt = 0; attempt < 50 && broker.GetRuntimeReadiness(starting.GroupEpoch).Ready; attempt++)
            {
                await Task.Delay(20);
            }
            var disconnected = broker.GetRuntimeReadiness(starting.GroupEpoch);
            Assert.False(disconnected.Ready);
            Assert.Contains("office", disconnected.MissingRoles);
        }
        finally
        {
            foreach (var client in clients) await client.DisposeAsync();
            await broker.StopAsync(CancellationToken.None);
        }
    }

    [Fact]
    public async Task PlayerOfficeRequestIsFencedPersistedForwardedAndCompleted()
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

        var officeId = Guid.NewGuid();
        registry.Register(CurrentIdentity(process, "office", officeId));
        await using var office = await ConnectAsync(server.PipeName);
        await WriteHelloAsync(office, process, "office", officeId, null);
        var officeWelcome = await ReadAsync(office);
        Assert.True(officeWelcome.OwnerEpoch > 0);
        await WriteAsync(office, Frame("worker_ready", officeId, officeWelcome.OwnerEpoch, null, new WorkerReadyDto
        {
            UiReady = true,
            Dependencies = new Dictionary<string, string> { ["powerpoint.com"] = "ready" },
        }));
        Assert.Equal("health_accepted", (await ReadAsync(office)).MessageType);

        var playerId = Guid.NewGuid();
        registry.Register(CurrentIdentity(process, "player-1", playerId));
        await using var player = await ConnectAsync(server.PipeName);
        await WriteHelloAsync(player, process, "player-1", playerId, DisplayTarget(1));
        var playerWelcome = await ReadAsync(player);
        var operationId = Guid.NewGuid();
        var commandId = Guid.NewGuid();
        await WriteAsync(player, Frame("office_request", playerId, playerWelcome.OwnerEpoch, DisplayTarget(1), new OfficeRequestDto
        {
            OfficeOperationId = operationId,
            ParentCommandId = commandId,
            ClaimToken = Guid.NewGuid(),
            SourceGeneration = 7,
            GroupEpoch = starting.GroupEpoch,
            Deadline = DateTimeOffset.UtcNow.AddSeconds(5).ToString("O"),
            Operation = "open",
            Parameters = new Dictionary<string, JsonElement>
            {
                ["window_id"] = JsonSerializer.SerializeToElement(1),
                ["source_id"] = JsonSerializer.SerializeToElement(42L),
                ["source_digest"] = JsonSerializer.SerializeToElement("sha256:source"),
            },
        }));

        var forwarded = await ReadAsync(office);
        Assert.Equal("office_request", forwarded.MessageType);
        var normalized = forwarded.Payload.Deserialize<OfficeRequestDto>();
        Assert.NotNull(normalized);
        Assert.Equal(operationId, normalized.OfficeOperationId);
        Assert.Equal(starting.GroupEpoch, normalized.GroupEpoch);
        Assert.Equal(officeWelcome.OwnerEpoch, normalized.HostEpoch);
        Assert.True(normalized.SlotEpoch > 0);

        // Office OPEN 仍在执行时，同一 Player 连接必须继续处理租约/健康消息。
        await WriteAsync(player, Frame("worker_ready", playerId, playerWelcome.OwnerEpoch, DisplayTarget(1), new WorkerReadyDto
        {
            UiReady = true,
            Dependencies = new Dictionary<string, string> { ["wpf"] = "ready" },
        }));
        Assert.Equal("health_accepted", (await ReadAsync(player)).MessageType);

        var result = new OfficeResultDto
        {
            OfficeOperationId = operationId,
            Status = "succeeded",
            ResultFingerprint = "sha256:office-result",
            Result = JsonSerializer.SerializeToElement(new
            {
                playback_mode = "powerpoint",
                presentation_identity = 9L,
                host_epoch = normalized.HostEpoch,
                slot_epoch = normalized.SlotEpoch,
            }),
        };
        await WriteAsync(office, Frame("office_result", officeId, officeWelcome.OwnerEpoch, null, result));
        Assert.Equal("office_result_accepted", (await ReadAsync(office)).MessageType);
        var playerResult = await ReadAsync(player);
        Assert.Equal("office_result", playerResult.MessageType);
        Assert.Equal("succeeded", playerResult.Payload.Deserialize<OfficeResultDto>()!.Status);

        await using var check = fixture.Database.CreateDbContext();
        var persisted = await check.OfficeOperations.SingleAsync(item => item.OperationId == operationId);
        Assert.Equal(OperationStatus.Succeeded, persisted.Status);
        Assert.Equal("sha256:office-result", persisted.ResultFingerprint);

        var fallbackPath = Path.Combine(Path.GetTempPath(), $"scp-cv-{Guid.NewGuid():N}.pdf");
        await File.WriteAllBytesAsync(fallbackPath, "%PDF-1.4"u8.ToArray());
        try
        {
            var fallbackOperation = Guid.NewGuid();
            await WriteAsync(player, Frame("office_request", playerId, playerWelcome.OwnerEpoch, DisplayTarget(1), new OfficeRequestDto
            {
                OfficeOperationId = fallbackOperation,
                ParentCommandId = Guid.NewGuid(),
                ClaimToken = Guid.NewGuid(),
                SourceGeneration = 8,
                GroupEpoch = starting.GroupEpoch,
                Deadline = DateTimeOffset.UtcNow.AddSeconds(5).ToString("O"),
                Operation = "open",
                Parameters = new Dictionary<string, JsonElement>
                {
                    ["window_id"] = JsonSerializer.SerializeToElement(2),
                    ["source_id"] = JsonSerializer.SerializeToElement(43L),
                    ["source_digest"] = JsonSerializer.SerializeToElement("sha256:fallback"),
                    ["fallback_uri"] = JsonSerializer.SerializeToElement(fallbackPath),
                    ["fallback_digest"] = JsonSerializer.SerializeToElement("sha256:fallback"),
                    ["fallback_fresh"] = JsonSerializer.SerializeToElement(true),
                },
            }));
            var fallback = (await ReadAsync(player)).Payload.Deserialize<OfficeResultDto>();
            Assert.NotNull(fallback);
            Assert.Equal("fallback", fallback.Status);
            Assert.Equal("pdf", fallback.Result.GetProperty("playback_mode").GetString());
            Assert.Equal(fallbackPath, fallback.Result.GetProperty("uri").GetString());
        }
        finally
        {
            File.Delete(fallbackPath);
        }
        await broker.StopAsync(CancellationToken.None);
    }

    [Fact]
    public async Task TimedOutOfficeOpenRemainsUncertainAndKeepsDynamicSlotFenced()
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

        var officeId = Guid.NewGuid();
        registry.Register(CurrentIdentity(process, "office", officeId));
        await using var office = await ConnectAsync(server.PipeName);
        await WriteHelloAsync(office, process, "office", officeId, null);
        var officeWelcome = await ReadAsync(office);
        await WriteAsync(office, Frame("worker_ready", officeId, officeWelcome.OwnerEpoch, null, new WorkerReadyDto
        {
            UiReady = true,
            Dependencies = new Dictionary<string, string> { ["powerpoint.com"] = "ready" },
        }));
        Assert.Equal("health_accepted", (await ReadAsync(office)).MessageType);

        var playerId = Guid.NewGuid();
        registry.Register(CurrentIdentity(process, "player-1", playerId));
        await using var player = await ConnectAsync(server.PipeName);
        await WriteHelloAsync(player, process, "player-1", playerId, DisplayTarget(1));
        var playerWelcome = await ReadAsync(player);
        var operationId = Guid.NewGuid();
        await WriteAsync(player, Frame("office_request", playerId, playerWelcome.OwnerEpoch, DisplayTarget(1), new OfficeRequestDto
        {
            OfficeOperationId = operationId,
            ParentCommandId = Guid.NewGuid(),
            ClaimToken = Guid.NewGuid(),
            SourceGeneration = 7,
            GroupEpoch = starting.GroupEpoch,
            Deadline = DateTimeOffset.UtcNow.AddMilliseconds(500).ToString("O"),
            Operation = "open",
            Parameters = new Dictionary<string, JsonElement>
            {
                ["window_id"] = JsonSerializer.SerializeToElement(1),
                ["source_id"] = JsonSerializer.SerializeToElement(42L),
                ["source_digest"] = JsonSerializer.SerializeToElement("sha256:source"),
            },
        }));

        var forwarded = await ReadAsync(office);
        var normalized = forwarded.Payload.Deserialize<OfficeRequestDto>();
        Assert.NotNull(normalized);
        var timedOut = (await ReadAsync(player)).Payload.Deserialize<OfficeResultDto>();
        Assert.NotNull(timedOut);
        Assert.Equal("uncertain", timedOut.Status);
        Assert.Equal("office_timeout", timedOut.ErrorCode);

        await WriteAsync(player, Frame("office_request", playerId, playerWelcome.OwnerEpoch, DisplayTarget(1), new OfficeRequestDto
        {
            OfficeOperationId = Guid.NewGuid(),
            ParentCommandId = Guid.NewGuid(),
            ClaimToken = Guid.NewGuid(),
            SourceGeneration = 8,
            GroupEpoch = starting.GroupEpoch,
            Deadline = DateTimeOffset.UtcNow.AddSeconds(5).ToString("O"),
            Operation = "open",
            Parameters = new Dictionary<string, JsonElement>
            {
                ["window_id"] = JsonSerializer.SerializeToElement(2),
                ["source_id"] = JsonSerializer.SerializeToElement(43L),
                ["source_digest"] = JsonSerializer.SerializeToElement("sha256:second"),
            },
        }));
        var second = (await ReadAsync(player)).Payload.Deserialize<OfficeResultDto>();
        Assert.NotNull(second);
        Assert.Equal("failed", second.Status);
        Assert.Equal("matching_pdf_unavailable", second.ErrorCode);

        await WriteAsync(office, Frame("office_result", officeId, officeWelcome.OwnerEpoch, null, new OfficeResultDto
        {
            OfficeOperationId = operationId,
            Status = "succeeded",
            ResultFingerprint = "sha256:late-office-result",
            Result = JsonSerializer.SerializeToElement(new { playback_mode = "powerpoint" }),
        }));
        var lateAcceptance = await ReadAsync(office);
        Assert.Equal("office_result_accepted", lateAcceptance.MessageType);
        Assert.False(lateAcceptance.Payload.GetProperty("accepted").GetBoolean());

        await using var check = fixture.Database.CreateDbContext();
        var persisted = await check.OfficeOperations.SingleAsync(item => item.OperationId == operationId);
        Assert.Equal(OperationStatus.Uncertain, persisted.Status);
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
            projections,
            new AudioFinishedEventProcessor(audio));
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

    private static async Task<(long First, long Second)> SeedAudioSourcesAsync(ControlHostFixture fixture)
    {
        await using var database = fixture.Database.CreateDbContext();
        var first = new MediaSource
        {
            SourceType = MediaSourceType.Audio,
            Name = "broker-audio-1",
            Uri = "broker-audio-1.mp3",
            SourceRevision = 1,
            CreatedAt = fixture.TimeProvider.GetUtcNow(),
        };
        var second = new MediaSource
        {
            SourceType = MediaSourceType.Audio,
            Name = "broker-audio-2",
            Uri = "broker-audio-2.mp3",
            SourceRevision = 1,
            CreatedAt = fixture.TimeProvider.GetUtcNow(),
        };
        database.MediaSources.AddRange(first, second);
        await database.SaveChangesAsync();
        return (first.Id, second.Id);
    }

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
