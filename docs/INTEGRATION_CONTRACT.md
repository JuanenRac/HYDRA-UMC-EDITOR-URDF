<!-- =============================================================================
HYDRA-UMC-EDITOR-URDF - Integration contract
Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE
============================================================================= -->

# Integration Contract

Input is a user-selected URDF and its declared local mesh references, OR a
GitHub repository the user names explicitly (a real, read-only zipball fetch -
`source/github_fetcher.py`). Output is a validated or rejected editable model
and, only after explicit save/export, a URDF artifact. Consumers must treat
that artifact as untrusted input and check joint names, limits, coordinate
frames and mesh locations themselves.

This project does provide two real network paths, both requiring an explicit
user action per use - neither is automatic, backgrounded, or triggered by
merely opening a file:

- **Reading a GitHub repository** (`source/github_fetcher.py`): downloads a
  public repo's zipball to fetch a URDF and its mesh references. Read-only -
  never pushes, authenticates, or writes back to GitHub.
- **Pushing/pulling a model to/from HYDRA-UMC-SERVER** (`server/client.py`'s
  `StudioClient`, driven from the Upload panel): real authenticated HTTP
  login/push/pull against `server.ts`'s own model-storage endpoints. Never
  sends motion commands, never authenticates as anything but the operator's
  own supplied credentials, and the Upload panel's own username/password
  fields start empty - no suggested credential of any kind.

No hardware-control authority, motion command, or robot connection is
provided by this project under any code path - that boundary is unaffected
by either network path above.
