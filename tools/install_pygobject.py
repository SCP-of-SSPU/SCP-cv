#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
PyGObject Windows 安装辅助脚本。
解决 Windows 上 pip install PyGObject 编译安装的环境配置问题。

支持两种编译工具链（按优先级自动选择）：
  1. MSVC（Visual Studio）— 通过 vcvarsall.bat 注入完整编译环境
  2. GCC（MinGW / Scoop / MSYS2）— 直接使用 gcc.exe

支持多种 GStreamer 安装变体的 pkgconfig 路径（按优先级）：
  1. MSVC x86_64 — 环境变量 GSTREAMER_1_0_ROOT_MSVC_X86_64
  2. MinGW x86_64 — 环境变量 GSTREAMER_1_0_ROOT_MINGW_X86_64
  3. MSYS2 MinGW64 — C:\\msys64\\mingw64
  4. 通用 x86_64 — 环境变量 GSTREAMER_1_0_ROOT_X86_64

使用方法：
  1. 确保已安装 GStreamer（选择 Complete 安装选项）
  2. 确保已安装 Visual Studio（含 C++ 桌面开发）或 GCC
  3. 在项目虚拟环境激活后运行：
     python tools/install_pygobject.py

@Project : SCP-cv
@File : install_pygobject.py
@Author : Qintsg
@Date : 2026-04-14
'''
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple


# ═══════════════════════════════════════════════════════════════
# GStreamer pkgconfig 检测
# ═══════════════════════════════════════════════════════════════

class _GstPkgSource(NamedTuple):
    """GStreamer pkgconfig 来源描述。"""
    label: str
    env_var: str
    fallback_paths: list[str]


# 按优先级排列的 pkgconfig 查找列表
_GST_PKG_SOURCES: list[_GstPkgSource] = [
    _GstPkgSource(
        label="MSVC x86_64",
        env_var="GSTREAMER_1_0_ROOT_MSVC_X86_64",
        fallback_paths=[
            r"C:\Program Files\gstreamer\1.0\msvc_x86_64",
            r"C:\gstreamer\1.0\msvc_x86_64",
            r"D:\gstreamer\1.0\msvc_x86_64",
        ],
    ),
    _GstPkgSource(
        label="MinGW x86_64",
        env_var="GSTREAMER_1_0_ROOT_MINGW_X86_64",
        fallback_paths=[
            r"C:\Program Files\gstreamer\1.0\mingw_x86_64",
            r"C:\gstreamer\1.0\mingw_x86_64",
            r"D:\gstreamer\1.0\mingw_x86_64",
        ],
    ),
    _GstPkgSource(
        label="MSYS2 MinGW64",
        env_var="",
        fallback_paths=[r"C:\msys64\mingw64"],
    ),
    _GstPkgSource(
        label="通用 x86_64",
        env_var="GSTREAMER_1_0_ROOT_X86_64",
        fallback_paths=[],
    ),
]


def find_gstreamer_pkgconfig() -> tuple[Path | None, str]:
    """
    按优先级查找 GStreamer 的 pkgconfig 目录。
    :return: (pkgconfig 目录, 变体标签) 或 (None, "")
    """
    for source in _GST_PKG_SOURCES:
        roots: list[str] = []
        # 环境变量指定的路径
        if source.env_var:
            env_value = os.environ.get(source.env_var, "")
            if env_value:
                roots.append(env_value)
        # 回退路径
        roots.extend(source.fallback_paths)

        for root in roots:
            pkgconfig_dir = Path(root) / "lib" / "pkgconfig"
            if pkgconfig_dir.exists():
                return pkgconfig_dir, source.label

    return None, ""


# ═══════════════════════════════════════════════════════════════
# 编译器检测：MSVC（vcvarsall）优先，GCC 其次
# ═══════════════════════════════════════════════════════════════

def find_vcvarsall() -> Path | None:
    """
    通过 vswhere 查找最新 Visual Studio 的 vcvarsall.bat。
    :return: vcvarsall.bat 路径，未找到返回 None
    """
    vswhere = Path(os.environ.get("ProgramFiles(x86)", "")) / \
        "Microsoft Visual Studio" / "Installer" / "vswhere.exe"
    if not vswhere.exists():
        return None

    vs_result = subprocess.run(
        [str(vswhere), "-latest", "-property", "installationPath"],
        capture_output=True, text=True,
    )
    vs_path = vs_result.stdout.strip()
    if not vs_path:
        return None

    vcvarsall = Path(vs_path) / "VC" / "Auxiliary" / "Build" / "vcvarsall.bat"
    return vcvarsall if vcvarsall.exists() else None


def capture_msvc_env(vcvarsall: Path, arch: str = "x64") -> dict[str, str]:
    """
    执行 vcvarsall.bat 并捕获其注入的完整环境变量。
    通过 cmd /c 运行批处理后输出所有环境变量，解析为字典。
    :param vcvarsall: vcvarsall.bat 的路径
    :param arch: 目标架构（默认 x64）
    :return: 包含 MSVC 编译环境的环境变量字典
    """
    # 用 cmd 执行 vcvarsall.bat 后打印所有环境变量
    capture_cmd = f'cmd /c ""{vcvarsall}" {arch} >nul 2>&1 && set"'
    capture_result = subprocess.run(
        capture_cmd,
        capture_output=True, text=True, shell=True,
    )
    if capture_result.returncode != 0:
        print(f"警告：vcvarsall.bat 执行失败（exit={capture_result.returncode}）")
        return {}

    # 解析 KEY=VALUE 格式的环境变量
    msvc_env: dict[str, str] = {}
    for line in capture_result.stdout.splitlines():
        if "=" in line:
            key, _, value = line.partition("=")
            msvc_env[key] = value

    return msvc_env


def find_gcc() -> Path | None:
    """
    在 PATH 中查找 gcc.exe。
    :return: gcc.exe 路径，未找到返回 None
    """
    gcc_path = shutil.which("gcc")
    return Path(gcc_path) if gcc_path else None


# ═══════════════════════════════════════════════════════════════
# 前提条件检查
# ═══════════════════════════════════════════════════════════════

def check_prerequisites() -> tuple[bool, dict[str, str], str]:
    """
    检查安装前提条件，返回可用的编译环境。
    :return: (是否满足, 环境变量字典, 编译器标签)
    """
    all_ok = True

    # ── 检查 GStreamer pkgconfig ──
    gst_pkgconfig, gst_label = find_gstreamer_pkgconfig()
    if gst_pkgconfig is None:
        print("错误：未找到 GStreamer 安装（含 pkgconfig）。")
        print("支持的变体（按优先级）：MSVC x86_64 → MinGW x86_64 → MSYS2 MinGW64 → 通用 x86_64")
        print("请从 https://gstreamer.freedesktop.org/download/ 下载并安装。")
        print("安装时选择 Complete 选项以包含开发文件。")
        all_ok = False
    else:
        # 检查是否有 gobject-introspection（Complete 安装才有）
        gi_pc = gst_pkgconfig / "gobject-introspection-1.0.pc"
        if not gi_pc.exists():
            print(f"警告：GStreamer [{gst_label}] 安装中未找到 gobject-introspection。")
            print("这通常意味着安装时未选择 Complete 选项。请重新安装并选择 Complete。")
            all_ok = False
        else:
            print(f"✓ GStreamer pkgconfig [{gst_label}]: {gst_pkgconfig}")

    # ── 检查编译器：MSVC 优先 → GCC 其次 ──
    build_env: dict[str, str] = {}
    compiler_label: str = ""

    vcvarsall = find_vcvarsall()
    if vcvarsall is not None:
        print(f"  检测到 Visual Studio: {vcvarsall.parent.parent.parent.parent}")
        print("  正在捕获 MSVC 编译环境（vcvarsall.bat x64）...")
        msvc_env = capture_msvc_env(vcvarsall)
        if msvc_env and "INCLUDE" in msvc_env:
            build_env = msvc_env
            compiler_label = "MSVC (vcvarsall)"
            print(f"✓ 编译器: {compiler_label}")
        else:
            print("  警告：vcvarsall.bat 环境捕获失败，尝试 GCC 回退…")

    # GCC 回退
    if not build_env:
        gcc_path = find_gcc()
        if gcc_path is not None:
            # GCC 环境无需特殊注入，继承当前环境即可
            build_env = os.environ.copy()
            build_env["CC"] = str(gcc_path)
            compiler_label = f"GCC ({gcc_path})"
            print(f"✓ 编译器: {compiler_label}")
        else:
            print("错误：未找到可用的 C 编译器。")
            print("请安装以下任一编译器：")
            print("  1. Visual Studio（含 C++ 桌面开发组件）— 推荐")
            print("  2. GCC（通过 Scoop: scoop install gcc）")
            print("  3. MSYS2 MinGW-w64（https://www.msys2.org/）")
            all_ok = False

    # 将 pkgconfig 写入环境，并把 GStreamer bin 目录加入 PATH 以便 Meson 找到 pkg-config.exe
    if gst_pkgconfig is not None and build_env:
        build_env["PKG_CONFIG_PATH"] = str(gst_pkgconfig)
        # pkgconfig 目录结构: <gst_root>/lib/pkgconfig → 回退两级得到 gst_root
        gst_root_bin = str(gst_pkgconfig.parent.parent / "bin")
        # Windows 环境变量不区分大小写，但 Python dict 区分；
        # vcvarsall 捕获的环境可能用 Path 而非 PATH
        path_key = "PATH" if "PATH" in build_env else "Path"
        existing_path = build_env.get(path_key, "")
        if gst_root_bin.lower() not in existing_path.lower():
            # 将 GStreamer bin 置于 PATH 前部，确保 Meson 能找到 pkg-config.exe
            build_env[path_key] = f"{gst_root_bin};{existing_path}"
            print(f"✓ 已将 GStreamer bin 目录加入 PATH: {gst_root_bin}")

    return all_ok, build_env, compiler_label


# ═══════════════════════════════════════════════════════════════
# 安装主流程
# ═══════════════════════════════════════════════════════════════

def install_pygobject() -> int:
    """
    在修正的环境中安装 PyGObject。
    自动检测编译器（MSVC → GCC）和 GStreamer 变体。
    :return: pip 进程退出码
    """
    print("=" * 60)
    print("PyGObject Windows 安装辅助脚本")
    print("=" * 60)
    print()

    prerequisites_ok, build_env, compiler_label = check_prerequisites()
    if not prerequisites_ok:
        print()
        print("前提条件未满足，请按上述提示修复后重试。")
        return 1

    print()
    print(f"编译器: {compiler_label}")
    print(f"PKG_CONFIG_PATH: {build_env.get('PKG_CONFIG_PATH', '未设置')}")
    print()
    print("开始安装 PyGObject...")
    print("-" * 60)

    # 执行 pip install（在捕获的编译环境中）
    # PyGObject 3.52+ 要求 girepository-2.0（GLib ≥ 2.80），
    # GStreamer MSVC 安装仅提供 gobject-introspection-1.0，
    # 因此固定 PyGObject < 3.52 使用旧 API
    pip_result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "PyGObject>=3.50.0,<3.52"],
        env=build_env,
    )

    if pip_result.returncode == 0:
        print()
        print("✓ PyGObject 安装成功！")
    else:
        print()
        print("✗ PyGObject 安装失败。")
        print("可能的原因：")
        print("  1. GStreamer 未选择 Complete 安装（缺少开发文件）")
        if "MSVC" in compiler_label:
            print("  2. Visual Studio 缺少 C++ 桌面开发组件")
        else:
            print("  2. GCC 版本不兼容，尝试安装 Visual Studio")
        print("  3. 网络问题导致下载失败")
        print("  4. 尝试切换编译器：设置 CC 环境变量指定编译器路径")

    return pip_result.returncode


if __name__ == "__main__":
    sys.exit(install_pygobject())
