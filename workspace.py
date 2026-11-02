#!/usr/bin/env python3
"""
Warband Modding Workspace
统一战团 Mod 开发工作区主入口
"""
import sys
import os

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ==================== Linux DRM / NVIDIA 驱动崩溃防御 ====================
os.environ["QT_XCB_FORCE_SOFTWARE_OPENGL"] = "1"
os.environ["LIBGL_ALWAYS_SOFTWARE"] = "1"
os.environ["QT_QUICK_BACKEND"] = "software"
# =======================================================================

from apps.mod_launcher.workspace_window import main

if __name__ == "__main__":
    main()

