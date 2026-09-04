# =============================================================================
# HYDRA-UMC EDITOR-URDF - hydra_editor_urdf/__init__.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Package version - single source of truth, read by ui/main_window.py's own
# About dialog and rewritten in place by bump_version.py right before every
# real PyInstaller build (see build_exe.bat/.sh). MAJOR.MINOR.PATCH with an
# odometer-style carry rule applied by bump_version.py: PATCH goes up by 1
# per build; once PATCH would exceed 9 it resets to 0 and MINOR goes up by 1
# instead (e.g. 1.0.9 -> 1.1.0). MAJOR is never bumped automatically - that
# stays a deliberate manual decision, same convention across the ecosystem.
#
# Starts at 1.0.0 - this project had no version number at all before this
# was introduced (per [[No reference -> reuse, don't invent]] this mirrors
# the versioning policy rolled out ecosystem-wide, with no prior
# __version__/bump script in a sibling project to port from, so this file
# and bump_version.py are the first real implementation of it).
# =============================================================================
__version__ = "0.0.3"