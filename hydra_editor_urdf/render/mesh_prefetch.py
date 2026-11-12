# =============================================================================
# HYDRA-UMC EDITOR-URDF - render/mesh_prefetch.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# Reads the meshes of a robot into the mesh cache (render/mesh.py) away from the interface thread. Reading a large
# STL or OBJ takes long enough to freeze the window, so the viewport panel runs prefetch_meshes() on a QThread and
# rebuilds the GPU buffers on the interface thread afterwards, when every read is a cache hit. Nothing here
# touches Qt or OpenGL, so it is tested without a display.
# =============================================================================
from __future__ import annotations

from pathlib import Path
from typing import Callable

from hydra_editor_urdf.models import MeshGeometry, Robot
from hydra_editor_urdf.render.mesh import MalformedMeshFile, UnsupportedMeshFormat, load_mesh_file


def mesh_jobs(robot: Robot | None, resolver: Callable[[str], "Path | None"]) -> list[tuple[Path, bool]]:
    """The distinct (file, size-guess) pairs the viewport will read for this robot, in the order of the links.
    A mesh the resolver cannot find is left out: the renderer reports it as missing."""
    if robot is None:
        return []
    jobs: list[tuple[Path, bool]] = []
    seen: set[tuple[Path, bool]] = set()
    for link in robot.links.values():
        for visual in link.visuals:
            geometry = visual.geometry
            if not isinstance(geometry, MeshGeometry):
                continue
            resolved = resolver(geometry.filename)
            if resolved is None:
                continue
            job = (Path(resolved), geometry.scale == (1.0, 1.0, 1.0))
            if job not in seen:
                seen.add(job)
                jobs.append(job)
    return jobs


def prefetch_meshes(
    robot: Robot | None,
    resolver: Callable[[str], "Path | None"],
    should_stop: Callable[[], bool] = lambda: False,
) -> int:
    """Reads every mesh of the robot into the cache and returns how many were read. A file that cannot be read is
    skipped (the renderer reports it); `should_stop` is asked before each file so a newer load can cancel this one."""
    read = 0
    for path, fallback in mesh_jobs(robot, resolver):
        if should_stop():
            break
        try:
            load_mesh_file(path, fallback=fallback)
        except (UnsupportedMeshFormat, MalformedMeshFile, OSError, ValueError):
            continue
        read += 1
    return read
