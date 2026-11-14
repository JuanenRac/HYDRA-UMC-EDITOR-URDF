# =============================================================================
# HYDRA-UMC-EDITOR-URDF - tests/test_urdf_tools_edges.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The tools around the URDF at their edges: the change of scale and of axis, the call to xacro (missing, failing, silent, slow, good), and the search for links that
touch each other, on boxes whose overlap is known."""
from __future__ import annotations

import copy
import random
import sys
from pathlib import Path

import pytest

from hydra_editor_urdf.models import BoxGeometry, Inertial, Joint, JointLimit, JointType, Link, Origin, Robot, Visual
from hydra_editor_urdf.urdf import xacro_expand
from hydra_editor_urdf.urdf.dof import validate
from hydra_editor_urdf.urdf.self_collision import collision_warnings, find_self_collisions
from hydra_editor_urdf.urdf.yup import scale_robot, to_y_up
from test_simulation_bench import SEED, make_robot


# ---------------------------------------------------------------------------------------------------------------------------------- scale and axis
def test_a_scale_multiplies_every_length_and_the_inertia_by_the_square_and_leaves_the_mass_and_the_original_alone():
    robot = make_robot(random.Random(SEED), 4)
    robot.joints["joint2"].type = JointType.PRISMATIC
    robot.joints["joint2"].limit = JointLimit(-0.1, 0.2, 5.0, 1.0)
    before = copy.deepcopy(robot)
    scaled = scale_robot(robot, 2.0)
    assert robot.joints["joint2"].limit == before.joints["joint2"].limit and robot.links["base"].inertial == before.links["base"].inertial  # the original is untouched
    for name, joint in robot.joints.items():
        assert scaled.joints[name].origin.xyz == pytest.approx(tuple(2 * v for v in joint.origin.xyz))
        assert scaled.joints[name].origin.rpy == joint.origin.rpy
    assert scaled.joints["joint2"].limit.upper == pytest.approx(0.4)  # type: ignore[union-attr]
    for name, link in robot.links.items():
        inertial, again = link.inertial, scaled.links[name].inertial
        assert inertial is not None and again is not None
        assert again.mass == inertial.mass and again.ixx == pytest.approx(4 * inertial.ixx) and again.origin.xyz == pytest.approx(tuple(2 * v for v in inertial.origin.xyz))
        for before_shape, after_shape in zip(link.visuals, scaled.links[name].visuals, strict=True):
            assert after_shape.origin.xyz == pytest.approx(tuple(2 * v for v in before_shape.origin.xyz))


@pytest.mark.parametrize("factor", [0, -1.0, float("nan"), float("inf")])
def test_a_scale_that_is_not_a_positive_number_is_refused(factor):
    with pytest.raises(ValueError):
        scale_robot(make_robot(random.Random(SEED), 2), factor)


def test_every_kind_of_shape_is_scaled():
    from hydra_editor_urdf.models import CylinderGeometry, MeshGeometry, SphereGeometry

    robot = Robot(links={"a": Link("a", visuals=[Visual(geometry=CylinderGeometry(0.1, 0.4)), Visual(geometry=SphereGeometry(0.2)), Visual(geometry=MeshGeometry("m.stl", (1, 2, 3)))])})
    shapes = [v.geometry for v in scale_robot(robot, 3.0).links["a"].visuals]
    assert (shapes[0].radius, shapes[0].length) == pytest.approx((0.3, 1.2)) and shapes[1].radius == pytest.approx(0.6) and shapes[2].scale == (3, 6, 9)


def test_a_robot_with_no_single_root_cannot_be_turned_to_y_up_and_one_with_a_root_can():
    broken = Robot(links={"a": Link("a"), "b": Link("b")})
    with pytest.raises(ValueError, match="single root"):
        to_y_up(broken)
    robot = make_robot(random.Random(SEED + 1), 3)
    up = to_y_up(robot, 0.001)
    assert set(robot.links) <= set(up.links) and validate(up).root_link_name is not None
    assert up.joints["joint1"].origin.xyz == pytest.approx(tuple(0.001 * v for v in robot.joints["joint1"].origin.xyz))


# ----------------------------------------------------------------------------------------------------------------------------------------- xacro
@pytest.mark.parametrize(("text", "expected"), [
    ('<robot xmlns:xacro="http://www.ros.org/wiki/xacro" name="x"/>', True),
    ('<robot name="x"><xacro:macro name="m"/></robot>', True),
    ('<robot name="x"><!-- xacro? --></robot>', False),
    ('<robot name="x">' + " " * 3000 + '<link name="xacro"/></robot>', False),
    ("<robot name='x'/>", False),
    ("", False),
])
def test_a_file_is_taken_for_xacro_by_its_namespace_or_its_tags(text, expected):
    assert xacro_expand.looks_like_xacro(text) is expected


def test_the_tool_is_looked_for_on_the_path_and_ros2_is_the_second_choice(monkeypatch):
    monkeypatch.setattr(xacro_expand.shutil, "which", lambda name: None)
    assert xacro_expand.find_xacro() is None
    monkeypatch.setattr(xacro_expand.shutil, "which", lambda name: "/usr/bin/ros2" if name == "ros2" else None)
    assert xacro_expand.find_xacro() == ["/usr/bin/ros2", "run", "xacro", "xacro"]
    monkeypatch.setattr(xacro_expand.shutil, "which", lambda name: f"/usr/bin/{name}")
    assert xacro_expand.find_xacro() == ["/usr/bin/xacro"]


def _tool(tmp_path: Path, body: str) -> list[str]:
    script = tmp_path / "tool.py"
    script.write_text(body, encoding="utf-8")
    return [sys.executable, str(script)]


def test_xacro_that_answers_with_a_robot_is_returned_and_every_other_outcome_is_an_xacro_error(tmp_path: Path, monkeypatch):
    source = tmp_path / "model.xacro"
    source.write_text("<robot/>", encoding="utf-8")
    assert "<robot" in xacro_expand.expand_xacro(source, _tool(tmp_path, "print('<robot name=\"x\"/>')"))
    with pytest.raises(xacro_expand.XacroError, match="exit 3"):
        xacro_expand.expand_xacro(source, _tool(tmp_path, "import sys; sys.stderr.write('bad macro\\n'); sys.exit(3)"))
    with pytest.raises(xacro_expand.XacroError, match="no message"):
        xacro_expand.expand_xacro(source, _tool(tmp_path, "import sys; sys.exit(2)"))
    with pytest.raises(xacro_expand.XacroError, match="no <robot>"):
        xacro_expand.expand_xacro(source, _tool(tmp_path, "print('nothing here')"))
    with pytest.raises(xacro_expand.XacroError, match="did not finish"):
        xacro_expand.expand_xacro(source, _tool(tmp_path, "import time; time.sleep(5)"), timeout=0.3)
    with pytest.raises(xacro_expand.XacroError, match="could not be started"):
        xacro_expand.expand_xacro(source, [str(tmp_path / "no-such-tool")])
    monkeypatch.setattr(xacro_expand.shutil, "which", lambda name: None)
    with pytest.raises(xacro_expand.XacroError, match="not found"):
        xacro_expand.expand_xacro(source)


# ------------------------------------------------------------------------------------------------------------------------------ self collision
def _box_link(name: str, size: float = 1.0) -> Link:
    return Link(name, visuals=[Visual(geometry=BoxGeometry((size, size, size)))], inertial=Inertial(mass=1.0, ixx=0.1, iyy=0.1, izz=0.1))


def _chain(*offsets: float) -> Robot:
    """Boxes of one metre joined by fixed joints that move the next link by the given heights."""
    robot = Robot(name="chain")
    robot.links["l0"] = _box_link("l0")
    for index, height in enumerate(offsets, start=1):
        robot.links[f"l{index}"] = _box_link(f"l{index}")
        robot.joints[f"j{index}"] = Joint(f"j{index}", JointType.FIXED, f"l{index - 1}", f"l{index}", Origin((0.0, 0.0, height), (0, 0, 0)))
    return robot


def test_two_links_that_are_not_neighbours_and_overlap_are_found_at_home_with_the_depth_they_overlap_by():
    found = find_self_collisions(_chain(2.0, -2.0))  # l2 is back where l0 is
    assert [(c.link_a, c.link_b, c.joint) for c in found] == [("l0", "l2", None)] and found[0].depth == pytest.approx(1.0)
    lines = collision_warnings(found)
    assert len(lines) == 1 and "in the home pose" in lines[0] and "1000.0 mm" in lines[0]


def test_neighbours_that_touch_and_boxes_that_are_clear_are_not_collisions():
    assert find_self_collisions(_chain(1.0)) == []  # neighbours may touch
    assert find_self_collisions(_chain(2.0, 2.0)) == []
    assert find_self_collisions(_chain()) == []  # one link: nothing to collide with
    assert find_self_collisions(Robot()) == []


def test_a_joint_that_swings_a_link_into_another_is_named_with_the_value_that_does_it():
    robot = _chain(2.0, 2.0)
    robot.joints["j2"] = Joint("j2", JointType.PRISMATIC, "l1", "l2", Origin((0.0, 0.0, 2.0), (0, 0, 0)), (0.0, 0.0, 1.0), JointLimit(-4.0, 0.0, 1.0, 1.0))
    found = find_self_collisions(robot, steps=9)
    assert any(c.joint == "j2" and c.link_a == "l0" and c.link_b == "l2" and c.value is not None and c.value < -1.0 for c in found)
    assert all(c.joint is None or isinstance(c.value, float) for c in found)
    assert "when joint 'j2' is at" in collision_warnings([c for c in found if c.joint][:1])[0]


def test_a_tolerance_that_is_not_a_number_or_a_few_steps_fall_back_to_what_works():
    robot = _chain(2.0, -2.0)
    assert [(c.link_a, c.link_b) for c in find_self_collisions(robot, tolerance=float("nan"))] == [("l0", "l2")]
    assert [(c.link_a, c.link_b) for c in find_self_collisions(robot, tolerance=-1.0, steps=0)] == [("l0", "l2")]
    assert find_self_collisions(robot, tolerance=5.0) == []  # a tolerance larger than the overlap hides it
