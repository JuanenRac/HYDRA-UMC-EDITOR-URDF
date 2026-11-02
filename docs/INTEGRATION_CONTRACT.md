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

## License gate and attribution before a push

`push_license_gate` in `hydra_editor_urdf_config.json` is `off` unless it says `warn` or `block` (anything else is `off`). When it is on, `StudioClient.push_model` looks, for every mesh the URDF uses, for LICENSE, COPYING, NOTICE, ATTRIBUTION and COPYRIGHT files in the folders from the mesh up to the folder that was opened, and guesses the license from well-known sentences (`source/licenses.py`; this is a help, not legal advice).

| Key | Default | Meaning |
|---|---|---|
| `push_license_gate` | `off` | `warn`: the push goes on; `block`: the push is refused with the list of meshes that fail |
| `push_license_require_file` | `true` | a mesh with no license-like file fails |
| `push_license_blocked` | `["CC-BY-NC"]` | licenses (as `guess_license` names them) that fail |

With `warn` or `block` the text of the attribution (the nearest license file of each mesh) goes at the top of `urdfXml` as an XML comment, so the server stores it next to the meshes without any new field in `POST /api/models/submit`.

## Golden URDF set

`tests/golden/` is the set of files that this editor, HYDRA-UMC-EDITOR-STL (the rotation of a placement) and HYDRA-UMC-PHYSICS-REPLICA (`fk`) all check. `cases.json` gives, for each robot and set of joint values, where every joint frame must be (meters, base frame, tolerance 1e-6); `rotations.json` gives rpy and the matrix it stands for. The numbers come from `tools/make_golden_urdf.py`, which uses plain matrix products and neither numpy nor editor code. `MANIFEST.sha256` lists the files (line endings are ignored when hashing); `tools/golden_sync.py --check` compares the copies next to this checkout.
