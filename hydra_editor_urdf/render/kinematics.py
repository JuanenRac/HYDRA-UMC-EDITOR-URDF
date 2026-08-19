# =============================================================================
# HYDRA-UMC EDITOR-URDF - render/kinematics.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Generic forward kinematics over WHATEVER tree urdf/parser.py produced -
# unlike HYDRA-UMC-SUITE's own render/kinematics.py (a fixed registry of
# a few dozen KNOWN robot models, each with hand-verified chain math),
# this app has to pose an arbitrary, previously-unseen URDF the operator
# just imported, so it walks the actual parent/child joint graph and the
# actual per-joint <origin>/<axis> instead of a per-model lookup table.
# Standard URDF convention throughout: right-handed, Z-up per LINK's own
# local frame (world orientation is whatever the root link's own meshes
# were authored in - this app doesn't re-orient a URDF into Y-up the way
# HYDRA-UMC-STUDIO's Three.js scene does, since a straight re-export of
# an edited URDF should stay in the coordinate convention URDF itself
# defines, not a viewer-specific one).
# =============================================================================
from __future__ import annotations

import numpy as np

from hydra_editor_urdf.models import Joint, JointType, Origin, Robot


def rpy_to_matrix(rpy: tuple[float, float, float]) -> np.ndarray:
    """URDF's own fixed-axis convention: R = Rz(yaw) * Ry(pitch) * Rx(roll)
    (http://wiki.ros.org/urdf/XML/joint, <origin rpy="roll pitch yaw">)."""
    roll, pitch, yaw = rpy
    cr, sr = np.cos(roll), np.sin(roll)
    cp, sp = np.cos(pitch), np.sin(pitch)
    cy, sy = np.cos(yaw), np.sin(yaw)
    rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]], dtype=np.float64)
    ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]], dtype=np.float64)
    rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]], dtype=np.float64)
    return rz @ ry @ rx


def origin_to_matrix(origin: Origin) -> np.ndarray:
    m = np.eye(4, dtype=np.float64)
    m[:3, :3] = rpy_to_matrix(origin.rpy)
    m[:3, 3] = origin.xyz
    return m


def axis_rotation_matrix(axis: tuple[float, float, float], angle_rad: float) -> np.ndarray:
    """Rodrigues' rotation formula about an arbitrary (normalized) axis -
    a revolute/continuous joint's own <axis xyz="..."/> is rarely a plain
    cardinal direction in a real-world URDF, so this can't shortcut to a
    simple Rx/Ry/Rz like rpy_to_matrix above does for the origin."""
    ax = np.array(axis, dtype=np.float64)
    length = np.linalg.norm(ax)
    if length < 1e-12:
        return np.eye(3, dtype=np.float64)
    ax = ax / length
    x, y, z = ax
    c, s = np.cos(angle_rad), np.sin(angle_rad)
    t = 1.0 - c
    return np.array([
        [t * x * x + c, t * x * y - s * z, t * x * z + s * y],
        [t * x * y + s * z, t * y * y + c, t * y * z - s * x],
        [t * x * z - s * y, t * y * z + s * x, t * z * z + c],
    ], dtype=np.float64)


def joint_local_transform(joint: Joint, value: float) -> np.ndarray:
    """The joint's own contribution to its child link's world transform,
    ALREADY composed with <origin> - i.e. this is what the parent link's
    world transform gets right-multiplied by to reach the child link's
    world transform directly (see compute_link_world_transforms)."""
    m = origin_to_matrix(joint.origin)
    if joint.type in (JointType.REVOLUTE, JointType.CONTINUOUS):
        rot = np.eye(4, dtype=np.float64)
        rot[:3, :3] = axis_rotation_matrix(joint.axis, value)
        return m @ rot
    if joint.type == JointType.PRISMATIC:
        ax = np.array(joint.axis, dtype=np.float64)
        length = np.linalg.norm(ax)
        ax = ax / length if length > 1e-12 else ax
        translate = np.eye(4, dtype=np.float64)
        translate[:3, 3] = ax * value
        return m @ translate
    # FIXED (and FLOATING/PLANAR, which urdf/dof.py already flags as
    # unsupported before this is ever reached for a real pose) - no
    # additional motion beyond the static <origin> itself.
    return m


def default_joint_values(robot: Robot) -> dict[str, float]:
    """A sensible starting pose for a freshly-imported URDF: the midpoint
    of each REVOLUTE/PRISMATIC joint's own <limit>, 0.0 for CONTINUOUS
    (which has none) - not always "home" in whatever sense the original
    robot's own firmware defines, but a defensible, in-range default the
    viewport can show immediately without the operator having to jog
    every joint away from an all-zeros pose that may itself be out of
    range (a common real-world case: a joint whose limit is e.g.
    [0.2, 1.8] rad, where 0.0 is actually unreachable)."""
    values: dict[str, float] = {}
    for joint in robot.movable_joints():
        if joint.type == JointType.CONTINUOUS or joint.limit is None:
            values[joint.name] = 0.0
        else:
            values[joint.name] = (joint.limit.lower + joint.limit.upper) / 2.0
    return values


def compute_link_world_transforms(robot: Robot, joint_values: dict[str, float]) -> dict[str, np.ndarray]:
    """One 4x4 world transform per link, keyed by link name - walks the
    tree breadth-first from Robot.root_link_name() outward. Returns an
    empty dict if the robot has no valid single root (caller should have
    already run urdf/dof.py's validate() and refused to render/export a
    tree that failed that check, same as it refuses to upload one)."""
    root = robot.root_link_name()
    if root is None:
        return {}

    world: dict[str, np.ndarray] = {root: np.eye(4, dtype=np.float64)}
    by_parent = robot.joints_by_parent()
    frontier = [root]
    while frontier:
        current = frontier.pop()
        parent_world = world[current]
        for joint in by_parent.get(current, []):
            value = joint_values.get(joint.name, 0.0) if joint.is_movable else 0.0
            child_world = parent_world @ joint_local_transform(joint, value)
            world[joint.child] = child_world
            frontier.append(joint.child)
    return world
