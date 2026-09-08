using ScpCv.Domain.Model;
using ScpCv.Domain.Rules;

namespace ScpCv.Domain.Tests;

public sealed class PresentationPolicyTests
{
    [Fact]
    public void FreeSlotSelectsPowerPoint()
    {
        var result = PresentationPolicy.ChooseOpen(new("sha:a", true, true, "sha:a", true));

        Assert.True(result.Accepted);
        Assert.Equal(PlaybackMode.PowerPoint, result.Mode);
    }

    [Fact]
    public void BusySlotUsesOnlyFreshMatchingPdf()
    {
        var result = PresentationPolicy.ChooseOpen(new("sha:a", false, true, "sha:a", true));

        Assert.True(result.Accepted);
        Assert.Equal(PlaybackMode.Pdf, result.Mode);
        Assert.Equal("pdf_fallback", result.Code);
    }

    [Theory]
    [InlineData(false, true, "sha:a", true)]
    [InlineData(true, true, "sha:b", true)]
    [InlineData(true, true, "sha:a", false)]
    [InlineData(true, false, "sha:a", true)]
    public void MissingStaleOrMismatchedPdfFailsSafely(
        bool artifactAvailable,
        bool hasDigest,
        string digest,
        bool fresh)
    {
        var result = PresentationPolicy.ChooseOpen(new(
            "sha:a", false, artifactAvailable, hasDigest ? digest : null, fresh));

        Assert.False(result.Accepted);
        Assert.Equal(PlaybackMode.None, result.Mode);
    }

    [Fact]
    public void SlotReleaseNeverAutoUpgradesPdfAndResetOnlyTargetsPowerPoint()
    {
        Assert.False(PresentationPolicy.CanUpgradeAfterSlotRelease(PlaybackMode.Pdf));
        Assert.True(PresentationPolicy.ShouldReset(PlaybackMode.PowerPoint));
        Assert.False(PresentationPolicy.ShouldReset(PlaybackMode.Pdf));
    }
}
