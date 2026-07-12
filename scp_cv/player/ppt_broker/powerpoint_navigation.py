#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PowerPoint Broker 放映导航内部 helper。
@Project : SCP-cv
@File : powerpoint_navigation.py
@Author : Qintsg
@Date : 2026-07-11
'''
from __future__ import annotations

from typing import Protocol

from scp_cv.player.ppt_broker.com_support import is_transient_com_error


class NavigationSession(Protocol):
    """导航 helper 所需的最小会话形状。"""

    view: object | None
    current_slide: int
    total_slides: int


def next_slide(session: NavigationSession) -> None:
    """推进到下一动画点击或下一页。"""
    if session.view is None:
        return
    next_click = getattr(session.view, "GotoNextClick", None)
    if callable(next_click):
        try:
            next_click()
        except Exception as click_error:
            if is_transient_com_error(click_error):
                raise
            session.view.Next()  # type: ignore[attr-defined]
    elif session.current_slide < session.total_slides:
        session.view.Next()  # type: ignore[attr-defined]
    session.current_slide = int(
        session.view.CurrentShowPosition or session.current_slide  # type: ignore[attr-defined]
    )


def previous_slide(session: NavigationSession) -> None:
    """回到上一动画点击或上一页。"""
    if session.view is None:
        return
    previous_click = getattr(session.view, "GotoPreClick", None)
    if callable(previous_click):
        try:
            previous_click()
        except Exception as click_error:
            if is_transient_com_error(click_error):
                raise
            session.view.Previous()  # type: ignore[attr-defined]
    elif session.current_slide > 1:
        session.view.Previous()  # type: ignore[attr-defined]
    session.current_slide = int(
        session.view.CurrentShowPosition or session.current_slide  # type: ignore[attr-defined]
    )


def goto_slide(session: NavigationSession, slide_index: int) -> None:
    """跳转到指定页。"""
    if slide_index > session.total_slides:
        raise ValueError(
            f"PPT 页码 {slide_index} 超出总页数 {session.total_slides}"
        )
    if session.view is None:
        session.current_slide = slide_index
        return
    try:
        session.view.GotoSlide(slide_index)  # type: ignore[attr-defined]
    except TypeError:
        session.view.GotoSlide(slide_index, False)  # type: ignore[attr-defined]
    session.current_slide = slide_index


__all__ = ["goto_slide", "next_slide", "previous_slide"]
