#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""校验仓库中的 GitHub Spec Kit 功能产物。"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


PLACEHOLDER_PATTERNS = (
    re.compile(r"\[(?:FEATURE NAME|###-feature-name|PROJECT_NAME)\]"),
    re.compile(r"\[NEEDS CLARIFICATION[^\]]*\]"),
    re.compile(
        r"\[(?:PRINCIPLE_|SECTION_|GOVERNANCE_RULES|CONSTITUTION_|RATIFICATION_DATE|LAST_AMENDED_DATE)[^\]]*\]"
    ),
)
FEATURE_DIR_PATTERN = re.compile(r"^(?:\d{3}|\d{8}-\d{6})-[a-z0-9]+(?:-[a-z0-9]+)*$")
REQUIRED_SPEC_HEADINGS = (
    "## User Scenarios & Testing",
    "## Requirements",
    "## Success Criteria",
)


def _find_placeholders(text: str) -> list[str]:
    """
    返回文档中仍存在的 Spec Kit 占位符。

    :param text: 待检查的 Markdown 文本。
    :returns: 去重并排序后的占位符列表。
    """
    matches: list[str] = []
    for pattern in PLACEHOLDER_PATTERNS:
        matches.extend(pattern.findall(text))
    return sorted(set(matches))


def validate_specs(specs_dir: Path) -> list[str]:
    """
    校验规范目录并返回错误信息。

    :param specs_dir: 功能规范根目录。
    :returns: 按功能目录归类的错误信息；空列表表示通过。
    """
    if not specs_dir.exists():
        return []

    errors: list[str] = []
    feature_dirs = sorted(path for path in specs_dir.iterdir() if path.is_dir())
    for feature_dir in feature_dirs:
        if feature_dir.name.startswith("."):
            continue
        if not FEATURE_DIR_PATTERN.fullmatch(feature_dir.name):
            errors.append(
                f"{feature_dir}: 目录名必须符合 <编号>-<短名称>（例如 001-user-auth）"
            )
        spec_file = feature_dir / "spec.md"
        if not spec_file.is_file():
            errors.append(f"{feature_dir}: 缺少 spec.md")
            continue

        spec_text = spec_file.read_text(encoding="utf-8")
        for heading in REQUIRED_SPEC_HEADINGS:
            if heading not in spec_text:
                errors.append(f"{spec_file}: 缺少必需章节 {heading}")

        documents = sorted(feature_dir.rglob("*.md"))
        for document in documents:
            placeholders = _find_placeholders(document.read_text(encoding="utf-8"))
            if placeholders:
                errors.append(f"{document}: 存在未完成占位符 {', '.join(placeholders)}")

        has_plan = (feature_dir / "plan.md").exists()
        has_tasks = (feature_dir / "tasks.md").exists()
        if has_tasks and not has_plan:
            errors.append(f"{feature_dir}: tasks.md 存在但缺少 plan.md")

    return errors


def main() -> int:
    """
    解析命令行参数并执行规范校验。

    :returns: 进程退出码，0 表示通过。
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--specs-dir", type=Path, default=Path("specs"))
    args = parser.parse_args()
    errors = validate_specs(args.specs_dir)
    if errors:
        for error in errors:
            print(f"::error::{error}")
        return 1
    print(f"Spec Kit 校验通过：{args.specs_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
