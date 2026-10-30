# =============================================================================
# HYDRA-UMC EDITOR-URDF - tests/test_mesh_unit.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The unit of a mesh: declared by the model, guessed from the size only when it is not.
# =============================================================================
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from stl import mesh as stl_mesh

from hydra_editor_urdf.render import mesh as mesh_module
from hydra_editor_urdf.render.mesh import clear_mesh_cache, declared_unit, load_mesh_file


def _write_cube(path: Path, side: float) -> None:
    cube = stl_mesh.Mesh(np.zeros(2, dtype=stl_mesh.Mesh.dtype))
    cube.vectors[0] = [[0, 0, 0], [side, 0, 0], [0, side, side]]
    cube.vectors[1] = [[side, 0, 0], [side, side, side], [0, side, side]]
    cube.save(str(path))


@pytest.fixture(autouse=True)
def _fresh_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_mesh_cache()
    monkeypatch.setattr("hydra_editor_urdf.i18n.load_config", lambda: {})


def _span(mesh) -> float:
    return float(np.max(mesh.vertices.max(axis=0) - mesh.vertices.min(axis=0)))


def test_a_small_part_in_millimeters_is_scaled_when_the_model_declares_the_unit(tmp_path: Path) -> None:
    (tmp_path / "metadata.json").write_text(json.dumps({"unit": "mm"}), encoding="utf-8")
    _write_cube(tmp_path / "nozzle.stl", 3.0)  # a 3 mm nozzle, below the size guess

    assert declared_unit(tmp_path / "nozzle.stl") == "mm"
    assert _span(load_mesh_file(tmp_path / "nozzle.stl")) == pytest.approx(0.003)


def test_a_large_part_in_meters_is_left_alone_when_the_model_declares_the_unit(tmp_path: Path) -> None:
    (tmp_path / "metadata.json").write_text(json.dumps({"unit": "meters"}), encoding="utf-8")
    _write_cube(tmp_path / "hall.stl", 8.0)  # 8 m: the size guess alone would call it millimeters

    assert _span(load_mesh_file(tmp_path / "hall.stl")) == pytest.approx(8.0)


def test_without_a_declared_unit_the_size_guess_is_the_fallback(tmp_path: Path) -> None:
    _write_cube(tmp_path / "arm.stl", 400.0)
    _write_cube(tmp_path / "small.stl", 0.4)

    assert declared_unit(tmp_path / "arm.stl") is None
    assert _span(load_mesh_file(tmp_path / "arm.stl")) == pytest.approx(0.4)
    assert _span(load_mesh_file(tmp_path / "small.stl")) == pytest.approx(0.4)


def test_the_fallback_is_off_for_a_mesh_the_urdf_scales_itself(tmp_path: Path) -> None:
    _write_cube(tmp_path / "arm.stl", 400.0)

    assert _span(load_mesh_file(tmp_path / "arm.stl", fallback=False)) == pytest.approx(400.0)
    assert _span(load_mesh_file(tmp_path / "arm.stl")) == pytest.approx(0.4)  # the cache keeps both answers apart


def test_the_span_of_the_fallback_comes_from_the_configuration_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_cube(tmp_path / "part.stl", 50.0)
    monkeypatch.setattr("hydra_editor_urdf.i18n.load_config", lambda: {"mesh_millimeter_span": 100})
    assert _span(load_mesh_file(tmp_path / "part.stl")) == pytest.approx(50.0)
    monkeypatch.setattr("hydra_editor_urdf.i18n.load_config", lambda: {"mesh_millimeter_span": 0})
    assert _span(load_mesh_file(tmp_path / "part.stl")) == pytest.approx(50.0)
    assert mesh_module.millimeter_span() == 0.0


def test_a_broken_or_unknown_declaration_does_not_stop_the_load(tmp_path: Path) -> None:
    (tmp_path / "metadata.json").write_text("{not json", encoding="utf-8")
    _write_cube(tmp_path / "arm.stl", 400.0)
    assert declared_unit(tmp_path / "arm.stl") is None
    assert _span(load_mesh_file(tmp_path / "arm.stl")) == pytest.approx(0.4)
    (tmp_path / "metadata.json").write_text(json.dumps({"unit": "furlong"}), encoding="utf-8")
    clear_mesh_cache()
    assert declared_unit(tmp_path / "arm.stl") is None
