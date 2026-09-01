<!-- =============================================================================
HYDRA-UMC-EDITOR-URDF - Build and run guide
Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE
============================================================================= -->

# Build and Run

Use `build-test.bat` or `build-test.sh` for the non-mutating validation path.
It must not update the manifest or CHANGELOG. Use `build_exe.bat` or
`build_exe.sh` only when an executable package is actually required; inspect
its output before distributing it.

The validation path syntax-checks every Python source file.

Run `main.py` from an environment that satisfies `requirements.txt`. Keep
external URDF and mesh paths local and review them before opening them.

The command deck (top toolbar) is a real `QToolBar`/`QLabel`/`QToolButton`
strip, not a separate Qt Quick/QML UI - real per-project screenshots showed
the earlier `QQuickWidget`-based deck rendering as a solid black bar with
no console error (a `QQuickWidget` embedded in a `QToolBar` inside this
`QMainWindow`'s real `QDockWidget` layout never composited correctly), so
it was reverted to plain widgets, matching HYDRA-UMC-SUITE's own deck. It
is a view over the existing workspace, not a second editor: after a URDF
load (and after a live property edit), its target chip shows the loaded
model's name, DOF count and current Studio feasibility verdict. The
Source, DOF, Viewport, Properties and Upload buttons only raise their
corresponding existing docks; export retains the established backup-safe
writer and remains unavailable until a model is loaded.
