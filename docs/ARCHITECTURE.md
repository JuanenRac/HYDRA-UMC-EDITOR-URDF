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

The editor does not connect to a robot or command motion, and never uploads a
model as a side effect of loading, editing or exporting it. It does support
two separate, explicit-action-only network paths: reading a named GitHub
repository to fetch a URDF and its meshes (read-only), and pushing/pulling a
model to/from HYDRA-UMC-SERVER once the operator supplies their own
credentials in the Upload panel. See
[`INTEGRATION_CONTRACT.md`](INTEGRATION_CONTRACT.md) for the exact boundary
of both. A saved file is an authoring artifact; a downstream runtime must
validate it again against its own limits.
