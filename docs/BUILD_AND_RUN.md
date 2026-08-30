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

Run `main.py` from an environment that satisfies `requirements.txt`. Keep
external URDF and mesh paths local and review them before opening them.
