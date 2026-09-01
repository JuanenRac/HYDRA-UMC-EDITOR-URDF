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

The validation path always syntax-checks the Python and Qt Quick sources. The
Qt Quick deck also needs the normal manual visual check from the desktop app:
headless/offscreen graphics drivers are not a reliable substitute for the
OpenGL and Qt Quick render paths used by this editor.

Run `main.py` from an environment that satisfies `requirements.txt`. Keep
external URDF and mesh paths local and review them before opening them.
