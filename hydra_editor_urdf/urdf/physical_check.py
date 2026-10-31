# =============================================================================
# HYDRA-UMC EDITOR-URDF - urdf/physical_check.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Physical validation of a model: are the numbers of a URDF coherent with a body that could exist?

The check is deterministic and read-only. Every finding is a `PhysicalWarning` with the rule, the element, the value found,
the limit it breaks and a suggested correction (`fix`); nothing is ever changed in the robot, and the correction is a
suggestion the user may apply by hand. The rules are:

  tree        a single root, no cycle, no link without a joint, no link out of reach of the root, one parent per link,
              no joint that names a link that does not exist, no duplicate names
  inertia     mass above 0, a finite inertia tensor that is positive definite and whose principal moments satisfy the
              triangle inequalities (Ixx + Iyy >= Izz and the permutations)
  limits      lower <= upper, effort and velocity above 0, a limit on every revolute and prismatic joint, none on a
              continuous one
  axes        a joint axis that is not zero and has length one
  meshes      the file of a mesh exists and its scale is positive, reasonable and the same on the three axes
  units       lengths, angles and masses that look like millimetres, degrees or grams where metres, radians and
              kilograms are expected

The tensor is stored as six numbers, so it is symmetric by construction; what is checked is that they are finite.
The bounds of the "units" rules and of the mesh scale are settings (`PhysicalLimits.from_config`).
"""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Mapping

import numpy as np

from hydra_editor_urdf.models import (
    BoxGeometry,
    CylinderGeometry,
    JointType,
    MeshGeometry,
    Robot,
    SphereGeometry,
)

RULES = (
    "tree_no_root",
    "tree_multiple_roots",
    "tree_cycle",
    "tree_orphan_link",
    "tree_unreachable_link",
    "tree_multiple_parents",
    "tree_unknown_link",
    "duplicate_name",
    "mass_not_positive",
    "inertia_not_finite",
    "inertia_not_positive_definite",
    "inertia_triangle",
    "limit_missing",
    "limit_inverted",
    "velocity_not_positive",
    "effort_not_positive",
    "continuous_with_limits",
    "axis_zero",
    "axis_not_unit",
    "mesh_missing",
    "mesh_scale_invalid",
    "mesh_scale_anisotropic",
    "units_length",
    "units_angle",
    "units_mass",
)
_ORDER = {rule: index for index, rule in enumerate(RULES)}

_AXIS_TOLERANCE = 1e-6
_EIGEN_TOLERANCE = 1e-12  # relative to the largest principal moment
_TRIANGLE_TOLERANCE = 1e-9  # relative to the largest principal moment


@dataclass(frozen=True)
class PhysicalLimits:
    """The bounds of the rules that depend on a judgement of scale, with the default of each. They are read from the
    configuration file by `from_config` (`physical_max_length_m`, `physical_max_angle_rad`, `physical_max_mass_kg`,
    `physical_mesh_scale_min`, `physical_mesh_scale_max`); a value that is not a positive finite number is ignored."""

    max_length_m: float = 100.0
    max_angle_rad: float = 4.0 * math.pi
    max_mass_kg: float = 10000.0
    mesh_scale_min: float = 1e-4
    mesh_scale_max: float = 1000.0

    @staticmethod
    def from_config(config: Mapping[str, object]) -> "PhysicalLimits":
        defaults = PhysicalLimits()

        def number(key: str, default: float) -> float:
            value = config.get(key, default)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return default
            return float(value) if math.isfinite(value) and value > 0 else default

        return PhysicalLimits(
            max_length_m=number("physical_max_length_m", defaults.max_length_m),
            max_angle_rad=number("physical_max_angle_rad", defaults.max_angle_rad),
            max_mass_kg=number("physical_max_mass_kg", defaults.max_mass_kg),
            mesh_scale_min=number("physical_mesh_scale_min", defaults.mesh_scale_min),
            mesh_scale_max=number("physical_mesh_scale_max", defaults.mesh_scale_max),
        )


@dataclass(frozen=True)
class PhysicalWarning:
    """One finding. `element` names what is wrong (`link:arm`, `joint:j1`, `link:arm/visual[0]`), `value` is what was
    found, `limit` the bound it breaks and `fix` the number (or name) the suggested correction uses; the text of the
    correction is the one of `rule` in the language file."""

    rule: str
    element: str
    value: str
    limit: str
    fix: str = ""

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


Translate = Callable[..., str]


def describe(warning: PhysicalWarning, translate: Translate) -> str:
    """The warning as one line in the language of `translate` (the `_` of hydra_editor_urdf.i18n)."""
    return translate(
        "PHYS_LINE",
        rule=warning.rule,
        what=translate("PHYS_R_" + warning.rule),
        element=warning.element,
        value=warning.value,
        limit=warning.limit,
        fix=translate("PHYS_F_" + warning.rule, fix=warning.fix, value=warning.value, limit=warning.limit),
    )


def _fmt(value: float) -> str:
    return f"{value:.6g}"


def _finite(*values: float) -> bool:
    return all(math.isfinite(v) for v in values)


# --- the tree ---------------------------------------------------------------------------------------------------------------


def _tree_warnings(robot: Robot) -> list[PhysicalWarning]:
    found: list[PhysicalWarning] = []
    joints = list(robot.joints.values())
    names = set(robot.links)

    for joint in joints:
        for role, target in (("parent", joint.parent), ("child", joint.child)):
            if target not in names:
                found.append(PhysicalWarning("tree_unknown_link", f"joint:{joint.name}", target, f"{role} link exists"))

    in_joint = {j.parent for j in joints} | {j.child for j in joints}
    linked = sorted(name for name in names if name in in_joint)
    if len(names) > 1:
        for name in sorted(names - in_joint):
            found.append(PhysicalWarning("tree_orphan_link", f"link:{name}", "no joint", "at least 1 joint", name))

    children = Counter(j.child for j in joints)
    for name in sorted(n for n, count in children.items() if count > 1):
        parents = ",".join(sorted(j.parent for j in joints if j.child == name))
        found.append(PhysicalWarning("tree_multiple_parents", f"link:{name}", f"{children[name]} parents ({parents})", "1 parent"))

    roots = [name for name in linked if name not in children]
    if joints and not roots:
        found.append(PhysicalWarning("tree_no_root", f"robot:{robot.name}", "0 roots", "1 root"))
    elif len(roots) > 1:
        found.append(PhysicalWarning("tree_multiple_roots", f"robot:{robot.name}", f"{len(roots)} roots ({','.join(roots)})", "1 root", roots[0]))

    # a cycle: what is left of the graph when every link with no parent left is taken away, repeatedly
    remaining = {name: 0 for name in linked}
    edges = [(j.parent, j.child) for j in joints if j.parent in remaining and j.child in remaining]
    for _parent, child in edges:
        remaining[child] += 1
    ready = sorted(name for name, count in remaining.items() if count == 0)
    removed: set[str] = set()
    while ready:
        node = ready.pop()
        removed.add(node)
        for parent, child in edges:
            if parent == node:
                remaining[child] -= 1
                if remaining[child] == 0:
                    ready.append(child)
    cyclic = sorted(set(linked) - removed)
    if cyclic:
        found.append(PhysicalWarning("tree_cycle", f"robot:{robot.name}", ",".join(cyclic), "no cycle", cyclic[0]))

    if len(roots) == 1:
        reached = {roots[0]}
        frontier = [roots[0]]
        while frontier:
            here = frontier.pop()
            for joint in joints:
                if joint.parent == here and joint.child not in reached:
                    reached.add(joint.child)
                    frontier.append(joint.child)
        for name in sorted(set(linked) - reached):
            found.append(PhysicalWarning("tree_unreachable_link", f"link:{name}", "not reachable", f"reachable from {roots[0]}", roots[0]))

    for key, link in robot.links.items():
        if link.name != key:
            found.append(PhysicalWarning("duplicate_name", f"link:{key}", f"also named {link.name}", "one name per link", key))
        for kind, items in (("visual", link.visuals), ("collision", link.collisions)):
            counts = Counter(item.name for item in items if item.name)
            for name, count in sorted(counts.items()):
                if count > 1:
                    found.append(PhysicalWarning("duplicate_name", f"link:{key}/{kind}", f"{name} x{count}", "one name per " + kind, name))
    for key, joint in robot.joints.items():
        if joint.name != key:
            found.append(PhysicalWarning("duplicate_name", f"joint:{key}", f"also named {joint.name}", "one name per joint", key))
    return found


def duplicate_names_in_xml(xml_text: str) -> list[PhysicalWarning]:
    """The names a URDF file uses twice (links, joints, materials). The reader refuses such a file, so this looks at the XML
    itself; a text that is not well-formed XML gives an empty list (the reader reports that)."""
    if "<!DOCTYPE" in xml_text.upper() or "<!ENTITY" in xml_text.upper():
        return []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    found: list[PhysicalWarning] = []
    for tag in ("link", "joint"):
        counts = Counter(el.get("name") for el in root.findall(tag) if el.get("name"))
        for name, count in sorted((str(n), c) for n, c in counts.items()):
            if count > 1:
                found.append(PhysicalWarning("duplicate_name", f"{tag}:{name}", f"{count} {tag}s", f"one {tag} per name", name))
    return found


# --- inertia ----------------------------------------------------------------------------------------------------------------


def _inertia_warnings(robot: Robot, limits: PhysicalLimits) -> list[PhysicalWarning]:
    found: list[PhysicalWarning] = []
    for name, link in robot.links.items():
        inertial = link.inertial
        if inertial is None:
            continue
        element = f"link:{name}"
        if not _finite(inertial.mass) or inertial.mass <= 0:
            found.append(PhysicalWarning("mass_not_positive", element, _fmt(inertial.mass), "> 0", "0.001"))
        elif inertial.mass > limits.max_mass_kg:
            found.append(PhysicalWarning("units_mass", element, _fmt(inertial.mass), f"<= {_fmt(limits.max_mass_kg)} kg", _fmt(inertial.mass / 1000.0)))
        components = (inertial.ixx, inertial.ixy, inertial.ixz, inertial.iyy, inertial.iyz, inertial.izz)
        if not _finite(*components):
            found.append(PhysicalWarning("inertia_not_finite", element, "NaN or infinity", "finite numbers"))
            continue
        matrix = np.array(
            [[inertial.ixx, inertial.ixy, inertial.ixz], [inertial.ixy, inertial.iyy, inertial.iyz], [inertial.ixz, inertial.iyz, inertial.izz]],
            dtype=float,
        )
        a, b, c = (float(v) for v in np.linalg.eigvalsh(matrix))  # ascending
        tolerance = _EIGEN_TOLERANCE * max(abs(a), abs(b), abs(c))
        if a <= tolerance:
            # adding d to the diagonal moves every principal moment by d, so d = |smallest| + a small margin makes it positive definite
            found.append(PhysicalWarning("inertia_not_positive_definite", element, f"smallest principal moment {_fmt(a)}", "> 0", _fmt(-a + max(abs(c), 1e-6) * 1e-3)))
            continue
        if a + b < c * (1.0 - _TRIANGLE_TOLERANCE):
            found.append(PhysicalWarning("inertia_triangle", element, f"{_fmt(a)} + {_fmt(b)} = {_fmt(a + b)}", f">= {_fmt(c)}", _fmt(c - a - b)))
    return found


# --- joints -----------------------------------------------------------------------------------------------------------------


def _joint_warnings(robot: Robot, limits: PhysicalLimits) -> list[PhysicalWarning]:
    found: list[PhysicalWarning] = []
    for key, joint in robot.joints.items():
        element = f"joint:{key}"
        bounded = joint.type in (JointType.REVOLUTE, JointType.PRISMATIC)
        limit = joint.limit
        if bounded and limit is None:
            found.append(PhysicalWarning("limit_missing", element, "no <limit>", "a <limit> with lower, upper, effort and velocity"))
        if limit is not None and joint.type in (JointType.REVOLUTE, JointType.PRISMATIC, JointType.CONTINUOUS):
            if bounded and (not _finite(limit.lower, limit.upper) or limit.lower > limit.upper):
                found.append(PhysicalWarning("limit_inverted", element, f"lower {_fmt(limit.lower)}, upper {_fmt(limit.upper)}", "lower <= upper", f"lower {_fmt(limit.upper)}, upper {_fmt(limit.lower)}"))
            if not _finite(limit.velocity) or limit.velocity <= 0:
                found.append(PhysicalWarning("velocity_not_positive", element, _fmt(limit.velocity), "> 0", "1"))
            if not _finite(limit.effort) or limit.effort <= 0:
                found.append(PhysicalWarning("effort_not_positive", element, _fmt(limit.effort), "> 0", "1"))
            if joint.type is JointType.CONTINUOUS and (limit.lower != 0 or limit.upper != 0):
                found.append(PhysicalWarning("continuous_with_limits", element, f"lower {_fmt(limit.lower)}, upper {_fmt(limit.upper)}", "none on a continuous joint", "0"))
            if joint.type is JointType.REVOLUTE and _finite(limit.lower, limit.upper):
                worst = max(abs(limit.lower), abs(limit.upper))
                if worst > limits.max_angle_rad:
                    found.append(PhysicalWarning("units_angle", element, _fmt(worst), f"<= {_fmt(limits.max_angle_rad)} rad", _fmt(math.radians(worst))))
            if joint.type is JointType.PRISMATIC and _finite(limit.lower, limit.upper):
                worst = max(abs(limit.lower), abs(limit.upper))
                if worst > limits.max_length_m:
                    found.append(PhysicalWarning("units_length", element, _fmt(worst), f"<= {_fmt(limits.max_length_m)} m", _fmt(worst / 1000.0)))
        if joint.type in (JointType.REVOLUTE, JointType.PRISMATIC, JointType.CONTINUOUS, JointType.PLANAR):
            axis = joint.axis
            norm = math.sqrt(sum(c * c for c in axis)) if _finite(*axis) else float("nan")
            if not math.isfinite(norm) or norm < 1e-12:
                found.append(PhysicalWarning("axis_zero", element, "x y z = " + " ".join(_fmt(c) for c in axis), "a non-zero axis", "1 0 0"))
            elif abs(norm - 1.0) > _AXIS_TOLERANCE:
                found.append(PhysicalWarning("axis_not_unit", element, f"length {_fmt(norm)}", "length 1", " ".join(_fmt(c / norm) for c in axis)))
        origin = joint.origin
        if _finite(*origin.xyz) and math.sqrt(sum(c * c for c in origin.xyz)) > limits.max_length_m:
            found.append(PhysicalWarning("units_length", element, _fmt(math.sqrt(sum(c * c for c in origin.xyz))), f"<= {_fmt(limits.max_length_m)} m", _fmt(math.sqrt(sum(c * c for c in origin.xyz)) / 1000.0)))
        if _finite(*origin.rpy) and max(abs(c) for c in origin.rpy) > limits.max_angle_rad:
            worst = max(abs(c) for c in origin.rpy)
            found.append(PhysicalWarning("units_angle", element, _fmt(worst), f"<= {_fmt(limits.max_angle_rad)} rad", _fmt(math.radians(worst))))
    return found


# --- geometry ---------------------------------------------------------------------------------------------------------------


def _geometry_warnings(robot: Robot, limits: PhysicalLimits, resolver: Callable[[str], Path | None] | None) -> list[PhysicalWarning]:
    found: list[PhysicalWarning] = []
    for name, link in robot.links.items():
        shapes = [(f"link:{name}/visual[{i}]", v.geometry) for i, v in enumerate(link.visuals)]
        shapes += [(f"link:{name}/collision[{i}]", c.geometry) for i, c in enumerate(link.collisions)]
        for element, geometry in shapes:
            if isinstance(geometry, MeshGeometry):
                if resolver is not None and geometry.filename and resolver(geometry.filename) is None:
                    found.append(PhysicalWarning("mesh_missing", element, geometry.filename, "an existing file"))
                scale = geometry.scale
                if not _finite(*scale) or min(scale) <= 0 or min(scale) < limits.mesh_scale_min or max(scale) > limits.mesh_scale_max:
                    text = " ".join(_fmt(s) for s in scale)
                    found.append(PhysicalWarning("mesh_scale_invalid", element, text, f"{_fmt(limits.mesh_scale_min)} to {_fmt(limits.mesh_scale_max)}", "1 1 1"))
                elif max(scale) - min(scale) > 1e-9 * max(scale):
                    found.append(PhysicalWarning("mesh_scale_anisotropic", element, " ".join(_fmt(s) for s in scale), "the same on x, y and z", _fmt(scale[0])))
                continue
            if isinstance(geometry, BoxGeometry):
                biggest = max(geometry.size) if _finite(*geometry.size) else 0.0
            elif isinstance(geometry, CylinderGeometry):
                biggest = max(geometry.radius, geometry.length) if _finite(geometry.radius, geometry.length) else 0.0
            elif isinstance(geometry, SphereGeometry):
                biggest = geometry.radius if _finite(geometry.radius) else 0.0
            else:
                continue
            if biggest > limits.max_length_m:
                found.append(PhysicalWarning("units_length", element, _fmt(biggest), f"<= {_fmt(limits.max_length_m)} m", _fmt(biggest / 1000.0)))
    return found


def check_robot(
    robot: Robot,
    resolver: Callable[[str], Path | None] | None = None,
    limits: PhysicalLimits | None = None,
) -> list[PhysicalWarning]:
    """Every finding of the physical check, in a fixed order (by rule, then element, then value). `resolver` is the mesh
    resolver of the editor; without one the existence of the mesh files is not checked."""
    bounds = limits if limits is not None else PhysicalLimits()
    found = _tree_warnings(robot) + _inertia_warnings(robot, bounds) + _joint_warnings(robot, bounds) + _geometry_warnings(robot, bounds, resolver)
    return sorted(found, key=lambda w: (_ORDER[w.rule], w.element, w.value))


def physical_warning_lines(
    robot: Robot,
    translate: Translate,
    resolver: Callable[[str], Path | None] | None = None,
    limits: PhysicalLimits | None = None,
) -> list[str]:
    return [describe(w, translate) for w in check_robot(robot, resolver, limits)]
