<!-- =============================================================================
HYDRA-UMC-EDITOR-URDF - Architecture guide
Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE
============================================================================= -->

# Architecture

The editor is a local desktop workspace for loading, inspecting, editing and
exporting URDF descriptions. `main.py` owns the application entry point;
parsing, feasibility validation, mesh references and 3D preview are separate
lanes so an invalid robot description is reported before an export is offered.

The editor does not connect to a robot, upload a URDF or command motion. A
saved file is an authoring artifact; a downstream runtime must validate it
again against its own limits.
