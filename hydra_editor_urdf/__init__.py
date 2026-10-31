# =============================================================================
# HYDRA-UMC EDITOR-URDF - hydra_editor_urdf/__init__.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# Package version - single source of truth, read by ui/main_window.py's own
# About dialog and rewritten in place by bump_version.py right before every
# real PyInstaller build (see build_exe.bat/.sh). MAJOR.MINOR.PATCH with an
# odometer-style carry rule applied by bump_version.py: PATCH goes up by 1
# per build; once PATCH would exceed 9 it resets to 0 and MINOR goes up by 1
# instead (e.g. 0.0.9 -> 0.1.0). MAJOR is never bumped automatically - that
# stays a deliberate manual decision, same convention across the ecosystem.
#
# Like every project of this ecosystem it starts at MAJOR 0.
# =============================================================================
__version__ = "0.1.7"