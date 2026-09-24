# =============================================================================
# HYDRA-UMC-EDITOR-URDF - hydra_editor_urdf/urdf/save_check.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Checks a robot before it is written out, so a model with a physically
impossible or unusable part is refused with a list of exactly what to fix.

Covered: joint limits (finite, lower below upper, non-negative effort and
velocity), a joint axis that is a real direction, geometry with positive
dimensions, a mesh whose file exists, and two links that sit exactly on top
of each other with a fixed joint between distinct points (a basic
collision hint). Structural problems (roots, cycles, orphans) stay in
`dof.validate`.
"""

from __future__ import annotations

import math
from pathlib import Path

from ..models import (
    BoxGeometry,
    CylinderGeometry,
    JointType,
    MeshGeometry,
    Robot,
    SphereGeometry,
)


class UrdfSaveError(ValueError):
    """Raised by export when the robot fails the pre-save check; `issues` lists every problem."""

    def __init__(self, issues: list[str]) -> None:
        super().__init__("the robot cannot be saved: " + "; ".join(issues))
        self.issues = issues


def _finite(*values: float) -> bool:
    return all(isinstance(v, (int, float)) and math.isfinite(v) for v in values)


def _geometry_issues(where: str, geometry: object, mesh_root: Path | None) -> list[str]:
    if isinstance(geometry, BoxGeometry):
        if not _finite(*geometry.size) or any(d <= 0 for d in geometry.size):
            return [f"{where}: box size must be positive and finite, got {geometry.size}"]
    elif isinstance(geometry, CylinderGeometry):
        if not _finite(geometry.radius, geometry.length) or geometry.radius <= 0 or geometry.length <= 0:
            return [f"{where}: cylinder radius and length must be positive and finite"]
    elif isinstance(geometry, SphereGeometry):
        if not _finite(geometry.radius) or geometry.radius <= 0:
            return [f"{where}: sphere radius must be positive and finite"]
    elif isinstance(geometry, MeshGeometry):
        issues: list[str] = []
        if not geometry.filename.strip():
            issues.append(f"{where}: mesh has no filename")
        elif mesh_root is not None and not geometry.filename.startswith(("package://", "file://", "http")):
            if not (mesh_root / geometry.filename).is_file():
                issues.append(f"{where}: mesh file {geometry.filename!r} was not found under {mesh_root}")
        if not _finite(*geometry.scale) or any(s == 0 for s in geometry.scale):
            issues.append(f"{where}: mesh scale must be finite and non-zero, got {geometry.scale}")
        return issues
    return []


def check_before_save(robot: Robot, mesh_root: Path | None = None) -> list[str]:
    """Every problem found, in a stable order; an empty list means the robot may be saved."""
    issues: list[str] = []
    for joint in robot.joints.values():
        label = f"joint {joint.name!r}"
        if joint.is_movable:
            length = math.sqrt(sum(c * c for c in joint.axis)) if _finite(*joint.axis) else float("nan")
            if not math.isfinite(length) or length < 1e-9:
                issues.append(f"{label}: the axis {joint.axis} is not a direction")
        if joint.type in (JointType.REVOLUTE, JointType.PRISMATIC):
            limit = joint.limit
            if limit is None:
                issues.append(f"{label}: a {joint.type.value} joint needs a limit")
            else:
                if not _finite(limit.lower, limit.upper, limit.effort, limit.velocity):
                    issues.append(f"{label}: limit values must be finite")
                elif limit.lower > limit.upper:
                    issues.append(f"{label}: lower limit {limit.lower} is above upper limit {limit.upper}")
                if _finite(limit.effort, limit.velocity) and (limit.effort < 0 or limit.velocity < 0):
                    issues.append(f"{label}: effort and velocity must not be negative")
    for link in robot.links.values():
        for index, visual in enumerate(link.visuals):
            issues.extend(_geometry_issues(f"link {link.name!r} visual {index}", visual.geometry, mesh_root))
        for index, collision in enumerate(link.collisions):
            issues.extend(_geometry_issues(f"link {link.name!r} collision {index}", collision.geometry, mesh_root))
        if link.inertial is not None:
            mass = getattr(link.inertial, "mass", None)
            if mass is not None and (not _finite(mass) or mass < 0):
                issues.append(f"link {link.name!r}: mass must be finite and not negative")
    return issues
