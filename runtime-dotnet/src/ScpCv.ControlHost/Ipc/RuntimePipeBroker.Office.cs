using System.Text.Json;
using ScpCv.Contracts.Ipc;
using ScpCv.Domain.Model;
using ScpCv.Domain.Rules;
using ScpCv.Infrastructure.Runtime;

namespace ScpCv.ControlHost.Ipc;

public sealed partial class RuntimePipeBroker
{
    private async Task<IpcFrameDto> ForwardOfficeRequestAsync(
        RuntimeConnection player,
        IpcFrameDto frame,
        CancellationToken cancellationToken)
    {
        var request = frame.Payload.Deserialize<OfficeRequestDto>()
            ?? throw new InvalidDataException("OfficeRequest payload 无效。");
        if (request.OfficeOperationId == Guid.Empty || string.IsNullOrWhiteSpace(request.Operation))
        {
            return Response(frame, "office_result", OfficeResult("failed", "invalid_office_request", request.OfficeOperationId));
        }

        if (!_connections.TryGetValue("office", out var office) || office.OwnerEpoch <= 0)
        {
            return Response(frame, "office_result", OfficeResult("failed", "office_unavailable", request.OfficeOperationId));
        }

        var group = await authority.GetGroupAsync(cancellationToken).ConfigureAwait(false);
        if (group.State != RuntimeGroupState.Armed || group.GroupEpoch != player.GroupEpoch)
        {
            return Response(frame, "office_result", OfficeResult("failed", "group_not_armed", request.OfficeOperationId));
        }

        var operation = request.Operation.Trim().ToLowerInvariant();
        var authorityRequest = request with
        {
            GroupEpoch = player.GroupEpoch,
            HostEpoch = office.OwnerEpoch,
        };
        var requestFingerprint = OfficeRequestFingerprint(authorityRequest);
        if (_officeResults.TryGetValue(request.OfficeOperationId, out var earlyCached))
        {
            return Response(frame, "office_result",
                string.Equals(earlyCached.RequestFingerprint, requestFingerprint, StringComparison.Ordinal)
                    ? earlyCached.Result
                    : OfficeResult("failed", "office_operation_conflict", request.OfficeOperationId));
        }
        if (_officePending.TryGetValue(request.OfficeOperationId, out var earlyPending))
        {
            if (!string.Equals(earlyPending.RequestFingerprint, requestFingerprint, StringComparison.Ordinal))
                return Response(frame, "office_result", OfficeResult("failed", "office_operation_conflict", request.OfficeOperationId));
            return Response(frame, "office_result", await WaitForOfficeResultAsync(
                earlyPending.Completion.Task,
                ParseDeadline(authorityRequest.Deadline),
                request.OfficeOperationId,
                cancellationToken).ConfigureAwait(false));
        }

        var acquiredSlot = false;
        if (operation == "open")
        {
            var decision = ChoosePresentation(authorityRequest);
            if (!decision.Accepted)
            {
                return Response(frame, "office_result", OfficeResult("failed", decision.Code, request.OfficeOperationId));
            }

            if (decision.Mode == PlaybackMode.Pdf)
            {
                return Response(frame, "office_result", new OfficeResultDto
                {
                    OfficeOperationId = request.OfficeOperationId,
                    Status = "fallback",
                    ResultFingerprint = $"fallback:{request.OfficeOperationId:N}",
                    Result = JsonSerializer.SerializeToElement(new
                    {
                        playback_mode = "pdf",
                        uri = ReadString(request.Parameters, "fallback_uri"),
                        code = decision.Code,
                    }),
                });
            }
            acquiredSlot = decision.Mode == PlaybackMode.PowerPoint;
        }

        var currentSlot = _presentations.CurrentSlot;
        if (operation != "open" &&
            (currentSlot is null || player.Target is null || currentSlot.WindowId != player.Target.Value.Id ||
             request.HostEpoch != office.OwnerEpoch || request.SlotEpoch != currentSlot.SlotEpoch ||
             ReadLong(request.Parameters, "slot_source_generation") != currentSlot.SourceGeneration))
        {
            return Response(frame, "office_result", OfficeResult("failed", "office_slot_fenced", request.OfficeOperationId));
        }

        var slotEpoch = currentSlot?.SlotEpoch ?? request.SlotEpoch;
        if (slotEpoch <= 0)
        {
            return Response(frame, "office_result", OfficeResult("failed", "slot_not_acquired", request.OfficeOperationId));
        }

        var normalized = authorityRequest with
        {
            GroupEpoch = player.GroupEpoch,
            HostEpoch = office.OwnerEpoch,
            SlotEpoch = slotEpoch,
        };
        var deadline = ParseDeadline(normalized.Deadline);
        try
        {
            await authority.RegisterOfficeOperationAsync(new RegisterOfficeOperation(
                normalized.OfficeOperationId,
                normalized.ParentCommandId,
                normalized.ParentJobId,
                normalized.ClaimToken,
                normalized.SourceGeneration,
                normalized.GroupEpoch,
                normalized.HostEpoch,
                normalized.SlotEpoch,
                deadline,
                JsonSerializer.Serialize(new { normalized.Operation, normalized.Parameters })), cancellationToken).ConfigureAwait(false);
        }
        catch (OfficeOperationConflictException)
        {
            if (acquiredSlot) _presentations.Release(office.OwnerEpoch, slotEpoch);
            return Response(frame, "office_result", OfficeResult("failed", "office_operation_conflict", request.OfficeOperationId));
        }
        catch (RuntimeAuthorityException exception)
        {
            if (acquiredSlot) _presentations.Release(office.OwnerEpoch, slotEpoch);
            return Response(frame, "office_result", OfficeResult("failed", "office_authority_rejected", request.OfficeOperationId) with { ErrorDetail = exception.Message });
        }

        if (_officeResults.TryGetValue(normalized.OfficeOperationId, out var cached))
        {
            return Response(frame, "office_result", cached.Result);
        }

        var completion = new TaskCompletionSource<OfficeResultDto>(TaskCreationOptions.RunContinuationsAsynchronously);
        if (!_officePending.TryAdd(normalized.OfficeOperationId, new OfficePendingRequest(
            completion,
            normalized,
            player.Identity.InstanceId,
            requestFingerprint)))
        {
            if (_officeResults.TryGetValue(normalized.OfficeOperationId, out cached))
                return Response(frame, "office_result", cached.Result);
            if (_officePending.TryGetValue(normalized.OfficeOperationId, out var existing))
            {
                if (!string.Equals(existing.RequestFingerprint, requestFingerprint, StringComparison.Ordinal))
                    return Response(frame, "office_result", OfficeResult("failed", "office_operation_conflict", request.OfficeOperationId));
                return Response(frame, "office_result", await WaitForOfficeResultAsync(
                    existing.Completion.Task,
                    deadline,
                    request.OfficeOperationId,
                    cancellationToken).ConfigureAwait(false));
            }
            return Response(frame, "office_result", OfficeResult("failed", "office_operation_inflight", request.OfficeOperationId));
        }

        var officeFrame = new IpcFrameDto
        {
            MessageType = "office_request",
            MessageId = Guid.NewGuid(),
            InstanceId = office.Identity.InstanceId,
            OwnerEpoch = office.OwnerEpoch,
            Payload = JsonSerializer.SerializeToElement(normalized),
        };
        try
        {
            await office.SendAsync(officeFrame, cancellationToken).ConfigureAwait(false);
            var remaining = deadline - DateTimeOffset.UtcNow;
            if (remaining <= TimeSpan.Zero)
                throw new TimeoutException("Office 操作 deadline 已过期。");
            var result = await completion.Task.WaitAsync(remaining, cancellationToken).ConfigureAwait(false);
            _officeResults[normalized.OfficeOperationId] = new OfficeCachedResult(requestFingerprint, result);
            return Response(frame, "office_result", result);
        }
        catch (TimeoutException)
        {
            _officePending.TryRemove(normalized.OfficeOperationId, out _);
            var uncertain = OfficeResult("uncertain", "office_timeout", normalized.OfficeOperationId);
            _officeResults[normalized.OfficeOperationId] = new OfficeCachedResult(requestFingerprint, uncertain);
            await CompleteOfficeOperationAsync(normalized, uncertain, cancellationToken).ConfigureAwait(false);
            return Response(frame, "office_result", uncertain);
        }
        finally
        {
            _officePending.TryRemove(normalized.OfficeOperationId, out _);
            if (operation == "close" && _officeResults.TryGetValue(normalized.OfficeOperationId, out var close) && close.Result.Status == "succeeded")
                _presentations.Release(normalized.HostEpoch, normalized.SlotEpoch);
            if (operation == "open" && _officeResults.TryGetValue(normalized.OfficeOperationId, out var open) && open.Result.Status == "failed")
                _presentations.Release(normalized.HostEpoch, normalized.SlotEpoch);
        }
    }

    private async Task<IpcFrameDto> CompleteOfficeResultAsync(
        RuntimeConnection office,
        IpcFrameDto frame,
        CancellationToken cancellationToken)
    {
        var result = frame.Payload.Deserialize<OfficeResultDto>()
            ?? throw new InvalidDataException("OfficeResult payload 无效。");
        if (!_officePending.TryGetValue(result.OfficeOperationId, out var pending) ||
            pending.Request.HostEpoch != office.OwnerEpoch)
        {
            return Response(frame, "office_result_accepted", new { accepted = false, reason = "office_operation_unknown" });
        }

        var status = result.Status.Trim().ToLowerInvariant() switch
        {
            "succeeded" => OperationStatus.Succeeded,
            "uncertain" => OperationStatus.Uncertain,
            _ => OperationStatus.Failed,
        };
        var acceptance = await authority.CompleteOfficeOperationAsync(new CompleteOfficeOperation(
            result.OfficeOperationId,
            pending.Request.HostEpoch,
            pending.Request.SlotEpoch,
            status,
            result.ResultFingerprint,
            result.ErrorDetail), cancellationToken).ConfigureAwait(false);
        pending.Completion.TrySetResult(result);
        return Response(frame, "office_result_accepted", new { accepted = acceptance.Accepted, duplicate = acceptance.Duplicate });
    }

    private async Task CompleteOfficeOperationAsync(
        OfficeRequestDto request,
        OfficeResultDto result,
        CancellationToken cancellationToken)
    {
        var status = result.Status.Equals("uncertain", StringComparison.OrdinalIgnoreCase)
            ? OperationStatus.Uncertain
            : OperationStatus.Failed;
        try
        {
            await authority.CompleteOfficeOperationAsync(new CompleteOfficeOperation(
                request.OfficeOperationId,
                request.HostEpoch,
                request.SlotEpoch,
                status,
                result.ResultFingerprint,
                result.ErrorDetail), cancellationToken).ConfigureAwait(false);
        }
        catch (Exception exception) when (exception is OfficeOperationConflictException or RuntimeAuthorityException or KeyNotFoundException)
        {
            LogOfficeCompletionFailed(logger, request.OfficeOperationId, exception);
        }
    }

    private PresentationDecision ChoosePresentation(OfficeRequestDto request)
    {
        var sourceDigest = ReadString(request.Parameters, "source_digest") ?? string.Empty;
        var windowId = ReadInt(request.Parameters, "window_id", 1);
        var fallbackUri = ReadString(request.Parameters, "fallback_uri");
        var fallbackDigest = ReadString(request.Parameters, "fallback_digest");
        var fallbackAvailable = !string.IsNullOrWhiteSpace(fallbackUri) && File.Exists(fallbackUri);
        var fallbackFresh = ReadBool(request.Parameters, "fallback_fresh", fallbackAvailable);
        return _presentations.Open(
            windowId,
            ReadLong(request.Parameters, "source_id"),
            request.SourceGeneration,
            sourceDigest,
            fallbackAvailable,
            fallbackDigest,
            fallbackFresh,
            request.HostEpoch);
    }

    private static OfficeResultDto OfficeResult(string status, string code, Guid? operationId = null) => new()
    {
        OfficeOperationId = operationId ?? Guid.Empty,
        Status = status,
        ResultFingerprint = $"{status}:{code}",
        ErrorCode = code,
        ErrorDetail = code,
        Result = JsonSerializer.SerializeToElement(new { code }),
    };

    private static DateTimeOffset ParseDeadline(string value) =>
        DateTimeOffset.TryParse(value, out var parsed) ? parsed : DateTimeOffset.UtcNow.AddSeconds(30);

    private static async Task<OfficeResultDto> WaitForOfficeResultAsync(
        Task<OfficeResultDto> task,
        DateTimeOffset deadline,
        Guid operationId,
        CancellationToken cancellationToken)
    {
        var remaining = deadline - DateTimeOffset.UtcNow;
        if (remaining <= TimeSpan.Zero) return OfficeResult("uncertain", "office_timeout", operationId);
        try
        {
            return await task.WaitAsync(remaining, cancellationToken).ConfigureAwait(false);
        }
        catch (TimeoutException)
        {
            return OfficeResult("uncertain", "office_timeout", operationId);
        }
    }

    private static string OfficeRequestFingerprint(OfficeRequestDto request) =>
        JsonSerializer.Serialize(new
        {
            request.OfficeOperationId,
            request.ParentCommandId,
            request.ParentJobId,
            request.ClaimToken,
            request.SourceGeneration,
            request.GroupEpoch,
            request.HostEpoch,
            request.Deadline,
            operation = request.Operation.Trim().ToLowerInvariant(),
            parameters = request.Parameters.OrderBy(pair => pair.Key, StringComparer.Ordinal)
                .Select(pair => new { pair.Key, pair.Value }),
        });

    private static string? ReadString(Dictionary<string, JsonElement> values, string key) =>
        values.TryGetValue(key, out var value) && value.ValueKind == JsonValueKind.String ? value.GetString() : null;

    private static long ReadLong(Dictionary<string, JsonElement> values, string key) =>
        values.TryGetValue(key, out var value) && value.TryGetInt64(out var parsed) ? parsed : 0;

    private static int ReadInt(Dictionary<string, JsonElement> values, string key, int fallback) =>
        values.TryGetValue(key, out var value) && value.TryGetInt32(out var parsed) ? parsed : fallback;

    private static bool ReadBool(Dictionary<string, JsonElement> values, string key, bool fallback) =>
        values.TryGetValue(key, out var value) && value.ValueKind is JsonValueKind.True or JsonValueKind.False
            ? value.GetBoolean()
            : fallback;

    private sealed record OfficePendingRequest(
        TaskCompletionSource<OfficeResultDto> Completion,
        OfficeRequestDto Request,
        Guid PlayerInstanceId,
        string RequestFingerprint);

    private sealed record OfficeCachedResult(string RequestFingerprint, OfficeResultDto Result);
}
