using ScpCv.Domain.Model;

namespace ScpCv.Domain.Rules;

/// <summary>
/// 与播放宿主和持久化无关的核心播控规则。调用方只提交领域值，规则返回决策，
/// 不在此模块内产生设备、数据库或播放器副作用。
/// </summary>
public static class PlaybackRules
{
    public static bool IsMutedByRuntime(WindowId windowId, BigScreenMode mode) =>
        windowId.Value is 3 or 4 || (mode == BigScreenMode.Single && windowId.Value == 2);

    public static PlaybackCapability GetWindowCapabilities(
        MediaSourceType sourceType,
        PlaybackMode actualPlaybackMode)
    {
        const PlaybackCapability transport =
            PlaybackCapability.Play | PlaybackCapability.Pause | PlaybackCapability.Stop;
        const PlaybackCapability audio = PlaybackCapability.Volume | PlaybackCapability.Mute;

        return sourceType switch
        {
            MediaSourceType.Presentation => PresentationCapabilities(actualPlaybackMode),
            MediaSourceType.Video => transport | audio | PlaybackCapability.Seek | PlaybackCapability.Loop,
            MediaSourceType.CustomStream or MediaSourceType.RtspStream or MediaSourceType.SrtStream =>
                transport | audio,
            MediaSourceType.Web => PlaybackCapability.Play,
            _ => PlaybackCapability.None,
        };
    }

    public static ScenarioTargetAction GetScenarioTargetAction(
        ScenarioValueState state,
        long? sourceId) => state switch
        {
            ScenarioValueState.Unset => ScenarioTargetAction.Keep,
            ScenarioValueState.Empty => ScenarioTargetAction.Close,
            ScenarioValueState.Set when sourceId is > 0 => ScenarioTargetAction.Open,
            ScenarioValueState.Set => ScenarioTargetAction.Keep,
            _ => throw new ArgumentOutOfRangeException(nameof(state), state, "未知的预案目标状态。"),
        };

    /// <summary>
    /// playback_mode 是播放器实际适配器上报的运行事实；非演示文稿源始终投影为空，
    /// 不能从媒体源偏好反推 PowerPoint 或 PDF。
    /// </summary>
    public static PlaybackMode NormalizeReportedPlaybackMode(
        MediaSourceType sourceType,
        PlaybackMode reportedMode) =>
        sourceType == MediaSourceType.Presentation &&
        reportedMode is PlaybackMode.PowerPoint or PlaybackMode.Pdf
            ? reportedMode
            : PlaybackMode.None;

    private static PlaybackCapability PresentationCapabilities(PlaybackMode actualPlaybackMode)
    {
        var capabilities = PlaybackCapability.Next | PlaybackCapability.Previous | PlaybackCapability.GoTo;
        if (actualPlaybackMode == PlaybackMode.PowerPoint)
        {
            capabilities |= PlaybackCapability.SlideMedia | PlaybackCapability.ResetPresentation;
        }

        return capabilities;
    }
}
