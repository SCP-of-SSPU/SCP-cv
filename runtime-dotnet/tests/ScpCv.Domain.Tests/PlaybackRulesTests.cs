using ScpCv.Domain.Model;
using ScpCv.Domain.Rules;

namespace ScpCv.Domain.Tests;

public sealed class PlaybackRulesTests
{
    [Theory]
    [InlineData(BigScreenMode.Single, 2, true)]
    [InlineData(BigScreenMode.Single, 3, true)]
    [InlineData(BigScreenMode.Single, 4, true)]
    [InlineData(BigScreenMode.Single, 1, false)]
    [InlineData(BigScreenMode.Double, 1, false)]
    [InlineData(BigScreenMode.Double, 2, false)]
    [InlineData(BigScreenMode.Double, 3, true)]
    [InlineData(BigScreenMode.Double, 4, true)]
    public void RuntimeMuteRuleMatchesExistingFourWindowLayout(
        BigScreenMode mode,
        int windowId,
        bool expected)
    {
        Assert.Equal(expected, PlaybackRules.IsMutedByRuntime(new WindowId(windowId), mode));
    }

    [Theory]
    [InlineData(MediaSourceType.Video, true, true)]
    [InlineData(MediaSourceType.CustomStream, true, false)]
    [InlineData(MediaSourceType.RtspStream, true, false)]
    [InlineData(MediaSourceType.SrtStream, true, false)]
    [InlineData(MediaSourceType.Presentation, false, false)]
    [InlineData(MediaSourceType.Audio, false, false)]
    [InlineData(MediaSourceType.Image, false, false)]
    [InlineData(MediaSourceType.Web, false, false)]
    public void WindowAudioAndLoopCapabilitiesMatchExistingSourceRules(
        MediaSourceType sourceType,
        bool supportsAudio,
        bool supportsLoop)
    {
        var capabilities = PlaybackRules.GetWindowCapabilities(sourceType, PlaybackMode.None);

        Assert.Equal(supportsAudio, capabilities.HasFlag(PlaybackCapability.Volume));
        Assert.Equal(supportsAudio, capabilities.HasFlag(PlaybackCapability.Mute));
        Assert.Equal(supportsLoop, capabilities.HasFlag(PlaybackCapability.Loop));
    }

    [Theory]
    [InlineData(ScenarioValueState.Unset, null, ScenarioTargetAction.Keep)]
    [InlineData(ScenarioValueState.Empty, null, ScenarioTargetAction.Close)]
    [InlineData(ScenarioValueState.Set, null, ScenarioTargetAction.Keep)]
    [InlineData(ScenarioValueState.Set, 42L, ScenarioTargetAction.Open)]
    public void ScenarioTargetKeepsExistingThreeStateBehavior(
        ScenarioValueState state,
        long? sourceId,
        ScenarioTargetAction expected)
    {
        Assert.Equal(expected, PlaybackRules.GetScenarioTargetAction(state, sourceId));
    }

    [Fact]
    public void ActualPresentationAdapterControlsDynamicPowerPointCapabilities()
    {
        var powerPoint = PlaybackRules.GetWindowCapabilities(
            MediaSourceType.Presentation,
            PlaybackMode.PowerPoint);
        var pdf = PlaybackRules.GetWindowCapabilities(
            MediaSourceType.Presentation,
            PlaybackMode.Pdf);

        Assert.True(powerPoint.HasFlag(PlaybackCapability.SlideMedia));
        Assert.True(powerPoint.HasFlag(PlaybackCapability.ResetPresentation));
        Assert.False(pdf.HasFlag(PlaybackCapability.SlideMedia));
        Assert.False(pdf.HasFlag(PlaybackCapability.ResetPresentation));
        Assert.Equal(
            PlaybackMode.None,
            PlaybackRules.NormalizeReportedPlaybackMode(MediaSourceType.Video, PlaybackMode.PowerPoint));
    }
}
