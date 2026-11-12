# =============================================================================
# HYDRA-UMC EDITOR-URDF - render/gizmo.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The mathematics of the translation gizmo of the 3D view: three axes drawn at the frame of the selected link that
# the operator drags with the mouse to move the origin of the joint that carries the link. Rays, picking an axis,
# the distance a drag covers along an axis and the conversion of a world displacement to the frame of the parent
# link live here as plain numpy functions, so they are tested without a window or a GPU; render/viewport.py only
# feeds them the camera matrices and the mouse position.
# =============================================================================
from __future__ import annotations

import numpy as np

AXIS_DIRECTIONS = (
    np.array([1.0, 0.0, 0.0]),
    np.array([0.0, 1.0, 0.0]),
    np.array([0.0, 0.0, 1.0]),
)
AXIS_NAMES = ("x", "y", "z")
AXIS_COLORS = ((0.90, 0.20, 0.20, 1.0), (0.25, 0.80, 0.25, 1.0), (0.25, 0.45, 0.95, 1.0))
PARALLEL_LIMIT = 1e-6  # 1 - cos^2 of the angle between two lines below which they count as parallel


def pixel_ray(view: np.ndarray, projection: np.ndarray, x: float, y: float, width: int, height: int) -> tuple[np.ndarray, np.ndarray]:
    """The ray (origin, unit direction) in world space that goes through the pixel (x, y) of a viewport `width` x `height`
    (y grows downwards, as the mouse reports it). `view` and `projection` are the matrices the renderer draws with."""
    ndc_x = 2.0 * x / max(width, 1) - 1.0
    ndc_y = 1.0 - 2.0 * y / max(height, 1)
    inverse = np.linalg.inv(projection.astype(np.float64) @ view.astype(np.float64))
    near = inverse @ np.array([ndc_x, ndc_y, -1.0, 1.0])
    far = inverse @ np.array([ndc_x, ndc_y, 1.0, 1.0])
    near = near[:3] / near[3]
    far = far[:3] / far[3]
    direction = far - near
    return near, direction / np.linalg.norm(direction)


def closest_points(ray_origin: np.ndarray, ray_direction: np.ndarray, line_point: np.ndarray, line_direction: np.ndarray) -> tuple[float, float] | None:
    """Parameters (t on the ray, s on the line) of the two closest points of a ray and a line, or None when they are
    parallel. Both directions are unit vectors."""
    w0 = ray_origin - line_point
    b = float(np.dot(ray_direction, line_direction))
    d = float(np.dot(ray_direction, w0))
    e = float(np.dot(line_direction, w0))
    denominator = 1.0 - b * b
    if denominator < PARALLEL_LIMIT:
        return None
    t = (b * e - d) / denominator
    s = (e - b * d) / denominator
    return t, s


def pick_axis(
    ray_origin: np.ndarray,
    ray_direction: np.ndarray,
    gizmo_origin: np.ndarray,
    length: float,
    tolerance: float,
) -> int | None:
    """The index (0 x, 1 y, 2 z) of the axis of the gizmo the ray passes within `tolerance` of, the closest one when
    several are; None when it misses all three. Each axis is the segment from the origin to `length` along it."""
    best: tuple[float, int] | None = None
    for index, direction in enumerate(AXIS_DIRECTIONS):
        found = closest_points(ray_origin, ray_direction, gizmo_origin, direction)
        if found is None:
            continue
        t, s = found
        if t < 0.0 or s < -tolerance or s > length + tolerance:
            continue
        gap = float(np.linalg.norm((ray_origin + t * ray_direction) - (gizmo_origin + s * direction)))
        if gap <= tolerance and (best is None or gap < best[0]):
            best = (gap, index)
    return None if best is None else best[1]


def drag_distance(
    start_ray: tuple[np.ndarray, np.ndarray],
    current_ray: tuple[np.ndarray, np.ndarray],
    gizmo_origin: np.ndarray,
    axis: int,
) -> float | None:
    """How far, in meters along `axis`, the point the mouse drags has moved between two rays; None when a ray runs
    parallel to the axis (the position along it cannot be read from that view)."""
    direction = AXIS_DIRECTIONS[axis]
    start = closest_points(start_ray[0], start_ray[1], gizmo_origin, direction)
    current = closest_points(current_ray[0], current_ray[1], gizmo_origin, direction)
    if start is None or current is None:
        return None
    return current[1] - start[1]


def world_delta_to_parent(parent_transform: np.ndarray, axis: int, distance: float) -> np.ndarray:
    """A displacement of `distance` along the world axis, written in the frame of the parent link (the frame the
    <origin> of a joint is expressed in). `parent_transform` is the 4x4 (or 3x3) pose of the parent in the world."""
    world = AXIS_DIRECTIONS[axis] * distance
    return np.asarray(parent_transform, dtype=np.float64)[:3, :3].T @ world


def moved_origin(start_xyz: tuple[float, float, float], delta: np.ndarray, step: float = 0.0) -> tuple[float, float, float]:
    """The new xyz of a joint origin after a drag. With a `step` above zero (a snap to the grid), each coordinate is
    rounded to a multiple of it."""
    values = np.asarray(start_xyz, dtype=np.float64) + delta
    if step > 0.0:
        values = np.round(values / step) * step
    return (float(values[0]), float(values[1]), float(values[2]))
