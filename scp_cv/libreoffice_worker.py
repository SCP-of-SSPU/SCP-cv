#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
LibreOffice Python worker，隔离 pyuno 与项目 Python 版本差异。
@Project : SCP-cv
@File : libreoffice_worker.py
@Author : Qintsg
@Date : 2026-05-27
'''
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import uuid
from pathlib import Path
from typing import Any, Optional


class WorkerError(RuntimeError):
    """LibreOffice worker 执行失败。"""


class LibreOfficeSession:
    """LibreOffice 隔离进程和 UNO 上下文。"""

    def __init__(self, process: subprocess.Popen[bytes], profile_dir: Path, context: Any, desktop: Any, uno: Any) -> None:
        """
        初始化 LibreOffice 会话。
        :param process: soffice 子进程
        :param profile_dir: 独立 UserInstallation 目录
        :param context: 远端 ComponentContext
        :param desktop: com.sun.star.frame.Desktop 实例
        :param uno: pyuno 模块
        :return: None
        """
        self.process = process
        self.profile_dir = profile_dir
        self.context = context
        self.desktop = desktop
        self.uno = uno

    def property_value(self, name: str, value: object) -> Any:
        """
        创建 UNO PropertyValue。
        :param name: 属性名
        :param value: 属性值
        :return: com.sun.star.beans.PropertyValue
        """
        property_value = self.uno.createUnoStruct("com.sun.star.beans.PropertyValue")
        property_value.Name = name
        property_value.Value = value
        return property_value

    def path_to_file_url(self, path: Path) -> str:
        """
        将系统路径转换为 UNO file URL。
        :param path: 本地路径
        :return: file URL
        """
        return self.uno.systemPathToFileUrl(str(path.resolve()))

    def close(self) -> None:
        """
        终止 LibreOffice 进程并清理隔离 profile。
        :return: None
        """
        try:
            self.desktop.terminate()
        except Exception:
            pass
        _terminate_process(self.process)
        shutil.rmtree(self.profile_dir, ignore_errors=True)


class LibreOfficeBridge:
    """LibreOffice 交互式放映 worker。"""

    def __init__(self) -> None:
        """
        初始化 bridge 状态。
        :return: None
        """
        self.session: Optional[LibreOfficeSession] = None
        self.document: Optional[object] = None
        self.presentation: Optional[object] = None
        self.controller: Optional[object] = None
        self.total_slides = 0
        self.last_slide_index = 1
        self.is_paused = False

    def open(self, file_path: Path, autoplay: bool) -> dict[str, object]:
        """
        打开文档并按需启动放映。
        :param file_path: PPT 文件路径
        :param autoplay: 是否立即开始放映
        :return: 状态响应
        """
        self.close_document()
        if self.session is None:
            self.session = _start_session(headless=False)
        self.document = self._load_document_with_retry(file_path, hidden=False, readonly=True)
        self.presentation = self.document.getPresentation()  # type: ignore[attr-defined]
        self._configure_presentation()
        self.total_slides = self._read_slide_count()
        self.last_slide_index = 1 if self.total_slides else 0
        if autoplay:
            self._start_slideshow(self.last_slide_index or 1)
        return self.state_payload()

    def preheat(self) -> dict[str, object]:
        """
        预启动 LibreOffice 会话但不打开文档。
        :return: 状态响应
        """
        if self.session is None:
            self.session = _start_session(headless=False)
        return self.state_payload()

    def close_document(self) -> dict[str, object]:
        """
        关闭当前文档但保留 LibreOffice 会话。
        :return: 状态响应
        """
        self._end_presentation()
        if self.document is not None:
            _close_document(self.document)
            self.document = None
        self.presentation = None
        self.controller = None
        self.total_slides = 0
        self.last_slide_index = 0
        self.is_paused = False
        return self.state_payload()

    def _load_document_with_retry(self, file_path: Path, hidden: bool, readonly: bool) -> object:
        """
        加载文档；LibreOffice 冷启动后 UNO bridge 偶发断开时重建一次会话。
        :param file_path: PPT 文件路径
        :param hidden: 是否隐藏文档窗口
        :param readonly: 是否只读打开
        :return: UNO 文档对象
        """
        if self.session is None:
            raise WorkerError("LibreOffice 会话未初始化")
        try:
            return _load_document(self.session, file_path, hidden=hidden, readonly=readonly)
        except Exception as load_error:
            if not _is_recoverable_bridge_dispose_error(load_error):
                raise
            self.session.close()
            self.session = _start_session(headless=False)
            return _load_document(self.session, file_path, hidden=hidden, readonly=readonly)

    def close(self) -> dict[str, object]:
        """
        关闭文档和 LibreOffice 会话。
        :return: 状态响应
        """
        self.close_document()
        if self.session is not None:
            self.session.close()
            self.session = None
        return self.state_payload()

    def play(self) -> dict[str, object]:
        """
        开始或恢复放映。
        :return: 状态响应
        """
        if self.controller is None and self.presentation is not None:
            self._start_slideshow(self.last_slide_index or 1)
        elif self.controller is not None and self.is_paused:
            self.controller.resume()  # type: ignore[attr-defined]
            self.is_paused = False
        return self.state_payload()

    def pause(self) -> dict[str, object]:
        """
        暂停放映。
        :return: 状态响应
        """
        if self.controller is not None and not self.is_paused:
            self.controller.pause()  # type: ignore[attr-defined]
            self.is_paused = True
        return self.state_payload()

    def stop(self) -> dict[str, object]:
        """
        停止放映但保留文档。
        :return: 状态响应
        """
        if self.controller is not None:
            self.last_slide_index = self._current_slide_index()
        self._end_presentation()
        self.controller = None
        self.is_paused = False
        return self.state_payload()

    def next_item(self) -> dict[str, object]:
        """
        推进下一动画或下一页。
        :return: 状态响应
        """
        if self.controller is not None and self._presentation_is_running():
            self.controller.gotoNextEffect()  # type: ignore[attr-defined]
            self.last_slide_index = self._current_slide_index()
        return self.state_payload()

    def prev_item(self) -> dict[str, object]:
        """
        回退上一动画或上一页。
        :return: 状态响应
        """
        if self.controller is not None and self._presentation_is_running():
            self.controller.gotoPreviousEffect()  # type: ignore[attr-defined]
            self.last_slide_index = self._current_slide_index()
        return self.state_payload()

    def goto_item(self, index: int) -> dict[str, object]:
        """
        跳转到指定页。
        :param index: 目标页码，1-based
        :return: 状态响应
        """
        if self.controller is not None and self._presentation_is_running() and 1 <= index <= self.total_slides:
            self.controller.gotoSlideIndex(index - 1)  # type: ignore[attr-defined]
            self.last_slide_index = index
        return self.state_payload()

    def control_media(self, media_id: str, action: str, media_index: int) -> dict[str, object]:
        """
        控制当前页媒体对象。
        :param media_id: 媒体对象标识
        :param action: 控制动作
        :param media_index: 当前页媒体序号
        :return: 状态响应
        """
        if self.controller is not None:
            from scp_cv.player.adapters.ppt_libreoffice_media import control_libreoffice_media

            control_libreoffice_media(
                self.controller,
                self.document,
                _StderrLogger(),
                media_id,
                action,
                media_index,
                self._current_slide_index(),
            )
            normalized_action = action.lower().strip()
            if normalized_action == "pause":
                self.is_paused = True
            elif normalized_action == "play":
                self.is_paused = False
        return self.state_payload()

    def state_payload(self) -> dict[str, object]:
        """
        返回当前放映状态。
        :return: 状态字典
        """
        process_id = self.session.process.pid if self.session is not None else 0
        if self.controller is not None and self._presentation_is_running():
            playback_state = "paused" if self._controller_is_paused() else "playing"
            current_slide = self._current_slide_index()
        elif self.document is not None:
            playback_state = "stopped"
            current_slide = self.last_slide_index if self.total_slides else 0
        else:
            playback_state = "idle"
            current_slide = 0
        return {
            "playback_state": playback_state,
            "current_slide": current_slide,
            "total_slides": self.total_slides,
            "process_id": process_id,
        }

    def _configure_presentation(self) -> None:
        """配置 Impress 放映属性。"""
        if self.presentation is None:
            return
        for property_name, value in (
            ("AllowAnimations", True),
            ("IsFullScreen", False),
            ("IsAlwaysOnTop", False),
            ("IsEndless", False),
            ("IsMouseVisible", False),
            ("StartWithNavigator", False),
        ):
            try:
                setattr(self.presentation, property_name, value)
            except Exception:
                pass

    def _start_slideshow(self, start_slide: int) -> None:
        """启动放映并按需跳页。"""
        if self.presentation is None:
            return
        start_errors: list[BaseException] = []
        start_thread = threading.Thread(
            target=_invoke_presentation_start,
            args=(self.presentation, start_errors),
            daemon=True,
            name="libreoffice-slideshow-start",
        )
        start_thread.start()
        self.controller = self._wait_for_controller(start_errors)
        self.is_paused = False
        if start_slide > 1 and self.controller is not None:
            self.controller.gotoSlideIndex(start_slide - 1)  # type: ignore[attr-defined]
            self.last_slide_index = start_slide

    def _wait_for_controller(self, start_errors: list[BaseException]) -> object:
        """等待 SlideShowController 创建。"""
        if self.presentation is None:
            raise WorkerError("LibreOffice Presentation 未初始化")
        deadline = time.monotonic() + _bridge_command_timeout_seconds()
        last_error: Optional[Exception] = None
        while time.monotonic() < deadline:
            if start_errors:
                raise WorkerError(f"LibreOffice 放映启动失败：{start_errors[0]}")
            try:
                controller = self.presentation.getController()  # type: ignore[attr-defined]
                if controller is not None:
                    return controller
            except Exception as controller_error:
                last_error = controller_error
            time.sleep(0.1)
        raise WorkerError(f"获取 LibreOffice 放映控制器超时：{last_error}")

    def _read_slide_count(self) -> int:
        """读取文档页数。"""
        if self.document is None:
            return 0
        try:
            return int(self.document.getDrawPages().getCount())  # type: ignore[attr-defined]
        except Exception:
            if self.controller is None:
                return 0
            try:
                return int(self.controller.getSlideCount())  # type: ignore[attr-defined]
            except Exception:
                return 0

    def _current_slide_index(self) -> int:
        """读取当前页码，返回 1-based。"""
        if self.controller is None:
            return self.last_slide_index if self.total_slides else 0
        try:
            current_slide = int(self.controller.getCurrentSlideIndex()) + 1  # type: ignore[attr-defined]
        except Exception:
            return self.last_slide_index if self.total_slides else 0
        if current_slide > 0:
            self.last_slide_index = current_slide
        return self.last_slide_index

    def _controller_is_paused(self) -> bool:
        """读取控制器暂停状态。"""
        if self.controller is None:
            return self.is_paused
        try:
            self.is_paused = bool(self.controller.isPaused())  # type: ignore[attr-defined]
        except Exception:
            pass
        return self.is_paused

    def _presentation_is_running(self) -> bool:
        """判断放映是否运行。"""
        if self.presentation is None:
            return False
        is_running = getattr(self.presentation, "isRunning", None)
        if is_running is None:
            return self.controller is not None
        try:
            return bool(is_running())
        except Exception:
            return self.controller is not None

    def _end_presentation(self) -> None:
        """结束当前放映。"""
        if self.presentation is None:
            return
        try:
            self.presentation.end()  # type: ignore[attr-defined]
        except Exception:
            pass


class _StderrLogger:
    """供媒体控制工具复用的轻量日志器。"""

    def warning(self, message: str, *args: object) -> None:
        """输出 warning 到 stderr。"""
        text = message % args if args else message
        print(text, file=sys.stderr, flush=True)


def main(argv: list[str] | None = None) -> int:
    """
    LibreOffice worker 命令入口。
    :param argv: 命令参数
    :return: 退出码
    """
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        _write_result(False, error="usage: libreoffice_worker <preview|bridge> ...")
        return 2
    if args[0] == "preview":
        return _preview_main(args[1:])
    if args[0] == "bridge":
        return _bridge_main()
    _write_result(False, error=f"unknown command: {args[0]}")
    return 2


def _preview_main(args: list[str]) -> int:
    """执行 PPT PNG 预览导出。"""
    if len(args) != 2:
        _write_result(False, error="usage: libreoffice_worker preview <file_path> <output_dir>")
        return 2
    try:
        previews = _export_previews(Path(args[0]), Path(args[1]))
    except Exception as preview_error:
        traceback.print_exc(file=sys.stderr)
        _write_result(False, error=str(preview_error))
        return 1
    _write_result(True, previews=previews)
    return 0


def _bridge_main() -> int:
    """执行交互式放映 bridge。"""
    bridge = LibreOfficeBridge()
    try:
        for line in sys.stdin:
            if not line.strip():
                continue
            response = _handle_bridge_command(bridge, line)
            print(json.dumps(response, ensure_ascii=False), flush=True)
            if response.get("command") == "shutdown":
                break
    finally:
        bridge.close()
    return 0


def _handle_bridge_command(bridge: LibreOfficeBridge, line: str) -> dict[str, object]:
    """处理单个 bridge JSON 命令。"""
    request_id = None
    command = ""
    try:
        request = json.loads(line)
        request_id = request.get("id")
        command = str(request.get("command", ""))
        payload = request.get("payload") if isinstance(request.get("payload"), dict) else {}
        data = _execute_bridge_command(bridge, command, payload)
        return {"id": request_id, "command": command, "success": True, "data": data, "error": ""}
    except Exception as command_error:
        traceback.print_exc(file=sys.stderr)
        return {"id": request_id, "command": command, "success": False, "data": {}, "error": str(command_error)}


def _execute_bridge_command(bridge: LibreOfficeBridge, command: str, payload: dict[str, object]) -> dict[str, object]:
    """分发 bridge 命令。"""
    if command == "open":
        return bridge.open(Path(str(payload.get("file_path", ""))), bool(payload.get("autoplay", True)))
    if command == "preheat":
        return bridge.preheat()
    if command == "close_document":
        return bridge.close_document()
    if command == "play":
        return bridge.play()
    if command == "pause":
        return bridge.pause()
    if command == "stop":
        return bridge.stop()
    if command == "next":
        return bridge.next_item()
    if command == "prev":
        return bridge.prev_item()
    if command == "goto":
        return bridge.goto_item(int(payload.get("index", 0)))
    if command == "control_media":
        return bridge.control_media(
            str(payload.get("media_id", "")),
            str(payload.get("action", "")),
            int(payload.get("media_index", 0)),
        )
    if command == "state":
        return bridge.state_payload()
    if command in {"close", "shutdown"}:
        return bridge.close()
    raise WorkerError(f"不支持的 LibreOffice bridge 命令：{command}")


def _invoke_presentation_start(presentation: object, start_errors: list[BaseException]) -> None:
    """在线程中调用 LibreOffice 放映启动，避免同步阻塞 bridge 命令循环。"""
    try:
        start_with_arguments = getattr(presentation, "startWithArguments", None)
        if start_with_arguments is not None:
            start_with_arguments(())
            return
        presentation.start()  # type: ignore[attr-defined]
    except BaseException as start_error:
        start_errors.append(start_error)


def _export_previews(file_path: Path, output_dir: Path) -> list[str]:
    """使用 LibreOffice UNO 导出每页 PNG。"""
    output_dir.mkdir(parents=True, exist_ok=True)
    session: Optional[LibreOfficeSession] = None
    document: Optional[object] = None
    try:
        session = _start_session(headless=True)
        document = _load_document(session, file_path, hidden=True, readonly=True)
        draw_pages = document.getDrawPages()  # type: ignore[attr-defined]
        slide_count = int(draw_pages.getCount())
        exporter = session.context.ServiceManager.createInstanceWithContext(
            "com.sun.star.drawing.GraphicExportFilter",
            session.context,
        )
        previews: list[str] = []
        for page_index in range(slide_count):
            output_path = output_dir / f"slide-{page_index + 1}.png"
            draw_page = draw_pages.getByIndex(page_index)
            exporter.setSourceDocument(draw_page)
            exporter.filter(
                (
                    session.property_value("URL", session.path_to_file_url(output_path)),
                    session.property_value("MediaType", "image/png"),
                )
            )
            if not output_path.is_file():
                raise WorkerError(f"LibreOffice 未生成预览文件：{output_path}")
            previews.append(output_path.name)
        return previews
    finally:
        if document is not None:
            _close_document(document)
        if session is not None:
            session.close()


def _start_session(headless: bool) -> LibreOfficeSession:
    """启动隔离 LibreOffice 会话并连接 UNO pipe。"""
    uno = _import_uno()
    executable = _resolve_soffice_executable()
    pipe_name = f"scp_cv_{os.getpid()}_{uuid.uuid4().hex}"
    profile_dir = Path(tempfile.mkdtemp(prefix="scp-cv-lo-"))
    profile_url = uno.systemPathToFileUrl(str(profile_dir.resolve()))
    accept_arg = f"--accept=pipe,name={pipe_name};urp;StarOffice.ComponentContext"
    args = [
        str(executable),
        "--norestore",
        "--nodefault",
        "--nolockcheck",
        "--nofirststartwizard",
        "--nologo",
        f"-env:UserInstallation={profile_url}",
        accept_arg,
    ]
    if headless:
        args.insert(1, "--headless")
    try:
        process = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError as start_error:
        shutil.rmtree(profile_dir, ignore_errors=True)
        raise WorkerError(f"LibreOffice 启动失败：{start_error}") from start_error
    try:
        context, desktop = _connect_uno_pipe(uno, pipe_name, process)
    except Exception:
        _terminate_process(process)
        shutil.rmtree(profile_dir, ignore_errors=True)
        raise
    return LibreOfficeSession(process, profile_dir, context, desktop, uno)


def _load_document(session: LibreOfficeSession, file_path: Path, hidden: bool, readonly: bool) -> object:
    """加载 LibreOffice 文档。"""
    properties = (
        session.property_value("Hidden", hidden),
        session.property_value("ReadOnly", readonly),
    )
    return session.desktop.loadComponentFromURL(session.path_to_file_url(file_path), "_blank", 0, properties)


def _close_document(document: object) -> None:
    """关闭 UNO 文档。"""
    try:
        document.close(True)  # type: ignore[attr-defined]
        return
    except Exception:
        pass
    try:
        document.dispose()  # type: ignore[attr-defined]
    except Exception:
        pass


def _import_uno() -> Any:
    """导入 LibreOffice Python 的 uno 模块。"""
    try:
        import uno  # type: ignore[import-not-found]
    except Exception as import_error:
        raise WorkerError(f"无法导入 LibreOffice pyuno：{import_error}") from import_error
    return uno


def _resolve_soffice_executable() -> Path:
    """从 LibreOffice Python 所在目录解析 soffice 可执行文件。"""
    program_dir = Path(sys.executable).resolve().parent
    names = ("soffice.com", "soffice.exe", "soffice") if os.name == "nt" else ("soffice", "soffice.com", "soffice.exe")
    for name in names:
        candidate = program_dir / name
        if candidate.is_file():
            return candidate
    raise WorkerError(f"未找到 LibreOffice soffice：{program_dir}")


def _connect_uno_pipe(uno: Any, pipe_name: str, process: subprocess.Popen[bytes]) -> tuple[object, object]:
    """等待 UNO pipe 连接。"""
    local_context = uno.getComponentContext()
    resolver = local_context.ServiceManager.createInstanceWithContext(
        "com.sun.star.bridge.UnoUrlResolver",
        local_context,
    )
    uno_url = f"uno:pipe,name={pipe_name};urp;StarOffice.ComponentContext"
    deadline = time.monotonic() + _timeout_seconds()
    last_error: Optional[Exception] = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise WorkerError(f"LibreOffice 进程提前退出，退出码={process.returncode}")
        try:
            context = resolver.resolve(uno_url)
            desktop = context.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", context)
            return context, desktop
        except Exception as connect_error:
            last_error = connect_error
            time.sleep(0.2)
    raise WorkerError(f"连接 LibreOffice UNO 超时：{last_error}")


def _timeout_seconds() -> float:
    """读取 worker 超时秒数。"""
    raw_value = os.environ.get("LIBREOFFICE_CONNECT_TIMEOUT_SECONDS", "10")
    try:
        return max(1.0, float(raw_value))
    except (TypeError, ValueError):
        return 10.0


def _bridge_command_timeout_seconds() -> float:
    """读取 bridge 命令超时秒数。"""
    raw_value = os.environ.get("LIBREOFFICE_BRIDGE_COMMAND_TIMEOUT_SECONDS", "120")
    try:
        return max(1.0, float(raw_value))
    except (TypeError, ValueError):
        return 120.0


def _is_recoverable_bridge_dispose_error(error: BaseException) -> bool:
    """
    判断是否为 LibreOffice 冷启动后 UNO bridge 断开的可恢复错误。
    :param error: 捕获到的异常
    :return: True 表示可重建 session 后重试一次
    """
    error_text = f"{error.__class__.__name__}: {error}"
    return "DisposedException" in error_text or "Binary URP bridge disposed" in error_text


def _terminate_process(process: subprocess.Popen[bytes]) -> None:
    """尽力结束 LibreOffice 进程。"""
    if process.poll() is not None:
        return
    try:
        process.terminate()
        process.wait(timeout=3)
        return
    except Exception:
        pass
    try:
        process.kill()
        process.wait(timeout=3)
    except Exception:
        pass


def _write_result(success: bool, previews: Optional[list[str]] = None, error: str = "") -> None:
    """写出单行 JSON 结果。"""
    print(
        json.dumps(
            {
                "success": success,
                "previews": previews or [],
                "error": error,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


if __name__ == "__main__":
    raise SystemExit(main())
