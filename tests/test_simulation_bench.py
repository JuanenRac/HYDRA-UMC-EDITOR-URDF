# =============================================================================
# HYDRA-UMC-EDITOR-URDF - tests/test_simulation_bench.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Simulation bench: the real parser, writer, checks and kinematics against robots made by a generator with a fixed seed, and against robots damaged on purpose.

The robots are serial arms of random length with random joint types, axes, origins, limits, masses and shapes. The bench writes each one to URDF text and reads it back,
counts its degrees of freedom, poses it and compares the pose with a product of matrices that it computes itself, and runs the physical check on it. Then it damages
the robot in the ways files are damaged (a cycle, a link nobody declared, two parents, a mass of zero, limits the wrong way round, a mass in grams, a length in
millimetres, an inertia that cannot exist) and requires the check to name the rule. Nothing here says how the editor behaves with the models of real robots: that needs the models."""
from __future__ import annotations

import copy
import math
import random

import numpy as np
import pytest

from hydra_editor_urdf.models import (
    BoxGeometry,
    CylinderGeometry,
    Inertial,
    Joint,
    JointLimit,
    JointType,
    Link,
    Material,
    Origin,
    Robot,
    SphereGeometry,
    Visual,
)
from hydra_editor_urdf.render.kinematics import compute_link_world_transforms, default_joint_values
from hydra_editor_urdf.urdf.dof import validate
from hydra_editor_urdf.urdf.parser import UrdfParseError, parse_urdf_string
from hydra_editor_urdf.urdf.physical_check import check_robot
from hydra_editor_urdf.urdf.writer import robot_to_urdf_string

SEED = 20260101


def _shape(rng: random.Random):
    return rng.choice([
        BoxGeometry((rng.uniform(0.02, 0.3), rng.uniform(0.02, 0.3), rng.uniform(0.02, 0.5))),
        CylinderGeometry(rng.uniform(0.01, 0.1), rng.uniform(0.05, 0.5)),
        SphereGeometry(rng.uniform(0.02, 0.15)),
    ])


def _inertial(rng: random.Random) -> Inertial:
    mass = rng.uniform(0.2, 12.0)
    a, b = rng.uniform(0.001, 0.05), rng.uniform(0.001, 0.05)
    return Inertial(mass=mass, origin=Origin((0.0, 0.0, rng.uniform(0, 0.1)), (0.0, 0.0, 0.0)), ixx=a + b, iyy=a + 2 * b, izz=a + b)  # principal moments a+b, a+2b, a+b: a real body


def make_robot(rng: random.Random, joints: int, *, name: str = "arm") -> Robot:
    robot = Robot(name=name)
    robot.links["base"] = Link("base", visuals=[Visual(geometry=_shape(rng), material=Material("grey", (0.5, 0.5, 0.5, 1.0)))], inertial=_inertial(rng))
    parent = "base"
    for index in range(joints):
        child = f"link{index + 1}"
        robot.links[child] = Link(child, visuals=[Visual(origin=Origin((0, 0, rng.uniform(0, 0.2)), (0, 0, 0)), geometry=_shape(rng))], inertial=_inertial(rng))
        kind = rng.choice([JointType.REVOLUTE, JointType.REVOLUTE, JointType.CONTINUOUS, JointType.PRISMATIC, JointType.FIXED])
        limit = None
        if kind in (JointType.REVOLUTE, JointType.PRISMATIC):
            span = rng.uniform(0.3, 3.0) if kind is JointType.REVOLUTE else rng.uniform(0.05, 0.4)
            limit = JointLimit(lower=-span, upper=span, effort=rng.uniform(1, 100), velocity=rng.uniform(0.1, 5))
        elif kind is JointType.CONTINUOUS:
            limit = JointLimit(effort=rng.uniform(1, 100), velocity=rng.uniform(0.1, 5))
        axis = rng.choice([(1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (0.0, 0.6, 0.8)])
        origin = Origin((rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3), rng.uniform(0, 0.4)), (rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)))
        robot.joints[f"joint{index + 1}"] = Joint(f"joint{index + 1}", kind, parent, child, origin, axis, limit)
        parent = child
    return robot


def _fk(robot: Robot, values: dict[str, float]) -> dict[str, np.ndarray]:
    """The pose of every link of a serial arm, from the definition of the joints (not from the code under test)."""

    def rotation_xyz(r: float, p: float, y: float) -> np.ndarray:
        rx = np.array([[1, 0, 0], [0, math.cos(r), -math.sin(r)], [0, math.sin(r), math.cos(r)]])
        ry = np.array([[math.cos(p), 0, math.sin(p)], [0, 1, 0], [-math.sin(p), 0, math.cos(p)]])
        rz = np.array([[math.cos(y), -math.sin(y), 0], [math.sin(y), math.cos(y), 0], [0, 0, 1]])
        return rz @ ry @ rx

    def about(axis: tuple[float, float, float], angle: float) -> np.ndarray:
        a = np.array(axis) / np.linalg.norm(axis)
        k = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
        return np.eye(3) + math.sin(angle) * k + (1 - math.cos(angle)) * (k @ k)

    poses = {"base": np.eye(4)}
    for joint in robot.joints.values():
        local = np.eye(4)
        local[:3, :3] = rotation_xyz(*joint.origin.rpy)
        local[:3, 3] = joint.origin.xyz
        value = values.get(joint.name, 0.0)
        motion = np.eye(4)
        if joint.type in (JointType.REVOLUTE, JointType.CONTINUOUS):
            motion[:3, :3] = about(joint.axis, value)
        elif joint.type is JointType.PRISMATIC:
            motion[:3, 3] = np.array(joint.axis) / np.linalg.norm(joint.axis) * value
        poses[joint.child] = poses[joint.parent] @ local @ motion
    return poses


def test_every_generated_robot_is_written_and_read_back_as_the_same_robot() -> None:
    rng = random.Random(SEED)
    for run in range(40):
        robot = make_robot(rng, rng.randint(1, 9))
        text = robot_to_urdf_string(robot)
        again = parse_urdf_string(text)
        assert again.name == robot.name and list(again.links) == list(robot.links) and list(again.joints) == list(robot.joints), run
        for name, joint in robot.joints.items():
            other = again.joints[name]
            assert (other.type, other.parent, other.child) == (joint.type, joint.parent, joint.child)
            assert other.origin.xyz == pytest.approx(joint.origin.xyz, abs=1e-6) and other.origin.rpy == pytest.approx(joint.origin.rpy, abs=1e-6)
            assert other.axis == pytest.approx(joint.axis, abs=1e-6)
            if joint.limit is not None:
                assert other.limit is not None and other.limit.lower == pytest.approx(joint.limit.lower, abs=1e-6) and other.limit.effort == pytest.approx(joint.limit.effort, abs=1e-4)
        for name, link in robot.links.items():
            inertial = again.links[name].inertial
            assert inertial is not None and link.inertial is not None
            assert inertial.mass == pytest.approx(link.inertial.mass, abs=1e-6)
        assert robot_to_urdf_string(again) == text  # writing what was read changes nothing


def test_the_degrees_of_freedom_are_the_movable_joints_and_only_three_to_six_are_feasible() -> None:
    rng = random.Random(SEED + 1)
    for _ in range(40):
        robot = make_robot(rng, rng.randint(1, 9))
        movable = [j.name for j in robot.joints.values() if j.type in (JointType.REVOLUTE, JointType.CONTINUOUS, JointType.PRISMATIC)]
        report = validate(robot)
        assert report.dof_count == len(movable) and sorted(report.movable_joint_names) == sorted(movable)
        assert report.root_link_name == "base"
        assert (not report.is_feasible) == bool(report.reasons)
        assert report.is_feasible == (3 <= len(movable) <= 6)


def test_the_pose_of_every_link_is_the_product_of_the_joints_that_lead_to_it() -> None:
    rng = random.Random(SEED + 2)
    for _ in range(30):
        robot = make_robot(rng, rng.randint(1, 8))
        values = default_joint_values(robot)
        for name, joint in robot.joints.items():
            if joint.limit is not None and joint.type is not JointType.CONTINUOUS:
                values[name] = rng.uniform(joint.limit.lower, joint.limit.upper)
            elif joint.type is JointType.CONTINUOUS:
                values[name] = rng.uniform(-6, 6)
        poses = compute_link_world_transforms(robot, values)
        expected = _fk(robot, values)
        assert set(poses) == set(expected)
        for name in expected:
            assert np.allclose(poses[name], expected[name], atol=1e-9), name


def test_a_healthy_robot_has_no_physical_warning_and_the_same_robot_gives_the_same_findings() -> None:
    rng = random.Random(SEED + 3)
    for _ in range(25):
        robot = make_robot(rng, rng.randint(1, 8))
        assert check_robot(robot) == [], [w.rule for w in check_robot(robot)]
        assert check_robot(robot) == check_robot(robot)


def _rules(robot: Robot) -> set[str]:
    return {w.rule for w in check_robot(robot)}


def test_each_damage_to_a_robot_is_named_by_its_rule() -> None:
    rng = random.Random(SEED + 4)
    base = make_robot(rng, 5)
    for joint in base.joints.values():
        joint.type = JointType.REVOLUTE
        joint.limit = JointLimit(lower=-1.0, upper=1.0, effort=10.0, velocity=1.0)
        joint.axis = (0.0, 0.0, 1.0)
    moving = "joint2"

    def damaged(change) -> Robot:
        robot = copy.deepcopy(base)
        change(robot)
        return robot

    def inertia(**values):
        def change(robot: Robot) -> None:
            for key, value in values.items():
                setattr(robot.links["link1"].inertial, key, value)

        return change

    cases = {
        "mass_not_positive": damaged(inertia(mass=0.0)),
        "units_mass": damaged(inertia(mass=20000.0)),
        "inertia_not_finite": damaged(inertia(ixx=float("nan"))),
        "inertia_not_positive_definite": damaged(inertia(izz=-0.5)),
        "inertia_triangle": damaged(inertia(ixx=0.001, iyy=0.001, izz=0.5)),
        "limit_missing": damaged(lambda r: setattr(r.joints[moving], "limit", None)),
        "limit_inverted": damaged(lambda r: setattr(r.joints[moving], "limit", JointLimit(lower=1.0, upper=-1.0, effort=1, velocity=1))),
        "velocity_not_positive": damaged(lambda r: setattr(r.joints[moving].limit, "velocity", 0.0)),
        "effort_not_positive": damaged(lambda r: setattr(r.joints[moving].limit, "effort", -3.0)),
        "axis_zero": damaged(lambda r: setattr(r.joints[moving], "axis", (0.0, 0.0, 0.0))),
        "axis_not_unit": damaged(lambda r: setattr(r.joints[moving], "axis", (0.0, 3.0, 4.0))),
        "units_length": damaged(lambda r: setattr(r.joints[moving], "origin", Origin((5000.0, 0, 0), (0, 0, 0)))),
        "units_angle": damaged(lambda r: setattr(r.joints[moving], "limit", JointLimit(lower=-720.0, upper=720.0, effort=1, velocity=1))),
        "tree_unknown_link": damaged(lambda r: setattr(r.joints[moving], "child", "ghost")),
        "tree_orphan_link": damaged(lambda r: r.links.setdefault("stray", Link("stray"))),
        "tree_multiple_roots": damaged(lambda r: (r.links.setdefault("island", Link("island")), r.links.setdefault("island2", Link("island2")),
                                                  r.joints.setdefault("bridge", Joint("bridge", JointType.FIXED, "island", "island2")))),
    }
    for rule, robot in cases.items():
        assert rule in _rules(robot), (rule, _rules(robot))
    assert "tree_multiple_parents" in _rules(damaged(lambda r: r.joints.setdefault("extra", Joint("extra", JointType.FIXED, "base", "link3"))))
    assert _rules(damaged(lambda r: r.joints.setdefault("loop", Joint("loop", JointType.FIXED, "link5", "base")))) & {"tree_no_root", "tree_cycle", "tree_multiple_parents"}


def test_a_structure_that_is_not_a_tree_is_infeasible_and_the_pose_still_terminates() -> None:
    rng = random.Random(SEED + 5)
    robot = make_robot(rng, 4)
    robot.joints["back"] = Joint("back", JointType.REVOLUTE, "link4", "link2", Origin(), (0, 0, 1), JointLimit(-1, 1, 1, 1))
    report = validate(robot)
    assert not report.is_feasible and report.multi_parent_link_names == ["link2"]
    poses = compute_link_world_transforms(robot, default_joint_values(robot))
    assert "base" in poses and all(np.isfinite(m).all() for m in poses.values())


@pytest.mark.parametrize("text", [
    "", "   ", "not xml", "<robot>", "<robot/>", "<other/>", "<robot name='x'></robot>",
    '<?xml version="1.0"?><!DOCTYPE robot [<!ENTITY a "b">]><robot name="x"><link name="a"/></robot>',
    '<robot name="x"><link name="a"/><link name="a"/></robot>',
    '<robot name="x"><link name="a"/><joint name="j" type="fixed"><parent link="a"/><child link="b"/></joint><joint name="j" type="fixed"><parent link="a"/><child link="b"/></joint></robot>',
    '<robot name="x"><link name="a"/><joint name="j" type="warp"><parent link="a"/><child link="b"/></joint></robot>',
    '<robot xmlns:xacro="x" name="x"><xacro:macro name="m"/></robot>',
])
def test_text_that_is_not_a_robot_is_refused_with_the_parse_error_and_nothing_else(text: str) -> None:
    with pytest.raises(UrdfParseError):
        parse_urdf_string(text)


def test_damaged_text_never_raises_anything_but_the_parse_error() -> None:
    rng = random.Random(SEED + 6)
    text = robot_to_urdf_string(make_robot(rng, 4))
    outcomes = {"read": 0, "refused": 0}
    for _ in range(300):
        broken = list(text)
        for _ in range(rng.randint(1, 6)):
            position = rng.randrange(len(broken))
            broken[position] = rng.choice(["", "<", ">", "&", '"', "nan", "9e999", " ", "x"])
        try:
            robot = parse_urdf_string("".join(broken))
        except UrdfParseError:
            outcomes["refused"] += 1
            continue
        outcomes["read"] += 1
        assert robot.links  # whatever was read is a robot with at least one link
        validate(robot)
        check_robot(robot)
    assert outcomes["read"] + outcomes["refused"] == 300 and outcomes["refused"] > 0


def test_the_same_seed_makes_the_same_robots_and_another_seed_does_not() -> None:
    def fingerprint(seed: int) -> str:
        rng = random.Random(seed)
        return "".join(robot_to_urdf_string(make_robot(rng, 3)) for _ in range(3))

    assert fingerprint(SEED) == fingerprint(SEED) and fingerprint(SEED) != fingerprint(SEED + 1)
