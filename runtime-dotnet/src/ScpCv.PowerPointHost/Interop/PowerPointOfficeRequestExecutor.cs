using System.Collections.Concurrent;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using ScpCv.Contracts.Ipc;
using ScpCv.PowerPointHost.Windows;

namespace ScpCv.PowerPointHost.Interop;

/// <summary>
/// PowerPointHost 内部的 OfficeRequest 执行器。
/// 每个 operation_id 只进入一次 STA；传输重试只重放缓存结果，不重复 COM 副作用。
/// </summary>
public sealed class PowerPointOfficeRequestExecutor(
    PowerPointComAdapter adapter,
    long groupEpoch,
    long hostEpoch,
    Action<PowerPointOpenResult>? onOpened = null)
{
    private readonly ConcurrentDictionary<Guid, OfficeExecution> _operations = new();

    public Task<OfficeResultDto> ExecuteAsync(
        OfficeRequestDto request,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(request);
        if (request.OfficeOperationId == Guid.Empty)
            return Task.FromResult(Failed(request, "invalid_operation_id", "Office operation_id 为空。"));

        var fingerprint = RequestFingerprint(request);
        var execution = _operations.GetOrAdd(
            request.OfficeOperationId,
            _ => new OfficeExecution(
                fingerprint,
                new Lazy<Task<OfficeResultDto>>(
                    () => ExecuteCoreAsync(request, cancellationToken),
                    LazyThreadSafetyMode.ExecutionAndPublication)));
        if (!string.Equals(execution.RequestFingerprint, fingerprint, StringComparison.Ordinal))
            return Task.FromResult(Failed(request, "office_operation_conflict", "同一 operation_id 的参数不一致。"));
        return AwaitCachedAsync(execution.Result.Value, cancellationToken);
    }

    private static async Task<OfficeResultDto> AwaitCachedAsync(
        Task<OfficeResultDto> operation,
        CancellationToken cancellationToken) =>
        await operation.WaitAsync(cancellationToken).ConfigureAwait(false);

    private async Task<OfficeResultDto> ExecuteCoreAsync(
        OfficeRequestDto request,
        CancellationToken cancellationToken)
    {
        if (request.GroupEpoch != groupEpoch)
            return Failed(request, "group_epoch_stale", "Office 请求的运行组 epoch 已失效。");
        if (request.HostEpoch != hostEpoch)
            return Failed(request, "host_epoch_stale", "Office 请求的 Host epoch 已失效。");
        if (request.SlotEpoch <= 0)
            return Failed(request, "slot_epoch_stale", "Office 请求没有有效槽位 epoch。");
        if (DateTimeOffset.TryParse(request.Deadline, out var deadline) && DateTimeOffset.UtcNow >= deadline)
            return Failed(request, "deadline_expired", "Office 操作在进入 STA 前已过期。");

        try
        {
            return request.Operation.Trim().ToLowerInvariant() switch
            {
                "open" => await OpenAsync(request, cancellationToken).ConfigureAwait(false),
                "navigate" => await NavigateAsync(request, cancellationToken).ConfigureAwait(false),
                "playback" => await PlaybackAsync(request, cancellationToken).ConfigureAwait(false),
                "media" => await MediaAsync(request, cancellationToken).ConfigureAwait(false),
                "close" => await CloseAsync(request, cancellationToken).ConfigureAwait(false),
                "export_pdf" => await ExportPdfAsync(request, cancellationToken).ConfigureAwait(false),
                _ => Failed(request, "unsupported_operation", $"不支持 Office 操作 {request.Operation}。"),
            };
        }
        catch (OperationCanceledException)
        {
            throw;
        }
        catch (Exception exception)
        {
            return Failed(request, "office_exception", exception.Message);
        }
    }

    private async Task<OfficeResultDto> OpenAsync(OfficeRequestDto request, CancellationToken cancellationToken)
    {
        var path = String(request.Parameters, "path");
        var opened = await adapter.OpenAsync(request.OfficeOperationId, path, cancellationToken).ConfigureAwait(false);
        if (!opened.Succeeded)
            return Failed(request, opened.Code, opened.Code);
        onOpened?.Invoke(opened);

        var parent = (nint)Long(request.Parameters, "parent_hwnd");
        var expectedDpi = Int(request.Parameters, "expected_dpi", 0);
        var attach = SlideShowWindowAttacher.Attach(new SlideShowSurfaceRequest(
            parent,
            opened.SlideShowWindowHandle,
            opened.ProcessId,
            opened.ProcessStart,
            expectedDpi,
            Int(request.Parameters, "x", 0),
            Int(request.Parameters, "y", 0),
            Int(request.Parameters, "width", 0),
            Int(request.Parameters, "height", 0),
            Int(request.Parameters, "parent_process_id", 0),
            ParseDateTime(request.Parameters, "parent_process_start")));
        if (!attach.Attached)
        {
            await adapter.CloseAsync(Guid.NewGuid(), opened.PresentationIdentity, CancellationToken.None).ConfigureAwait(false);
            return Failed(request, attach.Code, $"放映窗口附着失败：{attach.Code}");
        }

        return Succeeded(request, new
        {
            playback_mode = "powerpoint",
            presentation_identity = opened.PresentationIdentity,
            slideshow_hwnd = opened.SlideShowWindowHandle.ToInt64(),
            slide_count = opened.SlideCount,
            process_id = opened.ProcessId,
            process_start = opened.ProcessStart.ToString("O"),
            actual_dpi = attach.ActualDpi,
            host_epoch = request.HostEpoch,
            slot_epoch = request.SlotEpoch,
        });
    }

    private async Task<OfficeResultDto> NavigateAsync(OfficeRequestDto request, CancellationToken cancellationToken)
    {
        var identity = Long(request.Parameters, "presentation_identity");
        var slide = Int(request.Parameters, "target_slide", 1);
        var navigated = await adapter.NavigateAsync(
            request.OfficeOperationId,
            identity,
            String(request.Parameters, "action"),
            slide,
            cancellationToken).ConfigureAwait(false);
        return navigated.Succeeded
            ? Succeeded(request, new { current_slide = navigated.CurrentSlide, playback_mode = "powerpoint" })
            : Failed(request, "navigate_failed", "PowerPoint 不接受目标页码。");
    }

    private async Task<OfficeResultDto> PlaybackAsync(OfficeRequestDto request, CancellationToken cancellationToken)
    {
        var action = String(request.Parameters, "action");
        var succeeded = await adapter.ControlPlaybackAsync(
            request.OfficeOperationId,
            Long(request.Parameters, "presentation_identity"),
            action,
            cancellationToken).ConfigureAwait(false);
        return succeeded
            ? Succeeded(request, new { playback_mode = "powerpoint", playback_state = action })
            : Failed(request, "playback_control_failed", $"PowerPoint 无法执行 {action}。");
    }

    private async Task<OfficeResultDto> MediaAsync(OfficeRequestDto request, CancellationToken cancellationToken)
    {
        var succeeded = await adapter.ControlMediaAsync(
            request.OfficeOperationId,
            Long(request.Parameters, "presentation_identity"),
            String(request.Parameters, "action"),
            ReadString(request.Parameters, "media_id"),
            ReadNullableInt(request.Parameters, "media_index"),
            cancellationToken).ConfigureAwait(false);
        return succeeded
            ? Succeeded(request, new { playback_mode = "powerpoint" })
            : Failed(request, "media_control_failed", "PowerPoint 未找到可控制的页内媒体。");
    }

    private async Task<OfficeResultDto> CloseAsync(OfficeRequestDto request, CancellationToken cancellationToken)
    {
        var succeeded = await adapter.CloseAsync(
            request.OfficeOperationId,
            Long(request.Parameters, "presentation_identity"),
            cancellationToken).ConfigureAwait(false);
        return succeeded
            ? Succeeded(request, new { playback_mode = "none" })
            : Failed(request, "close_failed", "PowerPoint 放映窗口未能安全关闭。");
    }

    private async Task<OfficeResultDto> ExportPdfAsync(OfficeRequestDto request, CancellationToken cancellationToken)
    {
        var output = String(request.Parameters, "output_path");
        var succeeded = await adapter.ExportPdfAsync(
            request.OfficeOperationId,
            Long(request.Parameters, "presentation_identity"),
            output,
            cancellationToken).ConfigureAwait(false);
        return succeeded
            ? Succeeded(request, new { output_path = output, format = "pdf" })
            : Failed(request, "export_failed", "PowerPoint PDF 导出未生成已验证文件。");
    }

    private static OfficeResultDto Succeeded(OfficeRequestDto request, object result)
    {
        var element = JsonSerializer.SerializeToElement(result);
        return WithFingerprint(new OfficeResultDto
        {
            OfficeOperationId = request.OfficeOperationId,
            Status = "succeeded",
            Result = element,
        });
    }

    private static OfficeResultDto Failed(OfficeRequestDto request, string code, string detail) =>
        WithFingerprint(new OfficeResultDto
        {
            OfficeOperationId = request.OfficeOperationId,
            Status = "failed",
            ErrorCode = code,
            ErrorDetail = detail,
            Result = JsonSerializer.SerializeToElement(new { code }),
        });

    private static OfficeResultDto WithFingerprint(OfficeResultDto result)
    {
        var json = JsonSerializer.Serialize(new
        {
            result.OfficeOperationId,
            result.Status,
            result.Result,
            result.ErrorCode,
            result.ErrorDetail,
        });
        return result with
        {
            ResultFingerprint = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(json))).ToLowerInvariant(),
        };
    }

    private static string RequestFingerprint(OfficeRequestDto request)
    {
        var json = JsonSerializer.Serialize(new
        {
            request.OfficeOperationId,
            request.ParentCommandId,
            request.ParentJobId,
            request.ClaimToken,
            request.SourceGeneration,
            request.GroupEpoch,
            request.HostEpoch,
            request.SlotEpoch,
            request.Deadline,
            request.Operation,
            parameters = request.Parameters.OrderBy(pair => pair.Key, StringComparer.Ordinal)
                .Select(pair => new { pair.Key, pair.Value }),
        });
        return Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(json))).ToLowerInvariant();
    }

    private static string String(Dictionary<string, JsonElement> values, string key) =>
        ReadString(values, key) ?? throw new InvalidDataException($"缺少 Office 参数 {key}。");

    private static string? ReadString(Dictionary<string, JsonElement> values, string key) =>
        values.TryGetValue(key, out var value) && value.ValueKind == JsonValueKind.String ? value.GetString() : null;

    private static long Long(Dictionary<string, JsonElement> values, string key) =>
        values.TryGetValue(key, out var value) && value.TryGetInt64(out var parsed) ? parsed : 0;

    private static int Int(Dictionary<string, JsonElement> values, string key, int fallback) =>
        values.TryGetValue(key, out var value) && value.TryGetInt32(out var parsed) ? parsed : fallback;

    private static int? ReadNullableInt(Dictionary<string, JsonElement> values, string key) =>
        values.TryGetValue(key, out var value) && value.TryGetInt32(out var parsed) ? parsed : null;

    private static DateTimeOffset ParseDateTime(Dictionary<string, JsonElement> values, string key) =>
        ReadString(values, key) is { } raw && DateTimeOffset.TryParse(raw, out var parsed) ? parsed : default;

    private sealed record OfficeExecution(
        string RequestFingerprint,
        Lazy<Task<OfficeResultDto>> Result);
}
