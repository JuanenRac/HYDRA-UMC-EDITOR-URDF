# =============================================================================
# HYDRA-UMC EDITOR-URDF - tests/test_mesh_prefetch.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# Reading the meshes of a robot away from the interface thread: which files are read, that a bad file does not stop
# the rest, that a newer load cancels the one in flight, and that the mesh cache survives several threads.
# =============================================================================
from __future__ import annotations

import threading
from pathlib import Path

import numpy as np
import pytest
from stl import mesh as stl_mesh

from hydra_editor_urdf.models import BoxGeometry, Link, MeshGeometry, Robot, Visual
from hydra_editor_urdf.render import mesh as mesh_module
from hydra_editor_urdf.render.mesh import clear_mesh_cache, load_mesh_file
from hydra_editor_urdf.render.mesh_prefetch import mesh_jobs, prefetch_meshes


@pytest.fixture(autouse=True)
def _fresh_cache(monkeypatch):
    clear_mesh_cache()
    monkeypatch.setattr("hydra_editor_urdf.i18n.load_config", lambda: {})
    yield
    clear_mesh_cache()


def _cube(path: Path, side: float = 0.1) -> None:
    cube = stl_mesh.Mesh(np.zeros(2, dtype=stl_mesh.Mesh.dtype))
    cube.vectors[0] = [[0, 0, 0], [side, 0, 0], [0, side, side]]
    cube.vectors[1] = [[side, 0, 0], [side, side, side], [0, side, side]]
    cube.save(str(path))


def _robot(*visuals_per_link: list[Visual]) -> Robot:
    robot = Robot(name="r")
    for index, visuals in enumerate(visuals_per_link):
        robot.links[f"l{index}"] = Link(name=f"l{index}", visuals=visuals)
    return robot


def _mesh_visual(name: str, scale=(1.0, 1.0, 1.0)) -> Visual:
    return Visual(geometry=MeshGeometry(filename=name, scale=scale))


def test_jobs_are_the_distinct_resolved_meshes(tmp_path: Path) -> None:
    _cube(tmp_path / "a.stl")
    robot = _robot([_mesh_visual("a.stl"), Visual(geometry=BoxGeometry())], [_mesh_visual("a.stl"), _mesh_visual("gone.stl")])

    jobs = mesh_jobs(robot, lambda name: tmp_path / name if name == "a.stl" else None)

    assert jobs == [(tmp_path / "a.stl", True)]


def test_a_scaled_mesh_is_a_separate_job_without_the_size_guess(tmp_path: Path) -> None:
    _cube(tmp_path / "a.stl")
    robot = _robot([_mesh_visual("a.stl"), _mesh_visual("a.stl", scale=(2.0, 2.0, 2.0))])

    jobs = mesh_jobs(robot, lambda name: tmp_path / name)

    assert jobs == [(tmp_path / "a.stl", True), (tmp_path / "a.stl", False)]


def test_no_robot_has_no_jobs() -> None:
    assert mesh_jobs(None, lambda name: None) == []
    assert prefetch_meshes(None, lambda name: None) == 0


def test_prefetch_warms_the_cache_and_skips_a_broken_file(tmp_path: Path) -> None:
    _cube(tmp_path / "ok.stl")
    (tmp_path / "bad.stl").write_bytes(b"not a mesh")
    (tmp_path / "odd.xyz").write_bytes(b"x")
    robot = _robot([_mesh_visual("bad.stl"), _mesh_visual("odd.xyz"), _mesh_visual("ok.stl")])

    assert prefetch_meshes(robot, lambda name: tmp_path / name) == 1
    assert len(mesh_module._mesh_cache) == 1
    assert load_mesh_file(tmp_path / "ok.stl") is load_mesh_file(tmp_path / "ok.stl")  # a cache hit returns the same object


def test_a_stop_request_ends_the_read_before_the_next_file(tmp_path: Path) -> None:
    for name in ("a.stl", "b.stl", "c.stl"):
        _cube(tmp_path / name)
    robot = _robot([_mesh_visual("a.stl"), _mesh_visual("b.stl"), _mesh_visual("c.stl")])
    asked: list[int] = []

    def should_stop() -> bool:
        asked.append(1)
        return len(asked) > 1  # allows the first file only

    assert prefetch_meshes(robot, lambda name: tmp_path / name, should_stop=should_stop) == 1


def test_several_threads_can_load_the_same_mesh(tmp_path: Path) -> None:
    _cube(tmp_path / "shared.stl")
    results: list[object] = []
    errors: list[BaseException] = []

    def work() -> None:
        try:
            results.append(load_mesh_file(tmp_path / "shared.stl"))
        except BaseException as exc:  # pragma: no cover - the test fails below
            errors.append(exc)

    threads = [threading.Thread(target=work) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert not errors
    assert len(results) == 8
    assert len(mesh_module._mesh_cache) == 1
    assert mesh_module._mesh_cache_bytes == mesh_module._mesh_bytes(results[0])
