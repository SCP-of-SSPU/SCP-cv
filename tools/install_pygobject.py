#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PyGObject Windows 安装辅助脚本。
解决 Windows 上 pip install PyGObject 因 Meson 找到错误的 link.exe 而失败的问题。

使用方法：
  1. 确保已安装 GStreamer MSVC x86_64（选择 Complete 安装选项）
  2. 确保已安装 Visual Studio（含 C++ 桌面开发组件）
  3. 在项目虚拟环境激活后运行：
     python tools/install_pygobject.py

原理：
  - 自动检测 MSVC link.exe 路径并临时置于 PATH 最前
  - 设置 PKG_CONFIG_PATH 指向 GStreamer 的 pkgconfig 目录
  - 调用 pip install PyGObject 完成编译安装

@Project : SCP-cv
@File : install_pygobject.py
@Author : Qintsg
@Date : 2026-04-14
'''
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def find_msvc_link_dir() -> Path | None:
    """
    通过 vswhere 查找最新 Visual Studio 安装路径，
    再定位到 Hostx64/x64 下的 link.exe 所在目录。
    :return: 包含 MSVC link.exe 的目录路径，未找到时返回 None
    """
    vswhere = Path(os.environ.get("ProgramFiles(x86)", "")) / \
        "Microsoft Visual Studio" / "Installer" / "vswhere.exe"
    if not vswhere.exists():
        print("错误：未找到 vswhere.exe，请确认已安装 Visual Studio。")
        return None

    # 获取 VS 安装路径
    vs_install_result = subprocess.run(
        [str(vswhere), "-latest", "-property", "installationPath"],
        capture_output=True, text=True,
    )
    vs_path = vs_install_result.stdout.strip()
    if not vs_path:
        print("错误：vswhere 未找到 Visual Studio 安装。")
        return None

    # 在 MSVC 工具目录中搜索 x64 link.exe
    msvc_tools = Path(vs_path) / "VC" / "Tools" / "MSVC"
    if not msvc_tools.exists():
        print(f"错误：MSVC 工具目录不存在：{msvc_tools}")
        return None

    # 取最新版本
    versions = sorted(msvc_tools.iterdir(), reverse=True)
    for version_dir in versions:
        link_dir = version_dir / "bin" / "Hostx64" / "x64"
        link_exe = link_dir / "link.exe"
        if link_exe.exists():
            return link_dir

    print("错误：未找到 MSVC Hostx64/x64/link.exe")
    return None


def find_gstreamer_pkgconfig() -> Path | None:
    """
    查找 GStreamer MSVC x86_64 的 pkgconfig 目录。
    :return: pkgconfig 目录路径，未找到时返回 None
    """
    # 优先使用环境变量
    gst_root_env = os.environ.get("GSTREAMER_1_0_ROOT_MSVC_X86_64", "")
    if gst_root_env:
        pkgconfig_dir = Path(gst_root_env) / "lib" / "pkgconfig"
        if pkgconfig_dir.exists():
            return pkgconfig_dir

    # 常见安装路径
    candidate_paths = [
        Path(r"C:\Program Files\gstreamer\1.0\msvc_x86_64\lib\pkgconfig"),
        Path(r"C:\gstreamer\1.0\msvc_x86_64\lib\pkgconfig"),
        Path(r"D:\gstreamer\1.0\msvc_x86_64\lib\pkgconfig"),
    ]
    for candidate in candidate_paths:
        if candidate.exists():
            return candidate

    return None


def check_prerequisites() -> bool:
    """
    检查安装前提条件。
    :return: 前提条件是否全部满足
    """
    prerequisites_met = True

    # 检查 GStreamer
    gst_pkgconfig = find_gstreamer_pkgconfig()
    if gst_pkgconfig is None:
        print("错误：未找到 GStreamer MSVC x86_64 安装。")
        print("请从 https://gstreamer.freedesktop.org/download/ 下载并安装。")
        print("安装时选择 Complete 选项以包含开发文件。")
        prerequisites_met = False
    else:
        # 检查是否有 gobject-introspection（Complete 安装才有）
        gi_pc = gst_pkgconfig / "gobject-introspection-1.0.pc"
        if not gi_pc.exists():
            print("警告：GStreamer 安装中未找到 gobject-introspection。")
            print("这通常意味着安装时未选择 Complete 选项。")
            print("请重新运行 GStreamer 安装程序，选择 Complete 安装。")
            prerequisites_met = False
        else:
            print(f"✓ GStreamer pkgconfig: {gst_pkgconfig}")

    # 检查 MSVC link.exe
    msvc_link_dir = find_msvc_link_dir()
    if msvc_link_dir is None:
        prerequisites_met = False
    else:
        print(f"✓ MSVC link.exe: {msvc_link_dir / 'link.exe'}")

    return prerequisites_met


def install_pygobject() -> int:
    """
    在修正的环境中安装 PyGObject。
    :return: pip 进程退出码
    """
    print("=" * 60)
    print("PyGObject Windows 安装辅助脚本")
    print("=" * 60)
    print()

    # 检查前提条件
    if not check_prerequisites():
        print()
        print("前提条件未满足，请按上述提示修复后重试。")
        return 1

    msvc_link_dir = find_msvc_link_dir()
    gst_pkgconfig = find_gstreamer_pkgconfig()

    # 构建修正后的环境变量
    modified_env = os.environ.copy()

    # 将 MSVC link.exe 目录置于 PATH 最前（覆盖 Git 的 link.exe）
    current_path = modified_env.get("PATH", "")
    modified_env["PATH"] = f"{msvc_link_dir};{current_path}"

    # 设置 PKG_CONFIG_PATH
    modified_env["PKG_CONFIG_PATH"] = str(gst_pkgconfig)

    print()
    print(f"PATH 前置: {msvc_link_dir}")
    print(f"PKG_CONFIG_PATH: {gst_pkgconfig}")
    print()
    print("开始安装 PyGObject...")
    print("-" * 60)

    # 执行 pip install
    pip_result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "PyGObject>=3.50.0"],
        env=modified_env,
    )

    if pip_result.returncode == 0:
        print()
        print("✓ PyGObject 安装成功！")
    else:
        print()
        print("✗ PyGObject 安装失败。")
        print("可能的原因：")
        print("  1. GStreamer 未选择 Complete 安装（缺少开发文件）")
        print("  2. Visual Studio 缺少 C++ 桌面开发组件")
        print("  3. 网络问题导致下载失败")

    return pip_result.returncode


if __name__ == "__main__":
    sys.exit(install_pygobject())
