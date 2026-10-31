# =============================================================================
# HYDRA-UMC EDITOR-URDF - urdf/self_collision.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Self-collision hints: links whose boxes overlap in the home pose or at some point of a jog.

Each link is boxed in the world with an axis-aligned box that contains its collision geometry (its visual geometry when it
has no collision), so the check over-reports a little and never misses an overlap of the real shapes. Two links joined by
a joint touch by design and are not compared. The result is a list of warnings, never a refusal to save.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np

from hydra_editor_urdf.models import BoxGeometry, CylinderGeometry, MeshGeometry, Robot, SphereGeometry
from hydra_editor_urdf.render.kinematics import compute_link_world_transforms, default_joint_values, jog_range, origin_to_matrix

DEFAULT_TOLERANCE = 0.001  # meters of overlap below which two boxes are taken as touching
DEFAULT_STEPS = 9


@dataclass(frozen=True)
class SelfCollision:
    link_a: str
    link_b: str
    depth: float  # meters the boxes overlap by (the smallest axis)
    joint: str | None  # None: the home pose; otherwise the joint that was jogged to reach it
    value: float | None


def _local_corners(geometry: object, resolver: Callable[[str], "Path | None"] | None) -> np.ndarray | None:
    if isinstance(geometry, BoxGeometry):
        half = np.array(geometry.size, dtype=float) / 2.0
    elif isinstance(geometry, CylinderGeometry):
        half = np.array([geometry.radius, geometry.radius, geometry.length / 2.0], dtype=float)
    elif isinstance(geometry, SphereGeometry):
        half = np.full(3, float(geometry.radius))
    elif isinstance(geometry, MeshGeometry):
        path = resolver(geometry.filename) if resolver is not None else None
        if path is None:
            return None
        from hydra_editor_urdf.render.mesh import load_mesh_file

        try:
            vertices = np.asarray(load_mesh_file(path).vertices, dtype=float)
        except Exception:  # an unreadable mesh is reported elsewhere; it only has no box here
            return None
        if len(vertices) == 0:
            return None
        scale = np.array(geometry.scale, dtype=float)
        lo, hi = vertices.min(axis=0) * scale, vertices.max(axis=0) * scale
        lo, hi = np.minimum(lo, hi), np.maximum(lo, hi)
        return np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
    else:
        return None
    if not np.all(np.isfinite(half)):
        return None
    return np.array([[sx * half[0], sy * half[1], sz * half[2]] for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)])


def link_local_boxes(robot: Robot, resolver: Callable[[str], "Path | None"] | None = None) -> dict[str, np.ndarray]:
    """For each link that has geometry, the corners (N, 3) of its geometry in the frame of the link."""
    result: dict[str, np.ndarray] = {}
    for name, link in robot.links.items():
        shapes = link.collisions or link.visuals
        pieces = []
        for shape in shapes:
            corners = _local_corners(shape.geometry, resolver)
            if corners is None:
                continue
            matrix = origin_to_matrix(shape.origin)
            pieces.append(corners @ matrix[:3, :3].T + matrix[:3, 3])
        if pieces:
            result[name] = np.vstack(pieces)
    return result


def _world_boxes(local: dict[str, np.ndarray], world: dict[str, np.ndarray]) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    boxes = {}
    for name, corners in local.items():
        matrix = world.get(name)
        if matrix is None:
            continue
        points = corners @ matrix[:3, :3].T + matrix[:3, 3]
        boxes[name] = (points.min(axis=0), points.max(axis=0))
    return boxes


def _overlap(a: tuple[np.ndarray, np.ndarray], b: tuple[np.ndarray, np.ndarray]) -> float:
    """The smallest overlap of the two boxes over the three axes (negative when they are apart on some axis)."""
    return float(np.min(np.minimum(a[1], b[1]) - np.maximum(a[0], b[0])))


def _adjacent_pairs(robot: Robot) -> set[frozenset[str]]:
    return {frozenset((j.parent, j.child)) for j in robot.joints.values()}


def _colliding(robot: Robot, local, values: dict[str, float], tolerance: float, adjacent: set[frozenset[str]]) -> dict[frozenset[str], float]:
    boxes = _world_boxes(local, compute_link_world_transforms(robot, values))
    found: dict[frozenset[str], float] = {}
    for a, b in itertools.combinations(sorted(boxes), 2):
        pair = frozenset((a, b))
        if pair in adjacent:
            continue
        depth = _overlap(boxes[a], boxes[b])
        if depth > tolerance:
            found[pair] = depth
    return found


def find_self_collisions(
    robot: Robot,
    resolver: Callable[[str], "Path | None"] | None = None,
    steps: int = DEFAULT_STEPS,
    tolerance: float = DEFAULT_TOLERANCE,
) -> list[SelfCollision]:
    """The pairs of links that overlap at the home pose (the middle of every range), and those that first overlap while one
    joint at a time is jogged over its whole range in `steps` steps with the others at home. One entry per pair."""
    if not math.isfinite(tolerance) or tolerance < 0:
        tolerance = DEFAULT_TOLERANCE
    steps = max(2, int(steps))
    local = link_local_boxes(robot, resolver)
    if len(local) < 2:
        return []
    adjacent = _adjacent_pairs(robot)
    home = default_joint_values(robot)
    result: list[SelfCollision] = []
    seen: set[frozenset[str]] = set()
    for pair, depth in _colliding(robot, local, home, tolerance, adjacent).items():
        a, b = sorted(pair)
        result.append(SelfCollision(a, b, depth, None, None))
        seen.add(pair)
    for joint in robot.movable_joints():
        lower, upper = jog_range(joint)
        for index in range(steps):
            value = lower + (upper - lower) * index / (steps - 1)
            values = dict(home)
            values[joint.name] = value
            for pair, depth in _colliding(robot, local, values, tolerance, adjacent).items():
                if pair in seen:
                    continue
                seen.add(pair)
                a, b = sorted(pair)
                result.append(SelfCollision(a, b, depth, joint.name, value))
    return sorted(result, key=lambda c: (c.joint is not None, c.link_a, c.link_b))


def collision_warnings(collisions: list[SelfCollision]) -> list[str]:
    lines = []
    for c in collisions:
        where = "in the home pose" if c.joint is None else f"when joint {c.joint!r} is at {c.value:.3g}"
        lines.append(f"Links {c.link_a!r} and {c.link_b!r} may collide {where} (their boxes overlap by {c.depth * 1000:.1f} mm).")
    return lines
