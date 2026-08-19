# =============================================================================
# HYDRA-UMC EDITOR-URDF - source/scan.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Given a folder of "whatever a real robot description repo looks like"
# (fetched from GitHub by github_fetcher.py, or pointed at directly by
# local_folder.py), finds the candidate URDF files and builds a mesh
# filename resolver - the one piece of real, unglamorous work every
# robot-porting session in this ecosystem's own past did by hand: a
# URDF's own <mesh filename="package://some_pkg/meshes/link1.stl"/> is
# essentially never a real, directly-openable path once the file is
# sitting in a plain downloaded folder instead of a live ROS workspace
# (where `package://` resolves via the ROS package index) - this module
# is what makes that resolution automatic instead of a manual "find and
# rename every mesh reference" pass.
# =============================================================================
from __future__ import annotations

from pathlib import Path
from typing import Callable

# What a real robot description repo's own URDF/mesh files use - checked
# in this order per candidate file so a `.stl` sibling of an unsupported
# `.dae` (a common real-world pairing: `.dae` for visual, `.stl` for
# collision) is still found if the resolver is asked for the collision
# geometry specifically, not just whichever came first alphabetically.
MESH_EXTENSIONS = (".stl", ".obj", ".dae")


def find_urdf_files(root: str | Path) -> list[Path]:
    """Every *.urdf AND *.xacro under `root`, recursively - xacro files
    are deliberately still returned here (not filtered out) so
    ui/panels/source_panel.py can list them and let urdf/parser.py's own
    UrdfParseError explain the xacro limitation per-file, rather than
    this function silently making some files disappear from the list
    with no explanation of why."""
    root = Path(root)
    if not root.is_dir():
        return []
    found = sorted(root.rglob("*.urdf")) + sorted(root.rglob("*.xacro"))
    return found


def _basename_index(root: Path) -> dict[str, list[Path]]:
    """filename (lowercase, no directory) -> every real file under `root`
    with that name - built once per resolver, not per lookup, since a
    real fetched repo can have thousands of files and this is called
    once per unique mesh reference in the URDF, not once per triangle."""
    index: dict[str, list[Path]] = {}
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in MESH_EXTENSIONS:
            index.setdefault(path.name.lower(), []).append(path)
    return index


def build_mesh_resolver(root: str | Path, urdf_file_dir: str | Path) -> Callable[[str], "Path | None"]:
    """Returns a function `resolve(mesh_filename: str) -> Path | None`
    that turns whatever a <mesh filename="..."> attribute contains into a
    real file under `root`, trying (in order):

    1. As a path relative to `urdf_file_dir` (the folder the URDF itself
       lives in) - correct for a URDF authored with plain relative mesh
       paths, the simplest and most common real-world case for a
       standalone (non-ROS-package) repo.
    2. As an absolute path, if it happens to already be one and exists
       (rare once a repo is moved to a new machine/folder, but free to try).
    3. By basename anywhere under `root` - the fallback that actually
       handles `package://some_pkg/meshes/link1.stl` (the scheme and
       package name are meaningless outside a live ROS workspace, but
       `link1.stl` alone is still a real, findable filename in the
       fetched folder almost all the time) and any other path form that
       doesn't survive being moved out of its original context. Returns
       the first match if more than one file shares that basename
       somewhere in the tree - ambiguous, but a same-named mesh file
       used by two different links in the same repo virtually always
       IS the same real file (e.g. a duplicated bolt/bracket mesh).
    """
    root = Path(root)
    urdf_file_dir = Path(urdf_file_dir)
    index: dict[str, list[Path]] | None = None  # built lazily - most resolvers are only ever asked for a handful of files

    def resolve(mesh_filename: str) -> Path | None:
        nonlocal index
        if not mesh_filename:
            return None

        # Strip a package:// (or any other scheme://) prefix down to its
        # own path tail - "package://some_pkg/meshes/link1.stl" ->
        # "meshes/link1.stl". A bare relative/absolute path has no "://"
        # and passes through unchanged.
        tail = mesh_filename.split("://", 1)[-1]
        # Drop a leading package name segment too (package:// URIs put
        # the ROS package name as the first path component, which has no
        # meaning as a real directory in a plain downloaded folder).
        tail_parts = Path(tail).parts
        tail_without_pkg = Path(*tail_parts[1:]) if len(tail_parts) > 1 else Path(tail)

        candidate = (urdf_file_dir / tail).resolve()
        if candidate.is_file():
            return candidate
        candidate = (urdf_file_dir / tail_without_pkg).resolve()
        if candidate.is_file():
            return candidate

        as_absolute = Path(mesh_filename)
        if as_absolute.is_absolute() and as_absolute.is_file():
            return as_absolute

        if index is None:
            index = _basename_index(root)
        basename = Path(tail).name.lower()
        matches = index.get(basename)
        return matches[0] if matches else None

    return resolve
