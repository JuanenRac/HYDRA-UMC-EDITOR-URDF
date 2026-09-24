# =============================================================================
# HYDRA-UMC EDITOR-URDF - tests/test_dof.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Real unit tests for hydra_editor_urdf/urdf/dof.py - including explicit
# regression coverage for the negative-mass check already fixed in a
# prior audit pass (dof.py's own "BUG (found in audit)" comment), so a
# future edit can't silently regress it without a test failing.
# =============================================================================
from __future__ import annotations

from hydra_editor_urdf.models import Inertial, Joint, JointLimit, JointType, Link, Robot
from hydra_editor_urdf.urdf.dof import MAX_SUPPORTED_DOF, MIN_SUPPORTED_DOF, validate


def chain(n_movable_joints: int, joint_type: JointType = JointType.REVOLUTE, with_limits: bool = True) -> Robot:
    """A straight-line serial chain of `n_movable_joints` real joints,
    link0 -> link1 -> ... -> linkN, each with a real <limit> unless the
    caller is specifically testing the "missing limit" case."""
    links = {f"link{i}": Link(name=f"link{i}") for i in range(n_movable_joints + 1)}
    joints = {}
    for i in range(n_movable_joints):
        limit = JointLimit(lower=-1.0, upper=1.0, effort=10.0, velocity=1.0) if with_limits else None
        joints[f"j{i}"] = Joint(
            name=f"j{i}", type=joint_type, parent=f"link{i}", child=f"link{i + 1}", limit=limit
        )
    return Robot(name="r", links=links, joints=joints)


def test_feasible_chain_within_dof_range():
    robot = chain(4)
    report = validate(robot)
    assert report.is_feasible
    assert report.reasons == []
    assert report.dof_count == 4
    assert report.root_link_name == "link0"


def test_continuous_joint_needs_no_limit():
    robot = chain(3, joint_type=JointType.CONTINUOUS, with_limits=False)
    report = validate(robot)
    assert report.is_feasible


def test_below_min_dof_is_infeasible():
    robot = chain(MIN_SUPPORTED_DOF - 1)
    report = validate(robot)
    assert not report.is_feasible
    assert any("below" in r for r in report.reasons)


def test_at_min_dof_boundary_is_feasible():
    robot = chain(MIN_SUPPORTED_DOF)
    assert validate(robot).is_feasible


def test_at_max_dof_boundary_is_feasible():
    robot = chain(MAX_SUPPORTED_DOF)
    assert validate(robot).is_feasible


def test_above_max_dof_is_infeasible():
    robot = chain(MAX_SUPPORTED_DOF + 1)
    report = validate(robot)
    assert not report.is_feasible
    assert any("exceeds" in r for r in report.reasons)
    assert report.dof_count == MAX_SUPPORTED_DOF + 1


def test_fixed_joints_dont_count_toward_dof():
    robot = chain(4)
    robot.links["extra"] = Link(name="extra")
    robot.joints["jf"] = Joint(name="jf", type=JointType.FIXED, parent="link4", child="extra")
    report = validate(robot)
    assert report.dof_count == 4  # the FIXED joint adds no DOF
    assert report.is_feasible


# an inverted <limit> range (lower > upper) is physically
# meaningless - no real joint position exists between two bounds that
# don't overlap - but was never checked before.
def test_joint_limit_with_lower_greater_than_upper_is_flagged():
    robot = chain(3)
    robot.joints["j0"].limit = JointLimit(lower=1.0, upper=-1.0, effort=10.0, velocity=1.0)
    report = validate(robot)
    assert not report.is_feasible
    assert any("invalid <limit>" in reason for reason in report.reasons)


def test_revolute_or_prismatic_without_limit_is_flagged():
    robot = chain(3, with_limits=False)
    report = validate(robot)
    assert not report.is_feasible
    assert sum("has no <limit>" in r for r in report.reasons) == 3


def test_floating_or_planar_joint_is_unsupported_regardless_of_dof_count():
    robot = chain(4)
    robot.links["float_link"] = Link(name="float_link")
    robot.joints["jfloat"] = Joint(name="jfloat", type=JointType.FLOATING, parent="link4", child="float_link")
    report = validate(robot)
    assert not report.is_feasible
    assert "jfloat" in report.unsupported_joint_names
    assert any("FLOATING/PLANAR" in r for r in report.reasons)


def test_no_root_link_when_every_link_is_someone_elses_child():
    # A real cycle: a <- j0 <- b <- j1 <- a.
    robot = Robot(
        name="r",
        links={"a": Link(name="a"), "b": Link(name="b")},
        joints={
            "j0": Joint(name="j0", type=JointType.REVOLUTE, parent="b", child="a", limit=JointLimit(-1, 1)),
            "j1": Joint(name="j1", type=JointType.REVOLUTE, parent="a", child="b", limit=JointLimit(-1, 1)),
        },
    )
    report = validate(robot)
    assert report.root_link_name is None
    assert any("No root link found" in r for r in report.reasons)


def test_multiple_root_candidates_are_named_in_the_reason():
    robot = Robot(
        name="r",
        links={"base_a": Link(name="base_a"), "base_b": Link(name="base_b"), "tip": Link(name="tip")},
        joints={"j": Joint(name="j", type=JointType.FIXED, parent="base_a", child="tip")},
    )
    report = validate(robot)
    assert report.root_link_name is None
    assert any("candidate root links" in r for r in report.reasons)
    assert any("base_b" in r for r in report.reasons)


def test_disconnected_link_reachable_from_no_joint_chain_is_reported():
    # A genuinely disconnected sub-graph that resolves to a single root
    # candidate anyway needs BOTH of its own links to already be
    # someone's <child> (a 2-cycle) - a single isolated, unreferenced
    # link would instead become a second ROOT candidate itself (see
    # test_multiple_root_candidates_are_named_in_the_reason), not a
    # "disconnected" one; root_link_name() can only resolve to a single
    # link in the first place when there is exactly one such candidate.
    robot = chain(3)
    robot.links["x"] = Link(name="x")
    robot.links["y"] = Link(name="y")
    robot.joints["jx"] = Joint(name="jx", type=JointType.FIXED, parent="x", child="y")
    robot.joints["jy"] = Joint(name="jy", type=JointType.FIXED, parent="y", child="x")
    report = validate(robot)
    assert report.root_link_name == "link0"
    assert set(report.disconnected_link_names) == {"x", "y"}
    assert not report.is_feasible


def test_orphan_link_not_referenced_by_any_joint_is_reported_separately_from_disconnected():
    robot = chain(3)
    robot.links["unused"] = Link(name="unused")
    report = validate(robot)
    assert "unused" in report.orphan_link_names
    assert "unused" not in report.disconnected_link_names


# regression: a joint whose own parent/child names a link with no
# matching <link> element at all used to get a "viable" verdict -
# root_link_name()/_reachable_from() only ever walk names already in
# robot.links, so a fictitious child name was silently accepted into the
# "reachable" set instead of being flagged. Built on top of an otherwise
# perfectly feasible chain, to prove this specific check (not a knock-on
# effect of DOF count or missing limits) is what catches it.
def test_joint_referencing_a_nonexistent_link_is_flagged_not_viable():
    robot = chain(3)
    robot.joints["jghost"] = Joint(
        name="jghost", type=JointType.FIXED, parent="link3", child="ghost_link"
    )
    report = validate(robot)
    assert report.unknown_link_names == ["ghost_link"]
    assert not report.is_feasible
    assert any("ghost_link" in reason for reason in report.reasons)


def test_joint_with_a_nonexistent_parent_is_also_flagged():
    robot = chain(3)
    robot.joints["jghost"] = Joint(
        name="jghost", type=JointType.FIXED, parent="ghost_parent", child="link3"
    )
    report = validate(robot)
    assert report.unknown_link_names == ["ghost_parent"]
    assert not report.is_feasible


def test_multi_parent_link_is_flagged_as_invalid():
    robot = Robot(
        name="r",
        links={"base": Link(name="base"), "a": Link(name="a"), "shared": Link(name="shared")},
        joints={
            "j0": Joint(name="j0", type=JointType.REVOLUTE, parent="base", child="a", limit=JointLimit(-1, 1)),
            "j1": Joint(name="j1", type=JointType.REVOLUTE, parent="base", child="shared", limit=JointLimit(-1, 1)),
            "j2": Joint(name="j2", type=JointType.REVOLUTE, parent="a", child="shared", limit=JointLimit(-1, 1)),
        },
    )
    report = validate(robot)
    assert report.multi_parent_link_names == ["shared"]
    assert not report.is_feasible


def test_negative_mass_link_is_flagged_regression_for_prior_audit_fix():
    robot = chain(3)
    robot.links["link0"].inertial = Inertial(mass=-2.0)
    report = validate(robot)
    assert not report.is_feasible
    assert any("negative <inertial><mass>" in r for r in report.reasons)
    assert any("link0" in r for r in report.reasons)


def test_zero_or_positive_mass_is_never_flagged():
    robot = chain(3)
    robot.links["link0"].inertial = Inertial(mass=0.0)
    robot.links["link1"].inertial = Inertial(mass=1.5)
    report = validate(robot)
    assert not any("negative" in r for r in report.reasons)


def test_empty_robot_has_no_root_and_zero_dof():
    robot = Robot(name="r")
    report = validate(robot)
    assert report.dof_count == 0
    assert report.root_link_name is None
    assert not report.is_feasible
