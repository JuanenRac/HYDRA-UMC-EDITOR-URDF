# =============================================================================
# HYDRA-UMC EDITOR-URDF - inertia_calc.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Real, closed-form moment-of-inertia formulas for the 3 primitive
# geometries URDF (and this app's own models.py) knows about - the
# textbook uniform-density solid-body tensors, not a guess. MeshGeometry
# has no such closed form (it's an arbitrary triangle soup); the
# reasonable approximation there is the mesh's own AXIS-ALIGNED BOUNDING
# BOX treated as a solid box, which is exactly what the audit's own idea
# asked for ("aproximado, por geometría de la malla/primitiva"). This is
# explicitly an approximation, not a real per-mesh
# integral (that would need signed-tetrahedron volume integration over
# every triangle, a meaningfully bigger feature) - every function below
# that returns a Mesh-derived result says so in its own docstring, and
# the properties panel wiring surfaces that same caveat to the operator
# rather than presenting it as an exact figure.
#
# Every supported shape here is computed about its own principal axes by
# construction (a Box/Cylinder/Sphere centered at its own local origin
# has zero products of inertia along X/Y/Z) - so ixy/ixz/iyz are always
# 0.0 in the returned tensor. That's the honest answer for these shapes,
# not a shortcut: a URDF <inertial> element's own <origin> is expected to
# already place the inertial frame at the link's true center of mass with
# axes aligned to its own principal axes, which is exactly what "centered
# box/cylinder/sphere, no origin offset" means here.
#
# Units: meters and kilograms throughout, matching the URDF spec and
# every other geometry field in models.py (BoxGeometry(1.0, 1.0, 1.0) is
# a 1-meter cube, not 1mm - see that class's own field defaults).
# =============================================================================
from __future__ import annotations

import math
from dataclasses import dataclass

from hydra_editor_urdf.models import BoxGeometry, CylinderGeometry, Geometry, MeshGeometry, SphereGeometry

# A generic aluminum-alloy density - the ecosystem's own real robot links
# (HYDRA-UMC's own Robot Controller Board enclosure, most of the sample
# robots this app ships with) are machined/printed aluminum or a
# comparably dense engineering plastic, so this is a defensible default
# for "the operator hasn't told us the real material yet" rather than an
# arbitrary round number. Always just a STARTING point - see
# InertialEstimate.mass_is_assumed below, which the UI uses to label the
# mass field as an assumption rather than a measured value whenever this
# default was the one actually used.
DEFAULT_DENSITY_KG_M3 = 2700.0


@dataclass(frozen=True)
class InertialEstimate:
    mass: float
    ixx: float
    iyy: float
    izz: float
    ixy: float = 0.0
    ixz: float = 0.0
    iyz: float = 0.0
    mass_is_assumed: bool = False  # True when `mass` came from volume x DEFAULT_DENSITY_KG_M3, not an operator-supplied value
    is_mesh_approximation: bool = False  # True when the source shape was a Mesh (bounding-box approximation, not exact)


def box_volume(size: tuple[float, float, float]) -> float:
    a, b, c = size
    return a * b * c


def cylinder_volume(radius: float, length: float) -> float:
    return math.pi * radius * radius * length


def sphere_volume(radius: float) -> float:
    return (4.0 / 3.0) * math.pi * radius**3


def _box_inertia(mass: float, size: tuple[float, float, float]) -> tuple[float, float, float]:
    a, b, c = size
    ixx = mass / 12.0 * (b * b + c * c)
    iyy = mass / 12.0 * (a * a + c * c)
    izz = mass / 12.0 * (a * a + b * b)
    return ixx, iyy, izz


def _cylinder_inertia(mass: float, radius: float, length: float) -> tuple[float, float, float]:
    # Axis along local Z, matching URDF's own <cylinder> convention (the
    # geometry is defined along its origin frame's Z axis).
    ixx = iyy = mass / 12.0 * (3.0 * radius * radius + length * length)
    izz = mass / 2.0 * radius * radius
    return ixx, iyy, izz


def _sphere_inertia(mass: float, radius: float) -> tuple[float, float, float]:
    i = (2.0 / 5.0) * mass * radius * radius
    return i, i, i


def estimate_inertial(
    geometry: Geometry,
    *,
    known_mass: float | None = None,
    density_kg_m3: float = DEFAULT_DENSITY_KG_M3,
    mesh_bbox_size: tuple[float, float, float] | None = None,
) -> InertialEstimate | None:
    """Computes mass (if not already known) and the diagonal inertia
    tensor for one geometry. `known_mass` should be the link's own
    already-set Inertial.mass when it's non-zero (an operator-entered
    real value always wins over a density-based guess) - pass None (or
    0.0, models.py's own "unset" default) to estimate it from volume.
    `mesh_bbox_size` is required for MeshGeometry (this module has no
    mesh loader of its own - the caller already has one, see
    render/mesh.py's own load_mesh_file(), to avoid this module needing
    a numpy dependency it otherwise wouldn't); returns None for a Mesh
    with no bbox supplied rather than fabricating a shape."""
    is_mesh = False
    if isinstance(geometry, BoxGeometry):
        volume = box_volume(geometry.size)
        size = geometry.size
        inertia_fn = _box_inertia
        inertia_args = (geometry.size,)
    elif isinstance(geometry, CylinderGeometry):
        volume = cylinder_volume(geometry.radius, geometry.length)
        inertia_fn = _cylinder_inertia
        inertia_args = (geometry.radius, geometry.length)
    elif isinstance(geometry, SphereGeometry):
        volume = sphere_volume(geometry.radius)
        inertia_fn = _sphere_inertia
        inertia_args = (geometry.radius,)
    elif isinstance(geometry, MeshGeometry):
        if mesh_bbox_size is None:
            return None
        is_mesh = True
        volume = box_volume(mesh_bbox_size)
        inertia_fn = _box_inertia
        inertia_args = (mesh_bbox_size,)
    else:
        return None

    mass_is_assumed = not known_mass
    mass = known_mass if known_mass else volume * density_kg_m3
    if mass <= 0:
        return None

    ixx, iyy, izz = inertia_fn(mass, *inertia_args)
    return InertialEstimate(
        mass=mass, ixx=ixx, iyy=iyy, izz=izz,
        mass_is_assumed=mass_is_assumed, is_mesh_approximation=is_mesh,
    )
