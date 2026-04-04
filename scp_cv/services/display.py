from __future__ import annotations

from dataclasses import dataclass

from screeninfo import get_monitors


@dataclass(frozen=True)
class DisplayTarget:
    """运行时显示器描述。"""

    index: int
    name: str
    width: int
    height: int
    x: int
    y: int
    is_primary: bool

    @property
    def geometry_label(self) -> str:
        return f"{self.width}×{self.height}"

    @property
    def position_label(self) -> str:
        return f"({self.x}, {self.y})"


@dataclass(frozen=True)
class SplicedDisplayTarget:
    """左右拼接后的逻辑播放区域。"""

    left: DisplayTarget
    right: DisplayTarget
    width: int
    height: int

    @property
    def geometry_label(self) -> str:
        return f"{self.width}×{self.height}"


def list_display_targets() -> list[DisplayTarget]:
    """读取当前主机可见的显示器信息。"""

    display_targets: list[DisplayTarget] = []
    for index, monitor in enumerate(get_monitors(), start=1):
        monitor_name = getattr(monitor, "name", "") or f"显示器 {index}"
        display_targets.append(
            DisplayTarget(
                index=index,
                name=monitor_name,
                width=int(getattr(monitor, "width", 0)),
                height=int(getattr(monitor, "height", 0)),
                x=int(getattr(monitor, "x", 0)),
                y=int(getattr(monitor, "y", 0)),
                is_primary=bool(getattr(monitor, "is_primary", index == 1)),
            )
        )
    return display_targets


def build_left_right_splice_target(display_targets: list[DisplayTarget]) -> SplicedDisplayTarget | None:
    """把最左与次左显示器组合成一个逻辑拼接区域。"""

    if len(display_targets) < 2:
        return None

    ordered_targets = sorted(display_targets, key=lambda item: (item.x, item.y))
    left_target = ordered_targets[0]
    right_target = ordered_targets[1]
    return SplicedDisplayTarget(
        left=left_target,
        right=right_target,
        width=left_target.width + right_target.width,
        height=max(left_target.height, right_target.height),
    )
