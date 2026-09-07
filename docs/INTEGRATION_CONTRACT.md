<!-- =============================================================================
HYDRA-UMC-EDITOR-URDF - Integration contract
Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE
============================================================================= -->

# Integration Contract

Input is a user-selected URDF and its declared local mesh references. Output is
a validated or rejected editable model and, only after explicit save/export, a
URDF artifact. Consumers must treat that artifact as untrusted input and check
joint names, limits, coordinate frames and mesh locations themselves.

No network endpoint, remote loading contract or hardware-control authority is
provided by this project.
