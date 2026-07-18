"""播放指令队列的顺序与覆盖语义测试。"""

from __future__ import annotations

import pytest

from scp_cv.apps.playback.models import MediaSource, PlaybackCommand
from scp_cv.services.playback import control_playback, navigate_content, open_source
from scp_cv.services.playback_commands import (
    acknowledge_playback_command,
    claim_next_playback_command,
)


@pytest.mark.django_db(transaction=True)
def test_consecutive_navigation_commands_are_claimed_in_order(
    media_source_ppt: MediaSource,
) -> None:
    """连续 PPT 翻页必须逐条交付，不能被单槽 pending_command 合并。"""
    open_source(1, media_source_ppt.pk)
    first_open = claim_next_playback_command(1)
    assert first_open is not None
    acknowledge_playback_command(first_open.id)

    navigate_content(1, PlaybackCommand.NEXT)
    navigate_content(1, PlaybackCommand.NEXT)
    navigate_content(1, PlaybackCommand.PREV)

    claimed = []
    while command := claim_next_playback_command(1):
        claimed.append(command.command)
        acknowledge_playback_command(command.id)

    assert claimed == [PlaybackCommand.NEXT, PlaybackCommand.NEXT, PlaybackCommand.PREV]


@pytest.mark.django_db(transaction=True)
def test_new_open_discards_commands_for_previous_content(
    media_source_ppt: MediaSource,
    media_source_video: MediaSource,
) -> None:
    """切换到新源时不得继续执行旧源尚未消费的控制指令。"""
    open_source(1, media_source_ppt.pk)
    first_open = claim_next_playback_command(1)
    assert first_open is not None
    acknowledge_playback_command(first_open.id)

    navigate_content(1, PlaybackCommand.NEXT)
    control_playback(1, PlaybackCommand.PAUSE)
    open_source(1, media_source_video.pk)

    replacement = claim_next_playback_command(1)
    assert replacement is not None
    assert replacement.command == PlaybackCommand.OPEN
    assert replacement.command_args["source_id"] == media_source_video.pk
    acknowledge_playback_command(replacement.id)
    assert claim_next_playback_command(1) is None
