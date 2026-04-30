#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
系统音量管理服务，优先通过 Windows Core Audio 同步系统主音量。
无法访问系统音频端点时回退到 RuntimeState，保证控制台仍可运行。
@Project : SCP-cv
@File : volume.py
@Author : Qintsg
@Date : 2026-04-30
'''
from __future__ import annotations

import ctypes
import logging
import sys
from uuid import UUID

from scp_cv.apps.playback.models import RuntimeState

logger = logging.getLogger(__name__)


class VolumeError(Exception):
    """音量操作过程中的业务异常。"""


class _ComGuid(ctypes.Structure):
    """Windows COM GUID 结构。"""

    _fields_ = [
        ("Data1", ctypes.c_ulong),
        ("Data2", ctypes.c_ushort),
        ("Data3", ctypes.c_ushort),
        ("Data4", ctypes.c_ubyte * 8),
    ]

    def __init__(self, guid_text: str) -> None:
        """
        从标准 GUID 字符串构造 COM GUID。
        :param guid_text: GUID 字符串
        :return: None
        """
        guid = UUID(guid_text)
        data4 = (ctypes.c_ubyte * 8).from_buffer_copy(guid.bytes[8:])
        super().__init__(guid.time_low, guid.time_mid, guid.time_hi_version, data4)


_CLSID_MM_DEVICE_ENUMERATOR = _ComGuid("bcde0395-e52f-467c-8e3d-c4579291692e")
_IID_IMM_DEVICE_ENUMERATOR = _ComGuid("a95664d2-9614-4f35-a746-de8db63617e6")
_IID_IAUDIO_ENDPOINT_VOLUME = _ComGuid("5cdf2c82-841e-4546-9722-0cf74078229a")
_CLSCTX_ALL = 23
_E_RENDER = 0
_E_CONSOLE = 0


def get_system_volume() -> dict[str, object]:
    """
    获取当前系统音量状态。
    :return: 包含 level、muted、system_synced 和 backend 的字典
    """
    runtime = RuntimeState.get_instance()
    try:
        level, muted = _get_windows_master_volume()
        runtime.volume_level = level
        runtime.volume_muted = muted
        runtime.save(update_fields=["volume_level", "volume_muted", "updated_at"])
        return _volume_payload(level, muted, True, "windows_core_audio")
    except VolumeError as volume_error:
        logger.warning("读取 Windows 系统音量失败，使用运行态音量：%s", volume_error)
        return _volume_payload(runtime.volume_level, runtime.volume_muted, False, "runtime_state")


def set_system_volume(level: int | None = None, muted: bool | None = None) -> dict[str, object]:
    """
    设置系统音量或静音状态。
    :param level: 音量等级（0-100），None 表示不修改音量
    :param muted: 静音状态，None 表示不修改静音
    :return: 更新后的音量状态
    :raises VolumeError: 音量值无效时
    """
    runtime = RuntimeState.get_instance()
    normalized_level = runtime.volume_level if level is None else max(0, min(100, int(level)))
    if muted is None:
        normalized_muted = True if normalized_level == 0 else runtime.volume_muted
    else:
        normalized_muted = bool(muted)
    try:
        _set_windows_master_volume(normalized_level, normalized_muted)
        actual_level, actual_muted = _get_windows_master_volume()
        runtime.volume_level = actual_level
        runtime.volume_muted = actual_muted
        runtime.save(update_fields=["volume_level", "volume_muted", "updated_at"])
        logger.info("Windows 系统音量已同步：level=%d, muted=%s", actual_level, actual_muted)
        return _volume_payload(actual_level, actual_muted, True, "windows_core_audio")
    except VolumeError as volume_error:
        runtime.volume_level = normalized_level
        runtime.volume_muted = normalized_muted
        runtime.save(update_fields=["volume_level", "volume_muted", "updated_at"])
        logger.warning("设置 Windows 系统音量失败，已写入运行态：%s", volume_error)
        return _volume_payload(normalized_level, normalized_muted, False, "runtime_state")


def _volume_payload(level: int, muted: bool, system_synced: bool, backend: str) -> dict[str, object]:
    """构造统一音量响应。"""
    return {
        "level": max(0, min(100, int(level))),
        "muted": bool(muted),
        "system_synced": system_synced,
        "backend": backend,
    }


def _get_windows_master_volume() -> tuple[int, bool]:
    """
    读取 Windows 默认播放设备主音量。
    :return: (音量等级, 是否静音)
    :raises VolumeError: 非 Windows 或 Core Audio 调用失败时
    """
    endpoint = _activate_audio_endpoint()
    try:
        scalar = ctypes.c_float()
        muted = ctypes.c_int()
        _com_call(endpoint, 9, ctypes.c_long, [ctypes.POINTER(ctypes.c_float)], ctypes.byref(scalar))
        _com_call(endpoint, 15, ctypes.c_long, [ctypes.POINTER(ctypes.c_int)], ctypes.byref(muted))
        return round(float(scalar.value) * 100), bool(muted.value)
    finally:
        _release(endpoint)
        _co_uninitialize()


def _set_windows_master_volume(level: int, muted: bool) -> None:
    """
    设置 Windows 默认播放设备主音量和静音状态。
    :param level: 音量等级（0-100）
    :param muted: 是否静音
    :return: None
    :raises VolumeError: 非 Windows 或 Core Audio 调用失败时
    """
    endpoint = _activate_audio_endpoint()
    try:
        scalar = ctypes.c_float(max(0, min(100, int(level))) / 100)
        _com_call(endpoint, 7, ctypes.c_long, [ctypes.c_float, ctypes.c_void_p], scalar, None)
        _com_call(endpoint, 14, ctypes.c_long, [ctypes.c_int, ctypes.c_void_p], int(muted), None)
    finally:
        _release(endpoint)
        _co_uninitialize()


def _activate_audio_endpoint() -> ctypes.c_void_p:
    """
    激活默认渲染设备的 IAudioEndpointVolume 接口。
    :return: IAudioEndpointVolume COM 指针
    :raises VolumeError: Core Audio 不可用时
    """
    if not sys.platform.startswith("win"):
        raise VolumeError("当前平台不支持 Windows Core Audio")
    ole32 = ctypes.windll.ole32
    ole32.CoInitialize(None)
    enumerator = ctypes.c_void_p()
    device = ctypes.c_void_p()
    endpoint = ctypes.c_void_p()
    try:
        _check_hresult(ole32.CoCreateInstance(
            ctypes.byref(_CLSID_MM_DEVICE_ENUMERATOR),
            None,
            _CLSCTX_ALL,
            ctypes.byref(_IID_IMM_DEVICE_ENUMERATOR),
            ctypes.byref(enumerator),
        ))
        _com_call(
            enumerator,
            4,
            ctypes.c_long,
            [ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)],
            _E_RENDER,
            _E_CONSOLE,
            ctypes.byref(device),
        )
        _com_call(
            device,
            3,
            ctypes.c_long,
            [ctypes.POINTER(_ComGuid), ctypes.c_ulong, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)],
            ctypes.byref(_IID_IAUDIO_ENDPOINT_VOLUME),
            _CLSCTX_ALL,
            None,
            ctypes.byref(endpoint),
        )
        return endpoint
    except VolumeError:
        _release(endpoint)
        _co_uninitialize()
        raise
    finally:
        _release(device)
        _release(enumerator)


def _com_call(
    com_pointer: ctypes.c_void_p,
    method_index: int,
    result_type: object,
    argument_types: list[object],
    *arguments: object,
) -> object:
    """
    调用 COM vtable 方法并检查 HRESULT。
    :param com_pointer: COM 接口指针
    :param method_index: vtable 方法索引
    :param result_type: 返回类型
    :param argument_types: 除 this 外的方法参数类型
    :param arguments: 方法参数
    :return: 方法返回值
    """
    if not com_pointer:
        raise VolumeError("COM 指针为空")
    vtable = ctypes.cast(com_pointer, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    method = ctypes.WINFUNCTYPE(result_type, ctypes.c_void_p, *argument_types)(vtable[method_index])
    result = method(com_pointer, *arguments)
    if result_type is ctypes.c_long:
        _check_hresult(result)
    return result


def _release(com_pointer: ctypes.c_void_p) -> None:
    """释放 COM 指针，空指针自动忽略。"""
    if not com_pointer:
        return
    try:
        _com_call(com_pointer, 2, ctypes.c_ulong, [])
    except VolumeError:
        pass


def _co_uninitialize() -> None:
    """结束当前线程 COM 初始化，非 Windows 或未初始化时静默忽略。"""
    if not sys.platform.startswith("win"):
        return
    try:
        ctypes.windll.ole32.CoUninitialize()
    except OSError:
        pass


def _check_hresult(result: int) -> None:
    """
    检查 HRESULT，失败时抛出业务异常。
    :param result: HRESULT
    :return: None
    :raises VolumeError: HRESULT 表示失败时
    """
    if int(result) < 0:
        raise VolumeError(f"Windows Core Audio 调用失败：HRESULT={result}")
