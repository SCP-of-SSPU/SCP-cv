using System.Text.Json;
using ScpCv.Contracts.Ipc;
using ScpCv.ControlHost.Events;
using ScpCv.Domain.Model;
using ScpCv.Infrastructure.Commands;

namespace ScpCv.ControlHost.Ipc;

public sealed class RuntimeMessageDispatcher(
    CommandLeaseService leases,
    CommandResultService results,
    RuntimeProjectionPublisher projections,
    TimeSpan? leaseDuration = null)
{
    private readonly TimeSpan _leaseDuration = leaseDuration ?? TimeSpan.FromSeconds(30);

    public async Task<IpcFrameDto> DispatchAsync(
        IpcFrameDto frame,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(frame);
        if (frame.ProtocolVersion != IpcProtocol.Version)
        {
            return Response(frame, "error", new { code = "unsupported_protocol", retryable = false });
        }

        if (!TryTarget(frame.Target, out var targetKind, out var targetId))
        {
            return Response(frame, "error", new { code = "invalid_target", retryable = false });
        }

        return frame.MessageType.Trim().ToLowerInvariant() switch
        {
            "claim_request" => await ClaimAsync(frame, targetKind, targetId, cancellationToken).ConfigureAwait(false),
            "lease_renew" => await RenewAsync(frame, cancellationToken).ConfigureAwait(false),
            "command_result" => await ResultAsync(frame, targetKind, targetId, cancellationToken).ConfigureAwait(false),
            "state_report" => await StateAsync(frame, targetKind, targetId, cancellationToken).ConfigureAwait(false),
            _ => Response(frame, "error", new { code = "unknown_message_type", retryable = false }),
        };
    }

    private async Task<IpcFrameDto> ClaimAsync(
        IpcFrameDto frame,
        CommandTargetKind targetKind,
        int targetId,
        CancellationToken cancellationToken)
    {
        var request = frame.Payload.Deserialize<ClaimRequestDto>() ?? new ClaimRequestDto();
        try
        {
            var command = await leases.ClaimAsync(
                    new LeaseClaimRequest(
                        targetKind,
                        targetId,
                        frame.InstanceId,
                        frame.OwnerEpoch,
                        request.GroupEpoch,
                        _leaseDuration),
                    cancellationToken)
                .ConfigureAwait(false);
            if (command is null)
            {
                return Response(frame, "no_work", new NoWorkDto { Reason = "empty_or_busy", RetryAfterMs = 1000 });
            }

            var args = JsonSerializer.Deserialize<Dictionary<string, JsonElement>>(command.ArgsJson) ?? [];
            return Response(frame, "command_lease", new CommandLeaseDto
            {
                CommandId = command.CommandId,
                TargetSequence = command.TargetSequence,
                Command = command.Command,
                Args = args,
                ClaimToken = command.ClaimToken!.Value,
                OwnerEpoch = command.OwnerEpoch,
                GroupEpoch = request.GroupEpoch,
                SourceGeneration = command.SourceGeneration,
                SourceRevision = command.SourceRevision,
                LeaseExpiresAt = command.LeaseExpiresAt!.Value.ToString("O"),
                Deadline = command.Deadline?.ToString("O"),
            });
        }
        catch (CommandFenceException)
        {
            return Response(frame, "no_work", new NoWorkDto { Reason = "fenced", RetryAfterMs = 1000 });
        }
    }

    private async Task<IpcFrameDto> RenewAsync(IpcFrameDto frame, CancellationToken cancellationToken)
    {
        var request = frame.Payload.Deserialize<LeaseRenewDto>() ?? new LeaseRenewDto();
        var accepted = await leases.RenewAsync(
                request.CommandId,
                request.ClaimToken,
                request.OwnerEpoch,
                _leaseDuration,
                cancellationToken)
            .ConfigureAwait(false);
        return Response(frame, "renew_result", new RenewResultDto
        {
            Accepted = accepted,
            LeaseExpiresAt = accepted ? DateTimeOffset.UtcNow.Add(_leaseDuration).ToString("O") : null,
            Reason = accepted ? "accepted" : "fenced",
        });
    }

    private async Task<IpcFrameDto> ResultAsync(
        IpcFrameDto frame,
        CommandTargetKind targetKind,
        int targetId,
        CancellationToken cancellationToken)
    {
        var request = frame.Payload.Deserialize<CommandResultDto>() ?? new CommandResultDto();
        if (!Enum.TryParse<CommandStatus>(request.Status, true, out var status))
        {
            return Response(frame, "error", new { code = "invalid_result_status", retryable = false });
        }

        try
        {
            var evidenceJson = JsonSerializer.Serialize(request.Evidence);
            var acceptance = await results.AcceptAsync(
                    new CompleteCommand(
                        request.CommandId,
                        request.ClaimToken,
                        request.OwnerEpoch,
                        status,
                        request.ResultCode,
                        request.ResultHash,
                        evidenceJson),
                    cancellationToken)
                .ConfigureAwait(false);
            if (request.ActualState.ValueKind == JsonValueKind.Object)
            {
                await projections.ApplyStateReportAsync(
                        targetKind,
                        targetId,
                        frame.InstanceId,
                        frame.OwnerEpoch,
                        new StateReportDto
                        {
                            SourceGeneration = ReadGeneration(request.ActualState),
                            State = request.ActualState,
                        },
                        cancellationToken)
                    .ConfigureAwait(false);
            }
            else
            {
                projections.PublishCommandResult();
            }

            return Response(frame, "result_accepted", new ResultAcceptedDto
            {
                CommandId = request.CommandId,
                Accepted = acceptance.Accepted,
                Duplicate = acceptance.Duplicate,
            });
        }
        catch (CommandFenceException)
        {
            return Response(frame, "error", new { code = "command_fenced", retryable = false });
        }
        catch (CommandResultConflictException)
        {
            return Response(frame, "error", new { code = "result_conflict", retryable = false });
        }
    }

    private async Task<IpcFrameDto> StateAsync(
        IpcFrameDto frame,
        CommandTargetKind targetKind,
        int targetId,
        CancellationToken cancellationToken)
    {
        var request = frame.Payload.Deserialize<StateReportDto>() ?? new StateReportDto();
        var acceptance = await projections.ApplyStateReportAsync(
                targetKind,
                targetId,
                frame.InstanceId,
                frame.OwnerEpoch,
                request,
                cancellationToken)
            .ConfigureAwait(false);
        return Response(frame, "state_accepted", new { accepted = acceptance.Accepted, reason = acceptance.Reason });
    }

    private static IpcFrameDto Response<T>(IpcFrameDto request, string messageType, T payload) => new()
    {
        MessageType = messageType,
        MessageId = Guid.NewGuid(),
        CorrelationId = request.MessageId,
        InstanceId = Guid.Empty,
        OwnerEpoch = request.OwnerEpoch,
        Target = request.Target,
        Payload = JsonSerializer.SerializeToElement(payload),
    };

    private static bool TryTarget(IpcTargetDto? target, out CommandTargetKind kind, out int id)
    {
        id = target?.Id ?? 0;
        return Enum.TryParse(target?.Kind, true, out kind) &&
               (kind == CommandTargetKind.Display ? id is >= 1 and <= 4 : id == 1);
    }

    private static long ReadGeneration(JsonElement state) =>
        state.TryGetProperty("source_generation", out var value) && value.TryGetInt64(out var parsed)
            ? parsed
            : 0;
}
