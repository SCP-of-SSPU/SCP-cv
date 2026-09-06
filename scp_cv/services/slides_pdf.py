#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
演示文稿 PDF 播放缓存服务：静态演示文稿自动转 PDF，并为播放模式提供元数据。
@Project : SCP-cv
@File : slides_pdf.py
@Author : Qintsg
@Date : 2026-08-05
'''
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Optional

from django.conf import settings
from django.utils import timezone

from scp_cv.apps.playback.models import MediaSource, SourceType
from scp_cv.services.ppt_playback_cache import resolve_ppt_playback_uri

logger = logging.getLogger(__name__)

SLIDES_PDF_METADATA_KEY = "slides_pdf"
SLIDES_PLAYBACK_MODE_KEY = "playback_mode"
PDF_CACHE_ROOT = "slides_pdf"
_PPT_SAVE_AS_PDF = 32
_PPT_ALERTS_NONE = 1
_OOXML_EXTENSIONS = {".pptx", ".pptm", ".ppsx", ".ppsm", ".potx", ".potm"}
_LEGACY_EXTENSIONS = {".ppt", ".pps", ".pot", ".odp"}
_STATIC_MARKERS = (
    "<p:timing",
    "<p:transition",
    ":timing",
    ":transition",
    "<p:anim",
    "<p:seq",
    "<p:cmd",
    "<p:audio",
    "<p:video",
    "<p:oleobj",
    "<p:embedded",
    "<p:link",
)

PdfExporter = Callable[[Path, Path], str]
StaticDetector = Callable[[Path], Optional[bool]]


class SlidesPdfError(RuntimeError):
    """演示文稿 PDF 播放缓存生成失败。"""


def prepare_slides_pdf(
    source: MediaSource,
    pdf_exporter: Optional[PdfExporter] = None,
    static_detector: Optional[StaticDetector] = None,
) -> dict[str, object]:
    """
    为新上传的演示文稿准备 PDF 播放模式。
    :param source: PPT 类型媒体源
    :param pdf_exporter: PDF 导出函数，测试可注入替身
    :param static_detector: 静态检测函数，测试可注入替身
    :return: 更新后的 metadata
    """
    if source.source_type != SourceType.PPT:
        return dict(source.metadata or {})

    metadata = dict(source.metadata or {})
    source_path = Path(source.uri)
    if not source_path.is_file():
        metadata[SLIDES_PLAYBACK_MODE_KEY] = "powerpoint"
        source.metadata = metadata
        source.save(update_fields=["metadata"])
        return metadata

    if source_path.suffix.lower() == ".pdf":
        metadata[SLIDES_PLAYBACK_MODE_KEY] = "pdf"
        metadata.setdefault(SLIDES_PDF_METADATA_KEY, {
            "status": "source",
            "path": str(source_path),
            "relative_path": _relative_media_path(source_path),
        })
        source.metadata = metadata
        source.save(update_fields=["metadata"])
        return metadata

    # 测试/受限环境可关闭自动 COM 导出；显式注入 exporter 仍用于单元测试和
    # 离线批处理。生产默认开启，以便动态 PPT 也具备 PDF fallback。
    if not bool(getattr(settings, "SLIDES_PDF_AUTO_CONVERT", True)) and pdf_exporter is None:
        metadata["slides_static"] = None
        metadata[SLIDES_PLAYBACK_MODE_KEY] = "powerpoint"
        source.metadata = metadata
        source.save(update_fields=["metadata"])
        return metadata

    detector = static_detector or detect_slides_static
    try:
        static = detector(source_path)
    except Exception as detect_error:
        logger.warning("演示文稿静态检测失败，回退 PowerPoint：source_id=%s, error=%s", source.pk, detect_error)
        static = None

    # 所有可读 PPT 都尝试生成 PDF：静态源优先以 PDF 播放，动态/未知源仍保留
    # PowerPoint 主模式，但在 COM 槽位被占用时可安全回退到同一份 PDF。
    metadata["slides_static"] = static is True if static is not None else None
    try:
        payload = _build_pdf_cache(source, pdf_exporter)
    except Exception as cache_error:
        logger.warning("演示文稿 PDF 缓存生成失败：source_id=%s, error=%s", source.pk, cache_error)
        payload = _failed_payload(source, str(cache_error))
    metadata[SLIDES_PDF_METADATA_KEY] = payload
    metadata[SLIDES_PLAYBACK_MODE_KEY] = (
        "pdf" if static is True and payload.get("status") == "ready" else "powerpoint"
    )
    source.metadata = metadata
    source.save(update_fields=["metadata"])
    return metadata


def resolve_slide_playback_uri(source: MediaSource) -> str:
    """
    获取演示文稿播放时应使用的 URI：优先 PDF，其次 ppsx/pps 缓存，最后原始文件。
    :param source: PPT 类型媒体源
    :return: 播放 URI
    """
    if source.source_type != SourceType.PPT:
        return source.uri
    metadata = dict(source.metadata or {})
    mode = str(metadata.get(SLIDES_PLAYBACK_MODE_KEY) or "")
    if mode == "pdf":
        pdf_path = _pdf_path_from_metadata(
            dict(metadata.get(SLIDES_PDF_METADATA_KEY) or {})
        )
        if pdf_path is not None and pdf_path.is_file():
            return str(pdf_path)
        if Path(source.uri).suffix.lower() == ".pdf":
            return source.uri
    return resolve_ppt_playback_uri(source)


def get_slides_pdf_uri(source: MediaSource) -> str:
    """返回已生成且摘要对应当前源的 PDF 回退路径；不可用时返回空字符串。"""
    if source.source_type != SourceType.PPT:
        return ""
    metadata = dict(source.metadata or {})
    payload = dict(metadata.get(SLIDES_PDF_METADATA_KEY) or {})
    path = _pdf_path_from_metadata(payload)
    if path is None or not path.is_file():
        return ""
    source_path = Path(source.uri)
    if source_path.is_file() and payload.get("source_digest"):
        try:
            if payload.get("source_digest") != _file_digest(source_path):
                return ""
        except OSError:
            return ""
    return str(path)


def get_slides_playback_mode(source: MediaSource) -> str:
    """
    读取演示文稿播放模式。
    :param source: PPT 类型媒体源
    :return: pdf 或 powerpoint
    """
    if source.source_type != SourceType.PPT:
        return ""
    metadata = dict(source.metadata or {})
    mode = str(metadata.get(SLIDES_PLAYBACK_MODE_KEY) or "")
    if mode:
        return mode
    if Path(source.uri).suffix.lower() == ".pdf":
        return "pdf"
    return "powerpoint"


def cleanup_slides_pdf(source_id: int) -> None:
    """
    删除演示文稿 PDF 播放缓存目录。
    :param source_id: MediaSource 主键
    :return: None
    """
    cache_dir = Path(settings.MEDIA_ROOT) / PDF_CACHE_ROOT / str(int(source_id or 0))
    if cache_dir.exists():
        shutil.rmtree(cache_dir, ignore_errors=True)
        logger.info("删除演示文稿 PDF 播放缓存：%s", cache_dir)


def detect_slides_static(file_path: Path) -> Optional[bool]:
    """
    判断演示文稿是否只包含静态内容。
    :param file_path: 演示文稿文件路径
    :return: True 静态；False 含动画/媒体；None 无法判断
    """
    if not file_path.is_file():
        return None
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        return True
    if suffix in _OOXML_EXTENSIONS:
        return _detect_ooxml_static(file_path)
    if suffix in _LEGACY_EXTENSIONS:
        return _detect_legacy_static(file_path)
    return None


def detect_legacy_static_in_process(file_path: Path) -> Optional[bool]:
    """
    在隔离子进程内通过 PowerPoint COM 检查二进制演示文稿是否静态。
    :param file_path: 旧版 PPT/PPS/POT/ODP 文件路径
    :return: True/False；检测失败返回 None
    """
    try:
        import pythoncom
        import win32com.client
    except ImportError as import_error:
        logger.warning("旧版演示文稿静态检测缺少 COM 依赖：%s", import_error)
        return None

    pythoncom.CoInitialize()
    app = None
    presentation = None
    try:
        app = win32com.client.DispatchEx("PowerPoint.Application")
        app.DisplayAlerts = _PPT_ALERTS_NONE
        presentation = app.Presentations.Open(
            str(file_path), ReadOnly=True, Untitled=False, WithWindow=False,
        )
        for slide_index in range(1, int(presentation.Slides.Count) + 1):
            slide = presentation.Slides(slide_index)
            try:
                if int(slide.TimeLine.MainSequence.Count) > 0:
                    return False
            except Exception:
                pass
            try:
                if int(slide.SlideShowTransition.EntryEffect) != 0:
                    return False
            except Exception:
                pass
            try:
                for shape in slide.Shapes:
                    shape_type = int(getattr(shape, "Type", 0))
                    if shape_type in {7, 10, 16}:
                        return False
                    try:
                        if int(getattr(shape, "MediaType", 0)) != 0:
                            return False
                    except Exception:
                        pass
            except Exception:
                pass
        return True
    except Exception as inspect_error:
        logger.warning("旧版演示文稿静态检测失败：%s", inspect_error)
        return None
    finally:
        if presentation is not None:
            try:
                presentation.Saved = True
                presentation.Close()
            except Exception:
                pass
        if app is not None:
            try:
                app.Quit()
            except Exception:
                pass
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass


def export_slides_pdf(source_path: Path, target_path: Path) -> str:
    """
    使用 PowerPoint 将演示文稿导出为 PDF。
    :param source_path: 源演示文稿
    :param target_path: 目标 PDF 路径
    :return: 实际导出后端，固定为 powerpoint
    :raises SlidesPdfError: 导出失败时
    """
    target_path.unlink(missing_ok=True)
    _export_with_com(source_path, target_path)
    if not target_path.is_file():
        raise SlidesPdfError("PowerPoint 未生成 PDF 文件")
    logger.info("演示文稿 PDF 缓存导出成功：%s -> %s", source_path, target_path)
    return "powerpoint"


def _build_pdf_cache(source: MediaSource, pdf_exporter: Optional[PdfExporter]) -> dict[str, object]:
    """
    构建并写入 PDF 播放缓存 payload。
    :param source: PPT 类型媒体源
    :param pdf_exporter: 可注入的导出函数
    :return: ready 状态 payload
    """
    source_path = Path(source.uri)
    if not source_path.is_file():
        raise SlidesPdfError(f"演示文稿源文件不存在：{source_path}")
    source_digest = _file_digest(source_path)
    existing_payload = dict((source.metadata or {}).get(SLIDES_PDF_METADATA_KEY) or {})
    existing_path = _pdf_path_from_metadata(existing_payload)
    if (
        existing_payload.get("status") == "ready"
        and existing_payload.get("source_digest") == source_digest
        and existing_path is not None
        and existing_path.is_file()
    ):
        return existing_payload

    cache_dir = Path(settings.MEDIA_ROOT) / PDF_CACHE_ROOT / str(source.pk)
    cache_dir.mkdir(parents=True, exist_ok=True)
    target_path = cache_dir / f"{source_digest[:16]}.pdf"
    exporter = pdf_exporter or export_slides_pdf
    actual_backend = exporter(source_path, target_path)
    _remove_other_cache_files(cache_dir, target_path)
    return {
        "status": "ready",
        "source_digest": source_digest,
        "backend": actual_backend,
        "format": "pdf",
        "path": str(target_path),
        "relative_path": str(target_path.relative_to(settings.MEDIA_ROOT)).replace("\\", "/"),
        "generated_at": timezone.now().isoformat(),
        "error": "",
        "original_extension": source_path.suffix.lower(),
    }


def _detect_ooxml_static(file_path: Path) -> bool:
    """
    从 OOXML zip 包检测页内动画、切换、音视频和嵌入对象。
    :param file_path: OOXML 演示文稿
    :return: True 表示静态
    """
    try:
        with zipfile.ZipFile(file_path) as archive:
            slide_names = sorted(
                (name for name in archive.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)),
                key=lambda name: int(re.search(r"slide(\d+)\.xml", name).group(1)),
            )
            if not slide_names:
                return False
            from scp_cv.services.ppt_resources import _extract_slide_media_items
            for page_index, slide_name in enumerate(slide_names, start=1):
                content = archive.read(slide_name).decode("utf-8", errors="ignore").casefold()
                if any(marker in content for marker in _STATIC_MARKERS):
                    return False
                if _extract_slide_media_items(archive, slide_name, page_index):
                    return False
            return True
    except Exception as parse_error:
        logger.warning("OOXML 静态检测失败：%s", parse_error)
        return False


def _detect_legacy_static(file_path: Path) -> Optional[bool]:
    """
    通过隔离子进程检测二进制演示文稿是否静态。
    :param file_path: 旧版演示文稿
    :return: True/False；无法启动检测时 None
    """
    worker_script = Path(__file__).with_name("slides_static_worker.py")
    command = [sys.executable, str(worker_script), str(file_path)]
    env = os.environ.copy()
    env.setdefault("DJANGO_SETTINGS_MODULE", "scp_cv.settings")
    env["PYTHONPATH"] = _prepend_pythonpath(str(settings.BASE_DIR), env.get("PYTHONPATH", ""))
    try:
        completed = subprocess.run(
            command,
            cwd=str(settings.BASE_DIR),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=90.0,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as worker_error:
        logger.warning("旧版演示文稿静态检测 worker 异常：%s", worker_error)
        return None
    payload = _parse_worker_payload(completed.stdout)
    if not payload:
        return None
    raw_static = payload.get("static")
    if not isinstance(raw_static, bool):
        return None
    return raw_static


def _parse_worker_payload(stdout: str) -> dict[str, object]:
    """
    解析子进程输出中最后一行有效 JSON。
    :param stdout: 子进程标准输出
    :return: 有效 payload；失败返回空字典
    """
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and payload.get("success"):
            return payload
    return {}


def _export_with_com(source_path: Path, target_path: Path) -> None:
    """
    通过 PowerPoint COM SaveAs 导出 PDF。
    :param source_path: 源演示文稿
    :param target_path: 目标 PDF
    :return: None
    :raises SlidesPdfError: 导出失败时
    """
    try:
        import pythoncom
        import win32com.client
    except ImportError as import_error:
        raise SlidesPdfError(f"缺少 PowerPoint COM 依赖：{import_error}") from import_error

    pythoncom.CoInitialize()
    app = None
    presentation = None
    try:
        try:
            app = win32com.client.DispatchEx("PowerPoint.Application")
        except Exception as dispatch_error:
            raise SlidesPdfError(f"未找到 PowerPoint COM 自动化对象：{dispatch_error}") from dispatch_error
        try:
            app.DisplayAlerts = _PPT_ALERTS_NONE
        except Exception:
            pass
        presentations = app.Presentations
        try:
            presentation = presentations.Open(
                str(source_path), ReadOnly=True, Untitled=False, WithWindow=False,
            )
        except Exception:
            try:
                presentation = presentations.Open(str(source_path), True, False, False)
            except Exception as positional_error:
                raise SlidesPdfError(f"打开演示文稿失败：{positional_error}") from positional_error
        presentation.SaveAs(str(target_path), _PPT_SAVE_AS_PDF)
    finally:
        if presentation is not None:
            try:
                presentation.Saved = True
                presentation.Close()
            except Exception:
                pass
        if app is not None:
            try:
                app.Quit()
            except Exception:
                pass
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass


def _file_digest(file_path: Path) -> str:
    """
    计算源文件 SHA-256 摘要。
    :param file_path: 文件路径
    :return: 十六进制摘要
    """
    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _pdf_path_from_metadata(metadata: dict[str, object]) -> Optional[Path]:
    """
    从 metadata 解析 PDF 缓存路径。
    :param metadata: slides_pdf metadata 字典
    :return: 本地路径或 None
    """
    raw_path = str(metadata.get("path") or "")
    if raw_path:
        path = Path(raw_path)
        return path if path.is_absolute() else Path(settings.MEDIA_ROOT) / path
    relative_path = str(metadata.get("relative_path") or "")
    if relative_path:
        return Path(settings.MEDIA_ROOT) / relative_path
    return None


def _remove_other_cache_files(cache_dir: Path, keep_path: Path) -> None:
    """
    清理同一源目录下的旧缓存文件。
    :param cache_dir: 缓存目录
    :param keep_path: 当前保留文件
    :return: None
    """
    for child in cache_dir.iterdir():
        if child == keep_path:
            continue
        if child.is_file():
            child.unlink(missing_ok=True)
        elif child.is_dir():
            shutil.rmtree(child, ignore_errors=True)


def _failed_payload(source: MediaSource, error_message: str) -> dict[str, object]:
    """
    构造 PDF 缓存失败 payload。
    :param source: PPT 类型媒体源
    :param error_message: 失败原因
    :return: failed payload
    """
    source_path = Path(source.uri)
    source_digest = ""
    if source_path.is_file():
        try:
            source_digest = _file_digest(source_path)
        except OSError:
            source_digest = ""
    return {
        "status": "failed",
        "source_digest": source_digest,
        "backend": "powerpoint",
        "format": "pdf",
        "path": "",
        "relative_path": "",
        "generated_at": timezone.now().isoformat(),
        "error": error_message,
        "original_extension": source_path.suffix.lower(),
    }


def _relative_media_path(path: Path) -> str:
    """
    计算文件相对 MEDIA_ROOT 的路径。
    :param path: 本地文件路径
    :return: 相对路径或空字符串
    """
    try:
        return str(path.relative_to(settings.MEDIA_ROOT)).replace("\\", "/")
    except ValueError:
        return ""


def _prepend_pythonpath(path: str, current_pythonpath: str) -> str:
    """
    将项目根目录加入 PYTHONPATH 前部。
    :param path: 项目根目录
    :param current_pythonpath: 当前 PYTHONPATH
    :return: 合并后的 PYTHONPATH
    """
    if not current_pythonpath:
        return path
    entries = [entry for entry in current_pythonpath.split(os.pathsep) if entry]
    if path in entries:
        return current_pythonpath
    return os.pathsep.join([path, *entries])


__all__ = [
    "SLIDES_PDF_METADATA_KEY",
    "SLIDES_PLAYBACK_MODE_KEY",
    "SlidesPdfError",
    "cleanup_slides_pdf",
    "detect_legacy_static_in_process",
    "detect_slides_static",
    "export_slides_pdf",
    "get_slides_playback_mode",
    "get_slides_pdf_uri",
    "prepare_slides_pdf",
    "resolve_slide_playback_uri",
]
