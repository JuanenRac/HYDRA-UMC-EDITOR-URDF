# =============================================================================
# HYDRA-UMC EDITOR-URDF - tests/test_models.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Real unit tests for hydra_editor_urdf/models.py's own graph helpers
# (Robot.root_link_name/joints_by_parent/movable_joints) - the shared
# logic urdf/dof.py and render/kinematics.py both build on, tested here
# directly rather than only indirectly through those two callers.
# =============================================================================
from __future__ import annotations

from hydra_editor_urdf.models import Joint, JointType, Link, Robot


def test_root_link_name_single_root():
    robot = Robot(
        name="r",
        links={"base": Link(name="base"), "tip": Link(name="tip")},
        joints={"j": Joint(name="j", type=JointType.FIXED, parent="base", child="tip")},
    )
    assert robot.root_link_name() == "base"


def test_root_link_name_none_for_zero_links():
    assert Robot(name="r").root_link_name() is None


def test_root_link_name_none_when_every_link_is_a_child():
    robot = Robot(
        name="r",
        links={"a": Link(name="a"), "b": Link(name="b")},
        joints={
            "j0": Joint(name="j0", type=JointType.FIXED, parent="a", child="b"),
            "j1": Joint(name="j1", type=JointType.FIXED, parent="b", child="a"),
        },
    )
    assert robot.root_link_name() is None


def test_root_link_name_none_for_two_candidates():
    robot = Robot(
        name="r",
        links={"root_a": Link(name="root_a"), "root_b": Link(name="root_b"), "tip": Link(name="tip")},
        joints={"j": Joint(name="j", type=JointType.FIXED, parent="root_a", child="tip")},
    )
    assert robot.root_link_name() is None


def test_single_unconnected_link_is_its_own_root():
    robot = Robot(name="r", links={"solo": Link(name="solo")})
    assert robot.root_link_name() == "solo"


def test_joints_by_parent_groups_correctly():
    robot = Robot(
        name="r",
        links={"a": Link(name="a"), "b": Link(name="b"), "c": Link(name="c")},
        joints={
            "j0": Joint(name="j0", type=JointType.FIXED, parent="a", child="b"),
            "j1": Joint(name="j1", type=JointType.FIXED, parent="a", child="c"),
        },
    )
    by_parent = robot.joints_by_parent()
    assert {j.name for j in by_parent["a"]} == {"j0", "j1"}
    assert "b" not in by_parent  # b has no children of its own


def test_joints_by_parent_empty_robot():
    assert Robot(name="r").joints_by_parent() == {}


def test_movable_joints_excludes_fixed_floating_and_planar():
    robot = Robot(
        name="r",
        links={f"l{i}": Link(name=f"l{i}") for i in range(5)},
        joints={
            "rev": Joint(name="rev", type=JointType.REVOLUTE, parent="l0", child="l1"),
            "cont": Joint(name="cont", type=JointType.CONTINUOUS, parent="l1", child="l2"),
            "prism": Joint(name="prism", type=JointType.PRISMATIC, parent="l2", child="l3"),
            "fixed": Joint(name="fixed", type=JointType.FIXED, parent="l3", child="l4"),
        },
    )
    movable_names = {j.name for j in robot.movable_joints()}
    assert movable_names == {"rev", "cont", "prism"}


def test_joint_is_movable_property_matches_movable_joints():
    fixed = Joint(name="j", type=JointType.FIXED, parent="a", child="b")
    revolute = Joint(name="j2", type=JointType.REVOLUTE, parent="a", child="b")
    assert fixed.is_movable is False
    assert revolute.is_movable is True
