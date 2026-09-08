using ScpCv.Domain.Model;

namespace ScpCv.Domain.Rules;

public sealed record PresentationOpenRequest(
    string SourceDigest,
    bool DynamicSlotAvailable,
    bool PdfArtifactAvailable,
    string? PdfArtifactDigest,
    bool PdfArtifactFresh);

public sealed record PresentationDecision(
    bool Accepted,
    PlaybackMode Mode,
    string Code,
    bool CanAutoUpgrade);

/// <summary>唯一 PowerPoint 槽位与源版本匹配 PDF 回退的纯策略。</summary>
public static class PresentationPolicy
{
    public static PresentationDecision ChooseOpen(PresentationOpenRequest request)
    {
        ArgumentNullException.ThrowIfNull(request);
        if (request.DynamicSlotAvailable)
        {
            return new PresentationDecision(true, PlaybackMode.PowerPoint, "powerpoint_slot_acquired", false);
        }

        if (request.PdfArtifactAvailable &&
            request.PdfArtifactFresh &&
            !string.IsNullOrWhiteSpace(request.PdfArtifactDigest) &&
            string.Equals(request.SourceDigest, request.PdfArtifactDigest, StringComparison.Ordinal))
        {
            return new PresentationDecision(true, PlaybackMode.Pdf, "pdf_fallback", false);
        }

        return new PresentationDecision(false, PlaybackMode.None, "matching_pdf_unavailable", false);
    }

    public static bool ShouldReset(PlaybackMode actualMode) => actualMode == PlaybackMode.PowerPoint;

    public static bool CanUpgradeAfterSlotRelease(PlaybackMode actualMode) => false;
}
