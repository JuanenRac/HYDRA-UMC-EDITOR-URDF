# =============================================================================
# HYDRA-UMC EDITOR-URDF - tests/test_input_safety.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# A URDF and its meshes come from third parties. These tests pin down that
# the mesh resolver stays inside the folders it was given, that broken mesh
# files are reported instead of crashing, that the XML parser refuses DTDs
# and entities, that a non-finite limit is not feasible and that an export
# never destroys the original file.
# =============================================================================
from __future__ import annotations

import struct

import pytest

from hydra_editor_urdf.models import Joint, JointLimit, JointType, Link, Robot
from hydra_editor_urdf.render.mesh import MalformedMeshFile, load_mesh_file
from hydra_editor_urdf.source.scan import build_mesh_resolver
from hydra_editor_urdf.urdf.dof import validate
from hydra_editor_urdf.urdf.parser import UrdfParseError, parse_urdf_string

BINARY_STL_HEADER = b"\0" * 80


def _repo(tmp_path):
    repo = tmp_path / "repo"
    (repo / "urdf").mkdir(parents=True)
    (repo / "meshes").mkdir()
    (repo / "meshes" / "link1.stl").write_bytes(b"solid x\nendsolid x\n")
    (tmp_path / "secret.stl").write_bytes(b"outside the repository")
    (tmp_path / "secret.txt").write_text("outside the repository")
    return repo


def test_a_mesh_path_that_climbs_out_of_the_repo_is_not_resolved(tmp_path):
    repo = _repo(tmp_path)
    resolve = build_mesh_resolver(repo, repo / "urdf")
    assert resolve("../../secret.stl") is None
    assert resolve("package://pkg/../../../secret.stl") is None


def test_an_absolute_path_or_file_uri_outside_the_repo_is_not_resolved(tmp_path):
    repo = _repo(tmp_path)
    resolve = build_mesh_resolver(repo, repo / "urdf")
    assert resolve(str(tmp_path / "secret.stl")) is None
    assert resolve((tmp_path / "secret.stl").as_uri()) is None


def test_only_mesh_files_are_ever_resolved(tmp_path):
    repo = _repo(tmp_path)
    (repo / "urdf" / "notes.txt").write_text("hello")
    resolve = build_mesh_resolver(repo, repo / "urdf")
    assert resolve("notes.txt") is None
    assert resolve("../../secret.txt") is None


def test_meshes_inside_the_repo_still_resolve(tmp_path):
    repo = _repo(tmp_path)
    resolve = build_mesh_resolver(repo, repo / "urdf")
    assert resolve("../meshes/link1.stl") == (repo / "meshes" / "link1.stl").resolve()
    assert resolve("package://pkg/meshes/link1.stl") == (repo / "meshes" / "link1.stl").resolve()
    assert resolve(str(repo / "meshes" / "link1.stl")) == (repo / "meshes" / "link1.stl").resolve()


def test_an_extra_root_the_operator_chose_is_allowed(tmp_path):
    repo = _repo(tmp_path)
    resolve = build_mesh_resolver(repo, repo / "urdf", extra_roots=[tmp_path])
    assert resolve("secret.stl") == (tmp_path / "secret.stl").resolve()


def test_an_empty_stl_is_a_malformed_mesh_not_a_crash(tmp_path):
    empty = tmp_path / "empty.stl"
    empty.write_bytes(BINARY_STL_HEADER + struct.pack("<I", 0))
    with pytest.raises(MalformedMeshFile):
        load_mesh_file(empty)


def test_a_truncated_stl_is_a_malformed_mesh_not_a_crash(tmp_path):
    truncated = tmp_path / "cut.stl"
    truncated.write_bytes(BINARY_STL_HEADER + struct.pack("<I", 5) + b"\0" * 20)
    with pytest.raises(MalformedMeshFile):
        load_mesh_file(truncated)


def test_obj_without_faces_or_with_a_bad_index_is_malformed(tmp_path):
    comments = tmp_path / "comments.obj"
    comments.write_text("# nothing here\n")
    with pytest.raises(MalformedMeshFile):
        load_mesh_file(comments)
    bad_face = tmp_path / "bad.obj"
    bad_face.write_text("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 9\n")
    with pytest.raises(MalformedMeshFile):
        load_mesh_file(bad_face)
    not_finite = tmp_path / "nan.obj"
    not_finite.write_text("v nan 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n")
    with pytest.raises(MalformedMeshFile):
        load_mesh_file(not_finite)


def test_a_valid_obj_still_loads(tmp_path):
    good = tmp_path / "good.obj"
    good.write_text("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n")
    assert len(load_mesh_file(good).vertices) == 3


def test_the_parser_refuses_doctype_and_entities():
    bomb = '<?xml version="1.0"?><!DOCTYPE robot [<!ENTITY a "x">]><robot name="&a;"/>'
    with pytest.raises(UrdfParseError):
        parse_urdf_string(bomb)


def _arm(limit: JointLimit) -> Robot:
    robot = Robot(name="arm")
    names = ["base", "l1", "l2", "l3"]
    for name in names:
        robot.links[name] = Link(name=name)
    for index in range(3):
        robot.joints[f"j{index}"] = Joint(
            name=f"j{index}",
            type=JointType.REVOLUTE,
            parent=names[index],
            child=names[index + 1],
            limit=limit if index == 0 else JointLimit(lower=-1.0, upper=1.0, effort=1.0, velocity=1.0),
        )
    return robot


def test_a_non_finite_limit_makes_the_robot_infeasible():
    good = validate(_arm(JointLimit(lower=-1.0, upper=1.0, effort=1.0, velocity=1.0)))
    assert good.is_feasible
    for bad in (float("nan"), float("inf")):
        report = validate(_arm(JointLimit(lower=bad, upper=1.0, effort=1.0, velocity=1.0)))
        assert not report.is_feasible
        assert any("finite" in reason for reason in report.reasons)


def test_export_keeps_the_first_original_and_writes_atomically(tmp_path, monkeypatch):
    from hydra_editor_urdf.app import EditorController

    controller = EditorController.__new__(EditorController)
    controller.robot = _arm(JointLimit(lower=-1.0, upper=1.0, effort=1.0, velocity=1.0))
    monkeypatch.setattr(EditorController, "export_urdf_string", lambda self: "<robot name='arm'/>")
    target = tmp_path / "arm.urdf"
    target.write_text("ORIGINAL")
    controller.export_urdf_file(target)
    controller.export_urdf_file(target)
    assert (tmp_path / "arm.urdf.bak").read_text() == "ORIGINAL"
    assert target.read_text() == "<robot name='arm'/>"
    assert not (tmp_path / "arm.urdf.tmp").exists()
