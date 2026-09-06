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
