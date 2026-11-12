# =============================================================================
# HYDRA-UMC EDITOR-URDF - tests/test_gizmo.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The mathematics of the translation gizmo: rays through a pixel, picking an axis, the distance of a drag and the
# conversion to the frame of the parent link. No window or GPU needed besides importing the camera helpers.
# =============================================================================
from __future__ import annotations

import numpy as np
import pytest

from hydra_editor_urdf.render import gizmo
from hydra_editor_urdf.render.camera import look_at, perspective

EYE = np.array([3.0, 0.0, 0.0], dtype=np.float32)
VIEW = look_at(EYE, np.zeros(3, dtype=np.float32), np.array([0.0, 0.0, 1.0], dtype=np.float32))
PROJECTION = perspective(45.0, 1.0, 0.01, 50.0)
SIZE = 400


def _ray_at(x: float, y: float):
    return gizmo.pixel_ray(VIEW, PROJECTION, x, y, SIZE, SIZE)


def _pixel_of(point) -> tuple[float, float]:
    clip = PROJECTION.astype(np.float64) @ VIEW.astype(np.float64) @ np.array([*point, 1.0])
    ndc = clip[:3] / clip[3]
    return (ndc[0] + 1.0) * SIZE / 2, (1.0 - ndc[1]) * SIZE / 2


def test_the_centre_pixel_looks_at_the_target() -> None:
    origin, direction = _ray_at(SIZE / 2, SIZE / 2)

    assert np.linalg.norm(direction) == pytest.approx(1.0)
    assert direction == pytest.approx(np.array([-1.0, 0.0, 0.0]), abs=1e-5)
    assert origin[0] < 3.0


def test_pixels_either_side_of_the_centre_look_to_opposite_sides() -> None:
    _, left = _ray_at(100, SIZE / 2)
    _, right = _ray_at(300, SIZE / 2)

    assert left[1] != pytest.approx(right[1])
    assert left[1] == pytest.approx(-right[1], abs=1e-6)


def test_the_axis_under_the_cursor_is_picked() -> None:
    px, py = _pixel_of((0.0, 0.0, 0.25))
    origin, direction = _ray_at(px, py)
    assert gizmo.pick_axis(origin, direction, np.zeros(3), 0.5, 0.02) == 2

    px, py = _pixel_of((0.0, 0.3, 0.0))
    origin, direction = _ray_at(px, py)
    assert gizmo.pick_axis(origin, direction, np.zeros(3), 0.5, 0.02) == 1


def test_a_ray_far_from_every_axis_picks_nothing() -> None:
    origin, direction = _ray_at(10, 10)
    assert gizmo.pick_axis(origin, direction, np.zeros(3), 0.5, 0.02) is None


def test_an_axis_past_its_end_or_behind_the_ray_is_not_picked() -> None:
    down = np.array([0.0, -1.0, 0.0])
    start = np.array([0.0, 5.0, 0.0])
    assert gizmo.pick_axis(start + np.array([0.9, 0.0, 0.0]), down, np.zeros(3), 0.5, 0.01) is None  # crosses X at 0.9, the axis ends at 0.5
    assert gizmo.pick_axis(start + np.array([0.3, 0.0, 0.0]), down, np.zeros(3), 0.5, 0.01) == 0
    assert gizmo.pick_axis(start + np.array([0.3, 0.0, 0.0]), -down, np.zeros(3), 0.5, 0.01) is None  # the crossing is behind the ray


def test_the_nearest_of_two_axes_wins() -> None:
    # Looking straight down from above: 0.02 from the Y axis, 0.3 from the X axis.
    picked = gizmo.pick_axis(np.array([0.02, 0.3, 5.0]), np.array([0.0, 0.0, -1.0]), np.zeros(3), 1.0, 0.5)
    assert picked == 1


def test_a_drag_along_the_axis_measures_the_displacement() -> None:
    start = _ray_at(*_pixel_of((0.0, 0.0, 0.0)))
    end = _ray_at(*_pixel_of((0.0, 0.4, 0.0)))

    assert gizmo.drag_distance(start, end, np.zeros(3), 1) == pytest.approx(0.4, abs=1e-4)
    assert gizmo.drag_distance(end, start, np.zeros(3), 1) == pytest.approx(-0.4, abs=1e-4)


def test_a_view_along_the_axis_cannot_drag_it() -> None:
    along_x = _ray_at(SIZE / 2, SIZE / 2)
    assert gizmo.drag_distance(along_x, along_x, np.zeros(3), 0) is None


def test_parallel_lines_have_no_closest_points() -> None:
    x_axis = np.array([1.0, 0.0, 0.0])
    assert gizmo.closest_points(np.array([0.0, 1.0, 0.0]), x_axis, np.zeros(3), x_axis) is None


def test_a_world_displacement_is_written_in_the_frame_of_the_parent() -> None:
    rotate_z_90 = np.array([[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])
    # The x axis of the parent points along world y: 1 m along world x is 1 m along the -y of the parent.
    assert gizmo.world_delta_to_parent(rotate_z_90, 0, 1.0) == pytest.approx(np.array([0.0, -1.0, 0.0]), abs=1e-12)
    assert gizmo.world_delta_to_parent(np.eye(4), 2, -0.5) == pytest.approx(np.array([0.0, 0.0, -0.5]))


def test_the_new_origin_adds_the_delta_and_can_snap_to_a_grid() -> None:
    assert gizmo.moved_origin((0.1, 0.2, 0.3), np.array([0.1, 0.0, -0.1])) == pytest.approx((0.2, 0.2, 0.2))
    assert gizmo.moved_origin((0.0, 0.0, 0.0), np.array([0.0123, 0.0, 0.0]), step=0.005) == pytest.approx((0.01, 0.0, 0.0))
