using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Windows.Controls;
using ScpCv.Contracts.Ipc;
using WpfBrushes = System.Windows.Media.Brushes;

namespace ScpCv.PlayerWorker.Playback;

public sealed partial class PlayerRuntimeHost
{
    private async Task<SurfaceResource> OpenPowerPointAsync(
        CommandLeaseDto lease,
        string uri,
        CancellationToken cancellationToken)
    {
        if (_officeSession is null)
            throw new InvalidOperationException("PowerPointHost 管道未连接。");

        var parameters = new Dictionary<string, JsonElement>(StringComparer.Ordinal)
        {
            ["path"] = JsonSerializer.SerializeToElement(LocalPath(uri)),
            ["parent_hwnd"] = JsonSerializer.SerializeToElement(_window.NativeHandle.ToInt64()),
            ["parent_process_id"] = JsonSerializer.SerializeToElement(Environment.ProcessId),
            ["parent_process_start"] = JsonSerializer.SerializeToElement(
                new DateTimeOffset(System.Diagnostics.Process.GetCurrentProcess().StartTime.ToUniversalTime(), TimeSpan.Zero).ToString("O")),
            ["expected_dpi"] = JsonSerializer.SerializeToElement(_window.NativeDpi),
            ["x"] = JsonSerializer.SerializeToElement(0),
            ["y"] = JsonSerializer.SerializeToElement(0),
            ["width"] = JsonSerializer.SerializeToElement((int)Math.Max(1, _window.ActualWidth)),
            ["height"] = JsonSerializer.SerializeToElement((int)Math.Max(1, _window.ActualHeight)),
            ["window_id"] = JsonSerializer.SerializeToElement(_windowId),
            ["source_id"] = JsonSerializer.SerializeToElement(Long(lease.Args, "source_id")),
            ["source_digest"] = JsonSerializer.SerializeToElement(String(lease.Args, "content_digest", string.Empty)),
            ["fallback_uri"] = JsonSerializer.SerializeToElement(String(lease.Args, "fallback_uri", string.Empty)),
            ["fallback_digest"] = JsonSerializer.SerializeToElement(String(lease.Args, "fallback_digest", string.Empty)),
            ["fallback_fresh"] = JsonSerializer.SerializeToElement(Bool(lease.Args, "fallback_fresh", false)),
        };
        var result = await _officeSession.SendOfficeRequestAsync(new OfficeRequestDto
        {
            OfficeOperationId = OfficeOperationId(lease.CommandId, "open"),
            ParentCommandId = lease.CommandId,
            ClaimToken = lease.ClaimToken,
            SourceGeneration = lease.SourceGeneration,
            GroupEpoch = lease.GroupEpoch,
            Deadline = lease.Deadline ?? DateTimeOffset.UtcNow.AddSeconds(30).ToString("O"),
            Operation = "open",
            Parameters = parameters,
        }, cancellationToken).ConfigureAwait(false);

        if (string.Equals(result.Status, "fallback", StringComparison.OrdinalIgnoreCase))
        {
            var fallback = result.Result.TryGetProperty("uri", out var uriValue) && uriValue.ValueKind == JsonValueKind.String
                ? uriValue.GetString()
                : null;
            if (string.IsNullOrWhiteSpace(fallback))
                throw new InvalidOperationException("PowerPoint 槽位占用且没有匹配 PDF 回退。");
            return await OpenPdfAsync(fallback, Int(lease.Args, "target_slide", 1), cancellationToken);
        }

        if (!string.Equals(result.Status, "succeeded", StringComparison.OrdinalIgnoreCase))
            throw new InvalidOperationException($"PowerPoint OPEN 失败：{result.ErrorCode} {result.ErrorDetail}");

        _officePresentationIdentity = Long(result.Result, "presentation_identity");
        _officeHostEpoch = Long(result.Result, "host_epoch");
        _officeSlotEpoch = Long(result.Result, "slot_epoch");
        _currentSlide = Int(result.Result, "current_slide", Int(lease.Args, "target_slide", 1));
        _totalSlides = Int(result.Result, "slide_count", 0);
        return new SurfaceResource("powerpoint", new Grid { Background = WpfBrushes.Black }, DisposePowerPointSurfaceAsync);
    }

    private async Task ControlPptMediaAsync(CommandLeaseDto lease, CancellationToken cancellationToken)
    {
        if (_current?.Kind != "powerpoint")
            throw new InvalidOperationException("当前源不是动态 PowerPoint。");
        var args = new Dictionary<string, JsonElement>
        {
            ["presentation_identity"] = JsonSerializer.SerializeToElement(_officePresentationIdentity),
            ["action"] = JsonSerializer.SerializeToElement(String(lease.Args, "action", "toggle")),
            ["media_id"] = JsonSerializer.SerializeToElement(String(lease.Args, "media_id", string.Empty)),
        };
        if (lease.Args.TryGetValue("media_index", out var mediaIndex)) args["media_index"] = mediaIndex;
        await SendOfficeAsync(lease, "media", args, cancellationToken).ConfigureAwait(false);
    }

    private async Task<OfficeResultDto> SendOfficeAsync(
        CommandLeaseDto lease,
        string operation,
        Dictionary<string, JsonElement> parameters,
        CancellationToken cancellationToken)
    {
        if (_officeSession is null)
            throw new InvalidOperationException("PowerPointHost 管道未连接。");
        parameters.TryAdd("slot_source_generation", JsonSerializer.SerializeToElement(_generation));
        var result = await _officeSession.SendOfficeRequestAsync(new OfficeRequestDto
        {
            OfficeOperationId = OfficeOperationId(lease.CommandId, operation),
            ParentCommandId = lease.CommandId,
            ClaimToken = lease.ClaimToken,
            SourceGeneration = lease.SourceGeneration,
            GroupEpoch = lease.GroupEpoch,
            HostEpoch = _officeHostEpoch,
            SlotEpoch = _officeSlotEpoch,
            Deadline = lease.Deadline ?? DateTimeOffset.UtcNow.AddSeconds(30).ToString("O"),
            Operation = operation,
            Parameters = parameters,
        }, cancellationToken).ConfigureAwait(false);
        if (!string.Equals(result.Status, "succeeded", StringComparison.OrdinalIgnoreCase))
            throw new InvalidOperationException($"PowerPoint 操作 {operation} 失败：{result.ErrorCode} {result.ErrorDetail}");
        return result;
    }

    private async ValueTask DisposePowerPointSurfaceAsync()
    {
        // Office 子窗口由 PowerPointHost 的 CLOSE 子操作关闭；这里不直接触碰跨进程 HWND。
        await ValueTask.CompletedTask;
    }

    private async Task ClosePowerPointAsync(
        CommandLeaseDto lease,
        string stage,
        CancellationToken cancellationToken)
    {
        if (_officeSession is null || _officePresentationIdentity == 0) return;
        var result = await _officeSession.SendOfficeRequestAsync(new OfficeRequestDto
        {
            OfficeOperationId = OfficeOperationId(lease.CommandId, stage),
            ParentCommandId = lease.CommandId,
            ClaimToken = lease.ClaimToken,
            SourceGeneration = lease.SourceGeneration,
            GroupEpoch = lease.GroupEpoch,
            HostEpoch = _officeHostEpoch,
            SlotEpoch = _officeSlotEpoch,
            Deadline = lease.Deadline ?? DateTimeOffset.UtcNow.AddSeconds(30).ToString("O"),
            Operation = "close",
            Parameters = new Dictionary<string, JsonElement>
            {
                ["presentation_identity"] = JsonSerializer.SerializeToElement(_officePresentationIdentity),
                ["slot_source_generation"] = JsonSerializer.SerializeToElement(_generation),
            },
        }, cancellationToken).ConfigureAwait(false);
        if (!string.Equals(result.Status, "succeeded", StringComparison.OrdinalIgnoreCase))
            throw new InvalidOperationException($"PowerPoint 安全关闭失败：{result.ErrorCode} {result.ErrorDetail}");
        _officePresentationIdentity = 0;
        _officeHostEpoch = 0;
        _officeSlotEpoch = 0;
    }

    private static long Long(JsonElement value, string key, long fallback = 0) =>
        value.ValueKind == JsonValueKind.Object && value.TryGetProperty(key, out var item) && item.TryGetInt64(out var parsed)
            ? parsed
            : fallback;

    private static int Int(JsonElement value, string key, int fallback) =>
        value.ValueKind == JsonValueKind.Object && value.TryGetProperty(key, out var item) && item.TryGetInt32(out var parsed)
            ? parsed
            : fallback;

    private static Guid OfficeOperationId(Guid commandId, string stage)
    {
        var bytes = SHA256.HashData(Encoding.UTF8.GetBytes($"{commandId:N}:{stage}"));
        return new Guid(bytes.AsSpan(0, 16));
    }

}
