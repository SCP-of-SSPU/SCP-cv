#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
媒体源适配器包，提供统一的适配器工厂函数。
根据 SourceType 创建对应的适配器实例。
@Project : SCP-cv
@File : __init__.py
@Author : Qintsg
@Date : 2026-04-15
'''
from __future__ import annotations

import logging

from scp_cv.player.adapters.base import AdapterState, SourceAdapter

logger = logging.getLogger(__name__)

# 源类型 → 适配器类的延迟映射（避免启动时导入所有依赖）
_ADAPTER_CLASS_MAP: dict[str, str] = {
    "ppt": "scp_cv.player.adapters.ppt.PptSourceAdapter",
    "video": "scp_cv.player.adapters.video.VideoSourceAdapter",
    "audio": "scp_cv.player.adapters.video.VideoSourceAdapter",  # 音频复用视频适配器
    "image": "scp_cv.player.adapters.image.ImageSourceAdapter",
    "web": "scp_cv.player.adapters.web.WebSourceAdapter",
    "webrtc_stream": "scp_cv.player.adapters.webrtc_stream.WebRTCStreamAdapter",
    "custom_stream": "scp_cv.player.adapters.webrtc_stream.WebRTCStreamAdapter",
}


def create_adapter(source_type: str) -> SourceAdapter:
    """
    根据源类型创建对应的适配器实例。
    :param source_type: SourceType 枚举值
    :return: 适配器实例
    :raises ValueError: 不支持的源类型
    """
    class_path = _ADAPTER_CLASS_MAP.get(source_type)
    if class_path is None:
        raise ValueError(f"不支持的媒体源类型：{source_type}")

    # 延迟导入适配器类
    module_path, class_name = class_path.rsplit(".", 1)
    import importlib
    module = importlib.import_module(module_path)
    adapter_class = getattr(module, class_name)

    adapter_instance: SourceAdapter = adapter_class()
    logger.info("创建适配器：%s → %s", source_type, class_name)
    return adapter_instance


__all__ = [
    "AdapterState",
    "SourceAdapter",
    "create_adapter",
]
