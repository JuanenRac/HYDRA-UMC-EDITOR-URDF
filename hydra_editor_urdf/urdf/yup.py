# =============================================================================
# HYDRA-UMC EDITOR-URDF - urdf/yup.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The same robot in the Y-up convention of a Three.js scene instead of the Z-up one of URDF.

A new root link is put above the old root with a fixed joint that turns the world a quarter turn about X, so a point
(x, y, z) of the URDF world is (x, z, -y) in the Y-up one. Everything below the old root is untouched; an optional scale
(meters to the unit of the scene) is applied to every length of the model.
"""

from __future__ import annotations

import copy
import math

from hydra_editor_urdf.models import (
    BoxGeometry,
    CylinderGeometry,
    Joint,
    JointType,
    Link,
    MeshGeometry,
    Origin,
    Robot,
    SphereGeometry,
)


def _scaled_origin(origin: Origin, s: float) -> Origin:
    return Origin(xyz=(origin.xyz[0] * s, origin.xyz[1] * s, origin.xyz[2] * s), rpy=origin.rpy)


def _scale_geometry(geometry, s: float) -> None:
    if isinstance(geometry, BoxGeometry):
        geometry.size = tuple(d * s for d in geometry.size)  # type: ignore[assignment]
    elif isinstance(geometry, CylinderGeometry):
        geometry.radius *= s
        geometry.length *= s
    elif isinstance(geometry, SphereGeometry):
        geometry.radius *= s
    elif isinstance(geometry, MeshGeometry):
        geometry.scale = tuple(c * s for c in geometry.scale)  # type: ignore[assignment]


def scale_robot(robot: Robot, s: float) -> Robot:
    """A copy of `robot` with every length multiplied by `s` (the mass stays, the inertia follows the square of the length)."""
    if not math.isfinite(s) or s <= 0:
        raise ValueError(f"the scale must be a positive number, got {s!r}")
    out = copy.deepcopy(robot)
    for link in out.links.values():
        for shape in [*link.visuals, *link.collisions]:
            shape.origin = _scaled_origin(shape.origin, s)
            _scale_geometry(shape.geometry, s)
        inertial = link.inertial
        if inertial is not None:
            inertial.origin = _scaled_origin(inertial.origin, s)
            for name in ("ixx", "ixy", "ixz", "iyy", "iyz", "izz"):
                setattr(inertial, name, getattr(inertial, name) * s * s)
    for joint in out.joints.values():
        joint.origin = _scaled_origin(joint.origin, s)
        if joint.type == JointType.PRISMATIC and joint.limit is not None:
            joint.limit.lower *= s
            joint.limit.upper *= s
    return out


def to_y_up(robot: Robot, scale: float = 1.0) -> Robot:
    """The robot in Y-up (and scaled by `scale`). Raises ValueError for a robot without a single root link."""
    root = robot.root_link_name()
    if root is None:
        raise ValueError("the robot has no single root link, so it cannot be turned to Y-up")
    out = scale_robot(robot, scale) if scale != 1.0 else copy.deepcopy(robot)
    base = "world_y_up"
    while base in out.links:
        base += "_"
    new_links = {base: Link(name=base)}
    new_links.update(out.links)
    out.links = new_links
    joint_name = f"{base}_joint"
    while joint_name in out.joints:
        joint_name += "_"
    turn = Joint(name=joint_name, type=JointType.FIXED, parent=base, child=root, origin=Origin(rpy=(-math.pi / 2.0, 0.0, 0.0)))
    out.joints = {joint_name: turn, **out.joints}
    return out
