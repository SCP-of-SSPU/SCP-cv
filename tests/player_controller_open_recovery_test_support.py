#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放器 OPEN 指令失败恢复测试共享替身。
@Project : SCP-cv
@File : player_controller_open_recovery_test_support.py
@Author : Qintsg
@Date : 2026-07-12
'''
from __future__ import annotations


class OpenAdapter:
    """记录 OPEN/close 调用的 adapter 替身。"""

    def __init__(self) -> None:
        """
        初始化调用状态。
        :return: None
        """
        self.open_args: dict[str, object] = {}
        self.goto_items: list[int] = []
        self.volumes: list[int] = []
        self.mutes: list[bool] = []
        self.closed = False
        self.fail_open = False
        self.detached_for_fast_switch = False
        self.restored_after_failed_switch = False

    def open(self, uri: str, window_handle: int, autoplay: bool = True) -> None:
        """
        模拟打开媒体源。
        :param uri: 媒体 URI
        :param window_handle: 窗口句柄
        :param autoplay: 是否自动播放
        :return: None
        :raises RuntimeError: fail_open 为 True 时抛出
        """
        self.open_args = {
            "uri": uri,
            "window_handle": window_handle,
            "autoplay": autoplay,
        }
        if self.fail_open:
            raise RuntimeError("open failed")

    def close(self) -> None:
        """
        记录关闭调用。
        :return: None
        """
        self.closed = True

    def detach_for_fast_switch(self) -> None:
        """
        记录 PPT 嵌入子窗口隐藏调用。
        :return: None
        """
        self.detached_for_fast_switch = True

    def restore_after_failed_switch(self) -> None:
        """
        记录 PPT 嵌入子窗口恢复调用。
        :return: None
        """
        self.restored_after_failed_switch = True

    def goto_item(self, index: int) -> None:
        """
        记录跳页参数。
        :param index: 目标页码
        :return: None
        """
        self.goto_items.append(index)

    def set_volume(self, volume: int) -> None:
        """
        模拟设置音量。
        :param volume: 音量
        :return: None
        """
        self.volumes.append(volume)

    def set_mute(self, muted: bool) -> None:
        """
        模拟设置静音。
        :param muted: 是否静音
        :return: None
        """
        self.mutes.append(muted)


class FailingCloseAdapter:
    """模拟切源后旧适配器释放失败。"""

    def close(self) -> None:
        """抛出延迟清理路径必须隔离的异常。"""
        raise RuntimeError("detached adapter close failed")


class PreheatPoolStub:
    """记录退出阶段预热池释放。"""

    def __init__(self) -> None:
        self.closed = False

    def close_all(self) -> None:
        """记录全部预热资源已释放。"""
        self.closed = True


class WindowStub:
    """记录播放器窗口显示状态的替身。"""

    def __init__(self) -> None:
        """
        初始化调用记录。
        :return: None
        """
        self.calls: list[str] = []
        self.web_container = object()
        self.topmost: list[bool] = []
        self.top_level_window_handle = 5001

    def show_black_screen(self) -> None:
        """
        记录黑屏显示。
        :return: None
        """
        self.calls.append("black")

    def show(self) -> None:
        """
        记录显示窗口。
        :return: None
        """
        self.calls.append("show")

    def raise_(self) -> None:
        """
        记录置顶窗口。
        :return: None
        """
        self.calls.append("raise")

    def set_always_on_top(self, enabled: bool) -> None:
        """
        记录置顶状态切换。
        :param enabled: 是否置顶
        :return: None
        """
        self.topmost.append(enabled)

    def show_web_container(self) -> None:
        """
        记录网页容器显示。
        :return: None
        """
        self.calls.append("web")

    def show_video_container(self) -> None:
        """
        记录视频容器显示。
        :return: None
        """
        self.calls.append("video")

    def prepare_ppt_container(self) -> None:
        """
        记录 PPT 嵌入容器预激活。
        :return: None
        """
        self.calls.append("ppt_container")
