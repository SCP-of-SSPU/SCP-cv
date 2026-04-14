#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
WHEP 客户端：实现 WebRTC-HTTP Egestion Protocol (RFC 9002) 信令交换。
负责与 MediaMTX 进行 SDP Offer/Answer 协商、ICE 候选交换和会话管理。
@Project : SCP-cv
@File : whep_client.py
@Author : Qintsg
@Date : 2026-04-14
'''
from __future__ import annotations

import logging
from typing import Optional
from urllib.parse import urljoin

import requests

logger = logging.getLogger(__name__)


class WhepClient:
    """
    WHEP 客户端：通过 HTTP 与 MediaMTX WHEP 端点协商 WebRTC 会话。

    生命周期：
    1. 创建实例（传入 WHEP 端点 URL）
    2. exchange_sdp() 发送 SDP Offer → 获取 SDP Answer
    3. 可选 send_ice_candidate() 发送迟到的 ICE 候选
    4. disconnect() 终止会话
    """

    def __init__(self, whep_endpoint_url: str) -> None:
        """
        初始化 WHEP 客户端。
        :param whep_endpoint_url: WHEP 端点完整 URL
            （如 http://127.0.0.1:8889/stream/whep）
        """
        self._whep_endpoint_url = whep_endpoint_url
        self._resource_url: Optional[str] = None
        self._session = requests.Session()
        logger.debug("WHEP 客户端已创建（endpoint=%s）", whep_endpoint_url)

    @property
    def resource_url(self) -> Optional[str]:
        """WHEP 会话资源 URL，SDP 交换成功后可用。"""
        return self._resource_url

    def exchange_sdp(self, offer_sdp: str) -> str:
        """
        向 WHEP 端点发送 SDP Offer，获取 SDP Answer。
        成功后记录会话资源 URL 以便后续操作。
        :param offer_sdp: 本地生成的 SDP Offer 文本
        :return: 远端返回的 SDP Answer 文本
        :raises ConnectionError: WHEP 端点无响应或返回非 2xx 状态
        """
        try:
            response = self._session.post(
                self._whep_endpoint_url,
                data=offer_sdp.encode("utf-8"),
                headers={"Content-Type": "application/sdp"},
                timeout=10,
            )
            response.raise_for_status()
        except requests.RequestException as request_error:
            raise ConnectionError(
                f"WHEP SDP 交换失败：{request_error}"
            ) from request_error

        # 提取会话资源 URL（用于 ICE 候选补发和断开连接）
        location_header = response.headers.get("Location", "")
        if location_header:
            if location_header.startswith("http"):
                self._resource_url = location_header
            else:
                # 相对路径 → 拼接基础 URL
                self._resource_url = urljoin(
                    self._whep_endpoint_url, location_header,
                )

        answer_sdp = response.text
        logger.info(
            "WHEP SDP 交换成功（resource=%s）",
            self._resource_url or "未知",
        )
        return answer_sdp

    def send_ice_candidate(self, candidate_sdp_fragment: str) -> None:
        """
        通过 PATCH 向 WHEP 资源发送迟到的 ICE 候选（RFC 8840 格式）。
        仅在 SDP 交换成功后可用。
        :param candidate_sdp_fragment: ICE 候选 SDP 片段
        """
        if self._resource_url is None:
            logger.warning("WHEP 资源 URL 未设置，跳过 ICE 候选发送")
            return

        try:
            self._session.patch(
                self._resource_url,
                data=candidate_sdp_fragment.encode("utf-8"),
                headers={"Content-Type": "application/trickle-ice-sdpfrag"},
                timeout=5,
            )
        except requests.RequestException as patch_error:
            logger.warning("发送 ICE 候选失败：%s", patch_error)

    def disconnect(self) -> None:
        """
        断开 WHEP 会话，通过 DELETE 释放服务端资源。
        幂等操作，重复调用安全。
        """
        if self._resource_url is not None:
            try:
                self._session.delete(self._resource_url, timeout=5)
                logger.info("WHEP 会话已断开")
            except requests.RequestException as delete_error:
                logger.warning("WHEP 断开失败（忽略）：%s", delete_error)
            finally:
                self._resource_url = None

    def close(self) -> None:
        """关闭客户端：断开会话并释放 HTTP 连接池。"""
        self.disconnect()
        self._session.close()
