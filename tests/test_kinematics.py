# =============================================================================
# HYDRA-UMC EDITOR-URDF - tests/test_kinematics.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Real unit tests for hydra_editor_urdf/render/kinematics.py, including an
# explicit regression test for the infinite-loop-on-a-real-cycle bug
# already fixed in a prior audit pass (kinematics.py's own
# "BUG (found in audit)" comment on compute_link_world_transforms) -
# pytest's own timeout isn't configured in this repo, so the guard here
# is simply that the call returns at all rather than hanging the test run.
# =============================================================================
from __future__ import annotations

import math

import numpy as np
import pytest

from hydra_editor_urdf.models import Joint, JointType, Origin, Robot, Link
from hydra_editor_urdf.render.kinematics import (
    axis_rotation_matrix,
    compute_link_world_transforms,
    default_joint_values,
    joint_local_transform,
    origin_to_matrix,
    rpy_to_matrix,
)


def test_rpy_zero_is_identity():
    assert np.allclose(rpy_to_matrix((0.0, 0.0, 0.0)), np.eye(3))


def test_rpy_yaw_90deg_maps_x_to_y():
    r = rpy_to_matrix((0.0, 0.0, math.pi / 2))
    point = r @ np.array([1.0, 0.0, 0.0])
    assert np.allclose(point, [0.0, 1.0, 0.0], atol=1e-9)


def test_rpy_pitch_90deg_maps_x_to_negative_z():
    r = rpy_to_matrix((0.0, math.pi / 2, 0.0))
    point = r @ np.array([1.0, 0.0, 0.0])
    assert np.allclose(point, [0.0, 0.0, -1.0], atol=1e-9)


def test_rpy_roll_90deg_maps_y_to_z():
    r = rpy_to_matrix((math.pi / 2, 0.0, 0.0))
    point = r @ np.array([0.0, 1.0, 0.0])
    assert np.allclose(point, [0.0, 0.0, 1.0], atol=1e-9)


def test_origin_to_matrix_combines_rotation_and_translation():
    origin = Origin(xyz=(1.0, 2.0, 3.0), rpy=(0.0, 0.0, 0.0))
    m = origin_to_matrix(origin)
    assert np.allclose(m[:3, 3], [1.0, 2.0, 3.0])
    assert np.allclose(m[:3, :3], np.eye(3))


def test_axis_rotation_about_z_matches_rpy_yaw():
    angle = 0.7
    from_axis = axis_rotation_matrix((0.0, 0.0, 1.0), angle)
    from_rpy = rpy_to_matrix((0.0, 0.0, angle))
    assert np.allclose(from_axis, from_rpy, atol=1e-9)


def test_axis_rotation_normalizes_a_non_unit_axis():
    angle = math.pi / 3
    normalized = axis_rotation_matrix((0.0, 0.0, 1.0), angle)
    scaled = axis_rotation_matrix((0.0, 0.0, 5.0), angle)  # same direction, not unit length
    assert np.allclose(normalized, scaled, atol=1e-9)


def test_axis_rotation_zero_length_axis_is_identity_not_a_crash():
    r = axis_rotation_matrix((0.0, 0.0, 0.0), 1.23)
    assert np.allclose(r, np.eye(3))


def test_joint_local_transform_revolute_rotates_about_its_axis():
    joint = Joint(name="j", type=JointType.REVOLUTE, parent="a", child="b", axis=(0.0, 0.0, 1.0))
    m = joint_local_transform(joint, math.pi / 2)
    point = m[:3, :3] @ np.array([1.0, 0.0, 0.0])
    assert np.allclose(point, [0.0, 1.0, 0.0], atol=1e-9)


def test_joint_local_transform_prismatic_translates_along_its_axis():
    joint = Joint(name="j", type=JointType.PRISMATIC, parent="a", child="b", axis=(1.0, 0.0, 0.0))
    m = joint_local_transform(joint, 2.5)
    assert np.allclose(m[:3, 3], [2.5, 0.0, 0.0])
    assert np.allclose(m[:3, :3], np.eye(3))


def test_joint_local_transform_fixed_ignores_the_given_value():
    origin = Origin(xyz=(0.1, 0.2, 0.3))
    joint = Joint(name="j", type=JointType.FIXED, parent="a", child="b", origin=origin)
    m_at_zero = joint_local_transform(joint, 0.0)
    m_at_nonzero = joint_local_transform(joint, 99.0)
    assert np.allclose(m_at_zero, m_at_nonzero)
    assert np.allclose(m_at_zero[:3, 3], [0.1, 0.2, 0.3])


def test_joint_local_transform_prismatic_zero_length_axis_does_not_crash():
    joint = Joint(name="j", type=JointType.PRISMATIC, parent="a", child="b", axis=(0.0, 0.0, 0.0))
    m = joint_local_transform(joint, 5.0)
    assert np.allclose(m[:3, 3], [0.0, 0.0, 0.0])


# --- default_joint_values ----------------------------------------------


def test_default_joint_values_uses_limit_midpoint():
    from hydra_editor_urdf.models import JointLimit

    robot = Robot(
        name="r",
        links={"a": Link(name="a"), "b": Link(name="b")},
        joints={"j": Joint(name="j", type=JointType.REVOLUTE, parent="a", child="b", limit=JointLimit(lower=0.2, upper=1.8))},
    )
    values = default_joint_values(robot)
    assert values["j"] == pytest.approx(1.0)


def test_default_joint_values_continuous_joint_is_zero():
    robot = Robot(
        name="r",
        links={"a": Link(name="a"), "b": Link(name="b")},
        joints={"j": Joint(name="j", type=JointType.CONTINUOUS, parent="a", child="b")},
    )
    assert default_joint_values(robot)["j"] == 0.0


def test_default_joint_values_missing_limit_is_zero():
    robot = Robot(
        name="r",
        links={"a": Link(name="a"), "b": Link(name="b")},
        joints={"j": Joint(name="j", type=JointType.REVOLUTE, parent="a", child="b", limit=None)},
    )
    assert default_joint_values(robot)["j"] == 0.0


def test_default_joint_values_skips_fixed_joints():
    robot = Robot(
        name="r",
        links={"a": Link(name="a"), "b": Link(name="b")},
        joints={"j": Joint(name="j", type=JointType.FIXED, parent="a", child="b")},
    )
    assert default_joint_values(robot) == {}


# --- compute_link_world_transforms --------------------------------------


def straight_chain(n: int) -> Robot:
    links = {f"l{i}": Link(name=f"l{i}") for i in range(n + 1)}
    joints = {
        f"j{i}": Joint(
            name=f"j{i}", type=JointType.PRISMATIC, parent=f"l{i}", child=f"l{i + 1}", axis=(1.0, 0.0, 0.0)
        )
        for i in range(n)
    }
    return Robot(name="r", links=links, joints=joints)


def test_no_root_returns_empty_dict():
    robot = Robot(
        name="r",
        links={"a": Link(name="a"), "b": Link(name="b")},
        joints={
            "j0": Joint(name="j0", type=JointType.FIXED, parent="a", child="b"),
            "j1": Joint(name="j1", type=JointType.FIXED, parent="b", child="a"),
        },
    )
    assert compute_link_world_transforms(robot, {}) == {}


def test_root_link_gets_identity_transform():
    robot = straight_chain(2)
    world = compute_link_world_transforms(robot, {})
    assert np.allclose(world["l0"], np.eye(4))


def test_straight_chain_accumulates_translation():
    robot = straight_chain(3)
    values = {"j0": 1.0, "j1": 2.0, "j2": 3.0}
    world = compute_link_world_transforms(robot, values)
    assert np.allclose(world["l0"][:3, 3], [0.0, 0.0, 0.0])
    assert np.allclose(world["l1"][:3, 3], [1.0, 0.0, 0.0])
    assert np.allclose(world["l2"][:3, 3], [3.0, 0.0, 0.0])
    assert np.allclose(world["l3"][:3, 3], [6.0, 0.0, 0.0])


def test_missing_joint_value_defaults_to_zero():
    robot = straight_chain(1)
    world = compute_link_world_transforms(robot, {})  # no value given for j0 at all
    assert np.allclose(world["l1"][:3, 3], [0.0, 0.0, 0.0])


def test_fixed_joint_value_is_ignored_even_if_supplied():
    robot = Robot(
        name="r",
        links={"a": Link(name="a"), "b": Link(name="b")},
        joints={"j": Joint(name="j", type=JointType.FIXED, parent="a", child="b")},
    )
    world = compute_link_world_transforms(robot, {"j": 999.0})
    assert np.allclose(world["b"], np.eye(4))


def test_a_real_cycle_terminates_instead_of_hanging_regression_for_prior_audit_fix():
    # root -> A -> B via j1, then B -> C via j2, then C -> B via j3
    # closing the loop - the exact repro dof.py's own module doc
    # documents as having hung this function past a 3s watchdog before
    # the `joint.child not in world` guard was added.
    robot = Robot(
        name="r",
        links={"root": Link(name="root"), "a": Link(name="a"), "b": Link(name="b"), "c": Link(name="c")},
        joints={
            "j1": Joint(name="j1", type=JointType.FIXED, parent="root", child="a"),
            "j2": Joint(name="j2", type=JointType.FIXED, parent="a", child="b"),
            "j3": Joint(name="j3", type=JointType.FIXED, parent="b", child="c"),
            "j4": Joint(name="j4", type=JointType.FIXED, parent="c", child="b"),  # closes the cycle b<->c
        },
    )
    world = compute_link_world_transforms(robot, {})
    # Terminates (this call returning at all is the actual regression
    # guard) and visits every link reachable from the root at least once -
    # "c" is only ever reached as j3's target, never re-scheduled by j4
    # since "b" is already in `world` by then.
    assert set(world) == {"root", "a", "b", "c"}


def test_diamond_reconvergence_keeps_first_processed_writer():
    # root has two joints both landing on the same child link "tip" -
    # dof.py's own DofReport.multi_parent_link_names would flag this as
    # infeasible, but this function must still terminate and produce SOME
    # deterministic pose rather than crash, same as the cycle case above.
    robot = Robot(
        name="r",
        links={"root": Link(name="root"), "tip": Link(name="tip")},
        joints={
            "j1": Joint(name="j1", type=JointType.FIXED, parent="root", child="tip", origin=Origin(xyz=(1.0, 0.0, 0.0))),
            "j2": Joint(name="j2", type=JointType.FIXED, parent="root", child="tip", origin=Origin(xyz=(2.0, 0.0, 0.0))),
        },
    )
    world = compute_link_world_transforms(robot, {})
    # j1 is inserted (and therefore processed) first, so it wins - pinned
    # exactly, not just "one of the two", since joints_by_parent()
    # preserves Robot.joints' own insertion order and that determinism is
    # the whole point of this being a regression test.
    assert world["tip"][0, 3] == pytest.approx(1.0)
