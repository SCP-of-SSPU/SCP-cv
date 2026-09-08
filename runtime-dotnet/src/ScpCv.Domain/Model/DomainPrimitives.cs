namespace ScpCv.Domain.Model;

/// <summary>固定的四个播放输出窗口之一。</summary>
public readonly record struct WindowId
{
    public const int Minimum = 1;
    public const int Maximum = 4;

    public WindowId(int value)
    {
        if (value is < Minimum or > Maximum)
        {
            throw new ArgumentOutOfRangeException(nameof(value), value, "窗口编号必须在 1 到 4 之间。");
        }

        Value = value;
    }

    public int Value { get; }

    public override string ToString() => Value.ToString(System.Globalization.CultureInfo.InvariantCulture);
}

public enum MediaSourceType
{
    Presentation,
    Video,
    Audio,
    Image,
    Web,
    CustomStream,
    RtspStream,
    SrtStream,
}

public enum PlaybackState
{
    Idle,
    Loading,
    Playing,
    Paused,
    Stopped,
    Error,
}

public enum PlaybackMode
{
    None,
    PowerPoint,
    Pdf,
}

#pragma warning disable CA1720 // Single/Double 是现有外部合同中的领域术语。
public enum DisplayMode
{
    Single,
}

public enum BigScreenMode
{
    Single,
    Double,
}
#pragma warning restore CA1720

public enum ScenarioValueState
{
    Unset,
    Empty,
    Set,
}

public enum ScenarioTargetAction
{
    Keep,
    Close,
    Open,
}

public enum CommandTargetKind
{
    Display,
    Audio,
}

public enum CommandStatus
{
    Pending,
    Processing,
    Completed,
    Failed,
    Superseded,
    Uncertain,
}

public enum RuntimeGroupState
{
    Stopped,
    Starting,
    Armed,
    Draining,
    Faulted,
}

public enum WorkerOwnershipState
{
    Starting,
    Online,
    Stale,
    Stopped,
    Faulted,
}

public enum PreparationJobKind
{
    Metadata,
    Preview,
    ShowFormat,
    Pdf,
}

public enum OperationStatus
{
    Queued,
    Running,
    Succeeded,
    Failed,
    Cancelled,
    Uncertain,
}

[Flags]
public enum PlaybackCapability
{
    None = 0,
    Play = 1 << 0,
    Pause = 1 << 1,
    Stop = 1 << 2,
    Seek = 1 << 3,
    Next = 1 << 4,
    Previous = 1 << 5,
    GoTo = 1 << 6,
    Loop = 1 << 7,
    Volume = 1 << 8,
    Mute = 1 << 9,
    SlideMedia = 1 << 10,
    ResetPresentation = 1 << 11,
}
