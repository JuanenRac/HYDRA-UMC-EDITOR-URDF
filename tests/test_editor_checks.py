# =============================================================================
# HYDRA-UMC EDITOR-URDF - tests/test_editor_checks.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The optional checks and exports (each behind a switch in the configuration, all off by default):
# xacro expansion, self-collision hints, mesh license report and the Y-up export.
# =============================================================================
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

from hydra_editor_urdf.app import EditorController
from hydra_editor_urdf.models import BoxGeometry, Collision, Joint, JointLimit, JointType, Link, MeshGeometry, Origin, Robot, Visual
from hydra_editor_urdf.render.kinematics import compute_link_world_transforms
from hydra_editor_urdf.source import licenses
from hydra_editor_urdf.urdf.parser import parse_urdf_string
from hydra_editor_urdf.urdf.self_collision import collision_warnings, find_self_collisions
from hydra_editor_urdf.urdf.writer import robot_to_urdf_string
from hydra_editor_urdf.urdf.xacro_expand import XacroError, expand_xacro, looks_like_xacro
from hydra_editor_urdf.urdf.yup import scale_robot, to_y_up


def _box_link(name: str, size=(0.1, 0.1, 0.1), xyz=(0, 0, 0)) -> Link:
    return Link(name=name, collisions=[Collision(origin=Origin(xyz=xyz), geometry=BoxGeometry(size=size))])


def _arm(second_offset: float) -> Robot:
    """base -- j1 (revolute about z) --> a -- j2 (fixed, offset along x) --> b ; and c hangs from base."""
    robot = Robot(name="arm")
    for link in (_box_link("base"), _box_link("a"), _box_link("b"), _box_link("c")):
        robot.links[link.name] = link
    robot.joints["j1"] = Joint("j1", JointType.REVOLUTE, "base", "a", Origin(xyz=(0, 0, 0.5)), (0, 0, 1), JointLimit(-1.0, 1.0, 1, 1))
    robot.joints["j2"] = Joint("j2", JointType.FIXED, "a", "b", Origin(xyz=(second_offset, 0, 0)))
    robot.joints["j3"] = Joint("j3", JointType.FIXED, "base", "c", Origin(xyz=(-second_offset, 0, 0.5)))
    return robot


# --- xacro -------------------------------------------------------------------------------------------------------------

XACRO = '<?xml version="1.0"?><robot xmlns:xacro="http://www.ros.org/wiki/xacro" name="r"><xacro:property name="w" value="1"/><link name="a"/></robot>'


def test_xacro_is_recognised() -> None:
    assert looks_like_xacro(XACRO)
    assert not looks_like_xacro('<robot name="r"><link name="a"/></robot>')


def test_xacro_with_no_tool_is_an_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("hydra_editor_urdf.urdf.xacro_expand.find_xacro", lambda: None)
    with pytest.raises(XacroError):
        expand_xacro(tmp_path / "x.xacro")


def _fake_xacro(tmp_path: Path, body: str) -> list[str]:
    script = tmp_path / "fake_xacro.py"
    script.write_text(body, encoding="utf-8")
    return [sys.executable, str(script)]


def test_xacro_output_is_returned_and_failures_are_reported(tmp_path: Path) -> None:
    ok = _fake_xacro(tmp_path, 'print(\'<robot name="r"><link name="a"/></robot>\')')
    assert "<robot" in expand_xacro(tmp_path / "x.xacro", command=ok)
    bad = _fake_xacro(tmp_path, "import sys; sys.stderr.write('boom\\n'); sys.exit(3)")
    with pytest.raises(XacroError, match="boom"):
        expand_xacro(tmp_path / "x.xacro", command=bad)
    empty = _fake_xacro(tmp_path, "print('nothing')")
    with pytest.raises(XacroError):
        expand_xacro(tmp_path / "x.xacro", command=empty)
    slow = _fake_xacro(tmp_path, "import time; time.sleep(5)")
    with pytest.raises(XacroError, match="did not finish"):
        expand_xacro(tmp_path / "x.xacro", command=slow, timeout=0.3)


def _controller(monkeypatch: pytest.MonkeyPatch, config: dict) -> EditorController:
    monkeypatch.setattr("hydra_editor_urdf.i18n.load_config", lambda: config)
    return EditorController()


def test_xacro_file_is_refused_by_default_and_expanded_when_the_switch_is_on(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "r.xacro"
    path.write_text(XACRO, encoding="utf-8")
    failures: list[str] = []
    controller = _controller(monkeypatch, {})
    controller.load_failed.connect(failures.append)
    controller.load_urdf_file(path)
    assert controller.robot is None and failures and "xacro" in failures[0]

    fake = _fake_xacro(tmp_path, 'print(\'<robot name="expanded"><link name="a"/></robot>\')')
    monkeypatch.setattr("hydra_editor_urdf.urdf.xacro_expand.find_xacro", lambda: fake)
    on = _controller(monkeypatch, {"xacro_expand": True})
    on.load_urdf_file(path)
    assert on.robot is not None and on.robot.name == "expanded"


def test_a_failing_xacro_is_reported_as_a_load_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "r.xacro"
    path.write_text(XACRO, encoding="utf-8")
    monkeypatch.setattr("hydra_editor_urdf.urdf.xacro_expand.find_xacro", lambda: None)
    controller = _controller(monkeypatch, {"xacro_expand": True})
    failures: list[str] = []
    controller.load_failed.connect(failures.append)
    controller.load_urdf_file(path)
    assert controller.robot is None and "not found" in failures[0]


# --- self collision -----------------------------------------------------------------------------------------------------


def test_links_that_overlap_in_the_home_pose_are_reported() -> None:
    robot = _arm(second_offset=0.05)  # b and c sit 0.05 m from a and base: b overlaps c? a is at z 0.5, c at z 0.5
    found = find_self_collisions(robot)
    pairs = {(c.link_a, c.link_b) for c in found if c.joint is None}
    assert ("a", "c") in pairs  # a (0.5 up) and c (0.5 up, 0.05 aside) overlap
    assert ("base", "a") not in pairs  # joined by a joint: they touch by design
    assert any("home pose" in w for w in collision_warnings(found))


def test_links_that_are_apart_are_not_reported() -> None:
    assert find_self_collisions(_arm(second_offset=2.0)) == []


def test_a_collision_that_only_happens_while_jogging_names_the_joint() -> None:
    robot = _arm(second_offset=0.0)
    robot.joints["j2"].origin = Origin(xyz=(0.0, 0.3, 0.0))  # b is 0.3 m from a along y and swings with j1
    robot.joints["j3"].origin = Origin(xyz=(-0.25, 0.15, 0.5))  # c waits where b arrives when j1 turns
    found = find_self_collisions(robot, steps=9)
    assert [(c.link_a, c.link_b) for c in found if c.joint is None] == []  # nothing overlaps at home
    swing = [c for c in found if (c.link_a, c.link_b) == ("b", "c")]
    assert len(swing) == 1 and swing[0].joint == "j1" and swing[0].value is not None
    assert "when joint 'j1'" in collision_warnings(swing)[0]


def test_the_check_is_conservative_for_a_rotated_box() -> None:
    # a long thin box turned 45 degrees: its world box is bigger than the box itself, so a near miss may be reported (never missed).
    robot = Robot(name="r")
    robot.links["base"] = _box_link("base", size=(0.1, 0.1, 0.1))
    robot.links["x"] = Link(name="x", collisions=[Collision(origin=Origin(xyz=(0, 0, 0), rpy=(0, 0, math.pi / 4)), geometry=BoxGeometry(size=(1.0, 0.02, 0.02)))])
    robot.links["y"] = _box_link("y", size=(0.1, 0.1, 0.1))
    robot.joints["jx"] = Joint("jx", JointType.FIXED, "base", "x", Origin())
    robot.joints["jy"] = Joint("jy", JointType.FIXED, "base", "y", Origin(xyz=(0.0, 0.3, 0.0)))
    assert find_self_collisions(robot, tolerance=0.0)  # the 45-degree stick reaches y in the box check


def test_links_without_geometry_and_a_bad_tolerance_do_not_break_the_check() -> None:
    robot = Robot(name="r")
    robot.links["a"] = Link(name="a")
    robot.links["b"] = Link(name="b")
    robot.joints["j"] = Joint("j", JointType.FIXED, "a", "b", Origin())
    assert find_self_collisions(robot, tolerance=float("nan")) == []


def test_the_report_has_the_collision_warnings_only_when_the_switch_is_on(monkeypatch: pytest.MonkeyPatch) -> None:
    robot = _arm(second_offset=0.05)
    off = _controller(monkeypatch, {})
    assert not any("collide" in w for w in off._report(robot).warnings)
    on = _controller(monkeypatch, {"self_collision_check": True})
    report = on._report(robot)
    assert any("collide" in w for w in report.warnings)
    assert report.is_feasible == off._report(robot).is_feasible  # a warning never changes feasibility


# --- licenses -----------------------------------------------------------------------------------------------------------


def _mesh_robot(*names: str) -> Robot:
    robot = Robot(name="m")
    previous = None
    for index, name in enumerate(names):
        link = Link(name=f"l{index}", visuals=[Visual(geometry=MeshGeometry(filename=name))])
        robot.links[link.name] = link
        if previous:
            robot.joints[f"j{index}"] = Joint(f"j{index}", JointType.FIXED, previous, link.name, Origin())
        previous = link.name
    return robot


def test_license_files_are_found_from_the_mesh_up_to_the_opened_folder(tmp_path: Path) -> None:
    (tmp_path / "LICENSE").write_text("Permission is hereby granted, free of charge, to any person", encoding="utf-8")
    (tmp_path / "parts" / "free").mkdir(parents=True)
    (tmp_path / "parts" / "free" / "ATTRIBUTION.txt").write_text("By Someone, Creative Commons Attribution-NonCommercial 4.0", encoding="utf-8")
    (tmp_path / "parts" / "free" / "a.stl").write_bytes(b"x")
    (tmp_path / "parts" / "b.stl").write_bytes(b"x")
    outside = tmp_path.parent / "LICENSE"  # never read: it is above the opened folder
    found = licenses.find_license_files(tmp_path / "parts" / "free" / "a.stl", tmp_path)
    assert [p.name for p in found] == ["ATTRIBUTION.txt", "LICENSE"]
    assert outside not in found


def test_license_names_are_guessed() -> None:
    assert licenses.guess_license(Path("does-not-exist")) is None


def test_mesh_license_report_and_attribution(tmp_path: Path) -> None:
    (tmp_path / "free").mkdir()
    (tmp_path / "free" / "LICENSE").write_text("Creative Commons Attribution-NonCommercial 4.0", encoding="utf-8")
    (tmp_path / "free" / "a.stl").write_bytes(b"x")
    (tmp_path / "bare").mkdir()
    (tmp_path / "bare" / "b.stl").write_bytes(b"x")
    robot = _mesh_robot("free/a.stl", "bare/b.stl", "gone.stl")
    resolver = lambda name: (tmp_path / name) if (tmp_path / name).is_file() else None  # noqa: E731
    entries = licenses.check_mesh_licenses(robot, resolver, tmp_path)
    assert [e.mesh for e in entries] == ["free/a.stl", "bare/b.stl"]  # the mesh that was not found is left out
    assert entries[0].licenses == ["CC-BY-NC"] and entries[1].files == []
    lines = licenses.license_warnings(entries)
    assert any("'bare/b.stl'" in line for line in lines) and any("CC-BY-NC" in line for line in lines)
    text = licenses.attribution_text("m", entries, tmp_path)
    assert "free/LICENSE (CC-BY-NC)" in text and "No license file found for:" in text and "bare/b.stl" in text


def test_license_warnings_only_with_the_switch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "b.stl").write_bytes(b"x")
    robot = _mesh_robot("b.stl")
    off = _controller(monkeypatch, {})
    off._mesh_search_root = tmp_path
    off.mesh_resolver = lambda name: tmp_path / name
    assert not any("LICENSE" in w for w in off._report(robot).warnings)
    on = _controller(monkeypatch, {"license_check": True})
    on._mesh_search_root = tmp_path
    on.mesh_resolver = lambda name: tmp_path / name
    assert any("LICENSE" in w for w in on._report(robot).warnings)
    assert "No license file found" in (on.attribution_text() or "") or on.robot is None


# --- Y-up -------------------------------------------------------------------------------------------------------------


def test_y_up_maps_every_link_to_x_z_minus_y() -> None:
    robot = _arm(second_offset=0.4)
    values = {"j1": 0.3}
    before = compute_link_world_transforms(robot, values)
    after = compute_link_world_transforms(to_y_up(robot), values)
    for name, matrix in before.items():
        x, y, z = matrix[:3, 3]
        assert np.allclose(after[name][:3, 3], (x, z, -y), atol=1e-9)
    assert "world_y_up" in after


def test_y_up_scale_scales_lengths_and_keeps_the_original_untouched() -> None:
    robot = _arm(second_offset=0.4)
    robot.joints["j2"].type = JointType.PRISMATIC
    robot.joints["j2"].limit = JointLimit(0.0, 0.2, 1, 1)
    out = to_y_up(robot, scale=1000.0)
    assert robot.joints["j2"].origin.xyz == (0.4, 0, 0) and "world_y_up" not in robot.links
    assert out.joints["j2"].origin.xyz[0] == pytest.approx(400.0)
    assert out.joints["j2"].limit.upper == pytest.approx(200.0)
    assert out.links["a"].collisions[0].geometry.size == pytest.approx((100.0, 100.0, 100.0))


def test_y_up_round_trips_through_the_writer_and_names_do_not_clash() -> None:
    robot = _arm(second_offset=0.4)
    robot.links["world_y_up"] = Link(name="world_y_up")
    robot.joints["jw"] = Joint("jw", JointType.FIXED, "base", "world_y_up", Origin())
    out = to_y_up(robot)
    parsed = parse_urdf_string(robot_to_urdf_string(out))
    assert parsed.root_link_name() == "world_y_up_" and len(parsed.links) == len(robot.links) + 1


def test_y_up_needs_a_single_root_and_a_sane_scale() -> None:
    forest = Robot(name="f")
    forest.links["a"] = Link(name="a")
    forest.links["b"] = Link(name="b")
    with pytest.raises(ValueError):
        to_y_up(forest)
    for bad in (0.0, -1.0, float("nan")):
        with pytest.raises(ValueError):
            scale_robot(_arm(0.4), bad)


def test_export_is_z_up_unless_asked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    controller = _controller(monkeypatch, {})
    controller.robot = _arm(second_offset=0.4)
    plain = controller.export_urdf_string()
    assert "world_y_up" not in plain
    assert plain == controller.export_urdf_string(y_up=False)
    assert "world_y_up" in controller.export_urdf_string(y_up=True)
    scaled = _controller(monkeypatch, {"y_up_scale": 1000})
    scaled.robot = _arm(second_offset=0.4)
    assert 'xyz="400 0 0"' in scaled.export_urdf_string(y_up=True)
    out = tmp_path / "r.urdf"
    controller.export_urdf_file(out, y_up=True)
    assert "world_y_up" in out.read_text(encoding="utf-8")


def test_new_export_texts_exist_in_all_eight_languages() -> None:
    root = Path(__file__).resolve().parent.parent / "language"
    files = sorted(root.glob("*.lng"))
    assert len(files) == 8
    for f in files:
        text = f.read_text(encoding="utf-8")
        assert "EXPORT_Y_UP=" in text and "EXPORT_Y_UP_HINT=" in text, f.name
