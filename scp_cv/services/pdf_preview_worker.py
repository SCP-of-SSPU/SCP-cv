#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PDF 页面预览导出隔离 worker，避免 QtPdf 渲染影响 Django 主进程。
@Project : SCP-cv
@File : pdf_preview_worker.py
@Author : Qintsg
@Date : 2026-08-05
'''
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path


def _ensure_project_root_on_path() -> None:
    """
    将项目根目录加入 sys.path，保证脚本直跑时也能导入 scp_cv。
    :return: None
    """
    project_root = Path(__file__).resolve().parents[2]
    project_root_text = str(project_root)
    if project_root_text not in sys.path:
        sys.path.insert(0, project_root_text)


def main(argv: list[str] | None = None) -> int:
    """
    执行 PDF 预览导出并把结果以单行 JSON 写到标准输出。
    :param argv: 命令行参数，依次为文件路径、媒体源 ID
    :return: 进程退出码
    """
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2:
        _write_result(False, [], "usage: pdf_preview_worker <file_path> <source_id>")
        return 2

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "scp_cv.settings")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    _ensure_project_root_on_path()
    try:
        import django

        django.setup()
        from scp_cv.services.pdf_preview import export_pdf_slide_previews_in_process

        file_path = Path(args[0])
        source_id = int(args[1])
        previews = export_pdf_slide_previews_in_process(file_path, source_id)
    except Exception as worker_error:
        logging.getLogger(__name__).exception("PDF 预览 worker 执行失败")
        _write_result(False, [], str(worker_error))
        return 1

    _write_result(True, previews, "")
    return 0


def _write_result(success: bool, previews: list[str], error: str) -> None:
    """
    写出 worker 结果。
    :param success: 是否成功执行
    :param previews: 预览 URL 列表
    :param error: 错误描述
    :return: None
    """
    print(
        json.dumps(
            {
                "success": success,
                "previews": previews,
                "error": error,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


if __name__ == "__main__":
    raise SystemExit(main())
