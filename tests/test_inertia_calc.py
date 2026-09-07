# =============================================================================
# HYDRA-UMC EDITOR-URDF - tests/test_inertia_calc.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Real unit tests for hydra_editor_urdf/inertia_calc.py - checks the
# closed-form tensors against independently-computed textbook values, not
# just against the module's own formulas restated.
# =============================================================================
from __future__ import annotations

import math

import pytest

from hydra_editor_urdf.inertia_calc import (
    DEFAULT_DENSITY_KG_M3,
    box_volume,
    cylinder_volume,
    estimate_inertial,
    sphere_volume,
)
from hydra_editor_urdf.models import BoxGeometry, CylinderGeometry, MeshGeometry, SphereGeometry


def test_box_volume():
    assert box_volume((2.0, 3.0, 4.0)) == pytest.approx(24.0)


def test_cylinder_volume():
    assert cylinder_volume(radius=1.0, length=2.0) == pytest.approx(math.pi * 2.0)


def test_sphere_volume():
    assert sphere_volume(radius=1.0) == pytest.approx(4.0 / 3.0 * math.pi)


# --- box -------------------------------------------------------------------


def test_box_inertia_matches_textbook_formula_with_known_mass():
    size = (2.0, 3.0, 4.0)
    mass = 5.0
    estimate = estimate_inertial(BoxGeometry(size=size), known_mass=mass)
    a, b, c = size
    assert estimate.mass == pytest.approx(mass)
    assert estimate.ixx == pytest.approx(mass / 12.0 * (b * b + c * c))
    assert estimate.iyy == pytest.approx(mass / 12.0 * (a * a + c * c))
    assert estimate.izz == pytest.approx(mass / 12.0 * (a * a + b * b))
    assert estimate.ixy == 0.0 and estimate.ixz == 0.0 and estimate.iyz == 0.0
    assert estimate.mass_is_assumed is False
    assert estimate.is_mesh_approximation is False


def test_box_mass_defaults_to_volume_times_default_density_when_unknown():
    size = (1.0, 1.0, 1.0)
    estimate = estimate_inertial(BoxGeometry(size=size))
    assert estimate.mass == pytest.approx(box_volume(size) * DEFAULT_DENSITY_KG_M3)
    assert estimate.mass_is_assumed is True


def test_cube_has_equal_moments_about_all_three_axes():
    estimate = estimate_inertial(BoxGeometry(size=(2.0, 2.0, 2.0)), known_mass=6.0)
    assert estimate.ixx == pytest.approx(estimate.iyy)
    assert estimate.iyy == pytest.approx(estimate.izz)


# --- cylinder ----------------------------------------------------------


def test_cylinder_inertia_matches_textbook_formula():
    radius, length, mass = 0.5, 2.0, 3.0
    estimate = estimate_inertial(CylinderGeometry(radius=radius, length=length), known_mass=mass)
    expected_ixx_iyy = mass / 12.0 * (3.0 * radius * radius + length * length)
    expected_izz = mass / 2.0 * radius * radius
    assert estimate.ixx == pytest.approx(expected_ixx_iyy)
    assert estimate.iyy == pytest.approx(expected_ixx_iyy)
    assert estimate.izz == pytest.approx(expected_izz)


def test_cylinder_zz_is_the_symmetric_axis_and_differs_from_xx():
    estimate = estimate_inertial(CylinderGeometry(radius=1.0, length=1.0), known_mass=1.0)
    assert estimate.izz != pytest.approx(estimate.ixx)


# --- sphere --------------------------------------------------------------


def test_sphere_inertia_matches_textbook_formula_and_is_isotropic():
    radius, mass = 0.3, 2.0
    estimate = estimate_inertial(SphereGeometry(radius=radius), known_mass=mass)
    expected = (2.0 / 5.0) * mass * radius * radius
    assert estimate.ixx == pytest.approx(expected)
    assert estimate.iyy == pytest.approx(expected)
    assert estimate.izz == pytest.approx(expected)


# --- mesh (bounding-box approximation) --------------------------------------


def test_mesh_without_a_bbox_returns_none_rather_than_a_fabricated_shape():
    assert estimate_inertial(MeshGeometry(filename="m.stl")) is None


def test_mesh_with_a_bbox_is_treated_as_a_box_and_flagged_as_an_approximation():
    bbox = (1.0, 2.0, 3.0)
    estimate = estimate_inertial(MeshGeometry(filename="m.stl"), known_mass=4.0, mesh_bbox_size=bbox)
    a, b, c = bbox
    assert estimate.is_mesh_approximation is True
    assert estimate.ixx == pytest.approx(4.0 / 12.0 * (b * b + c * c))


# --- shared edge cases -------------------------------------------------


def test_zero_mass_estimate_is_none_not_a_zero_tensor():
    # A zero-volume box with no known_mass would otherwise divide-by-zero
    # its way to a spurious "valid" all-zero tensor - refused instead.
    estimate = estimate_inertial(BoxGeometry(size=(0.0, 1.0, 1.0)))
    assert estimate is None


def test_negative_known_mass_is_refused_not_silently_computed():
    estimate = estimate_inertial(BoxGeometry(size=(1.0, 1.0, 1.0)), known_mass=-5.0)
    assert estimate is None


def test_custom_density_is_honored_when_mass_is_unknown():
    size = (1.0, 1.0, 1.0)
    estimate = estimate_inertial(BoxGeometry(size=size), density_kg_m3=1000.0)
    assert estimate.mass == pytest.approx(1000.0)


def test_known_mass_overrides_density_based_guess():
    estimate = estimate_inertial(BoxGeometry(size=(1.0, 1.0, 1.0)), known_mass=42.0, density_kg_m3=1.0)
    assert estimate.mass == pytest.approx(42.0)
