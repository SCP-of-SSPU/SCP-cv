#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
旧版演示文稿静态检测隔离 worker，避免 Office COM 影响 Django 主进程。
@Project : SCP-cv
@File : slides_static_worker.py
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
    执行旧版演示文稿静态检测并把结果以单行 JSON 写到标准输出。
    :param argv: 命令行参数，依次为文件路径
    :return: 进程退出码
    """
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        _write_result(False, None, "usage: slides_static_worker <file_path>")
        return 2

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "scp_cv.settings")
    _ensure_project_root_on_path()
    try:
        import django

        django.setup()
        from scp_cv.services.slides_pdf import detect_legacy_static_in_process

        static = detect_legacy_static_in_process(Path(args[0]))
    except Exception as worker_error:
        logging.getLogger(__name__).exception("旧版演示文稿静态检测 worker 执行失败")
        _write_result(False, None, str(worker_error))
        return 1

    _write_result(True, static, "")
    return 0


def _write_result(success: bool, static: object, error: str) -> None:
    """
    写出 worker 结果。
    :param success: 是否成功执行
    :param static: 静态检测结果
    :param error: 错误描述
    :return: None
    """
    print(
        json.dumps(
            {
                "success": success,
                "static": static,
                "error": error,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


if __name__ == "__main__":
    raise SystemExit(main())
