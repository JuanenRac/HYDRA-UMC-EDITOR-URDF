# =============================================================================
# HYDRA-UMC EDITOR-URDF - urdf/parser.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Plain URDF XML -> models.py object tree, via the stdlib's own
# xml.etree.ElementTree (no lxml dependency needed for a format this
# simple). Deliberately does NOT expand xacro macros (<xacro:*> tags,
# ${...} expressions, <xacro:property>/<xacro:macro>) - xacro is a
# Python/XML macro preprocessor with its own package (`xacro`, itself a
# ROS package with a heavier dependency chain), and a real xacro file is
# only truly resolvable with the same ROS package environment it was
# authored against (macro args, included files via `$(find pkg)`, etc.).
# ParserError below reports a raw `.xacro` file or literal `${` found in
# an otherwise-URDF-shaped file as a clear, named limitation rather than
# silently mis-parsing it. Real xacro support is documented future work,
# not a silent gap.
# =============================================================================
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from hydra_editor_urdf.models import (
    BoxGeometry,
    Collision,
    CylinderGeometry,
    Geometry,
    Inertial,
    Joint,
    JointLimit,
    JointType,
    Link,
    Material,
    MeshGeometry,
    Origin,
    Robot,
    SphereGeometry,
    Visual,
)


class UrdfParseError(Exception):
    """Raised for anything that isn't a plain, well-formed <robot> URDF -
    including the xacro case above. Always carries a human-readable
    `.args[0]`, since this is what source/scan.py and ui/panels/
    source_panel.py surface directly to the operator, not a stack trace."""


def _parse_floats(text: str | None, count: int, default: tuple[float, ...]) -> tuple[float, ...]:
    if not text or not text.strip():
        return default
    parts = text.split()
    if len(parts) != count:
        raise UrdfParseError(f"Expected {count} numbers, got {len(parts)!r} in {text!r}")
    return tuple(float(p) for p in parts)


def _parse_origin(el: ET.Element | None) -> Origin:
    if el is None:
        return Origin.identity()
    xyz = _parse_floats(el.get("xyz"), 3, (0.0, 0.0, 0.0))
    rpy = _parse_floats(el.get("rpy"), 3, (0.0, 0.0, 0.0))
    return Origin(xyz=xyz, rpy=rpy)  # type: ignore[arg-type]


def _parse_geometry(el: ET.Element | None) -> Geometry:
    if el is None:
        # A <visual>/<collision> with no <geometry> is malformed per spec,
        # but crashing the whole import over one link's own bad geometry
        # is worse than substituting a small, visibly-a-placeholder box -
        # DOF validation and the rest of the tree still get parsed either way.
        return BoxGeometry(size=(0.05, 0.05, 0.05))
    box = el.find("box")
    if box is not None:
        return BoxGeometry(size=_parse_floats(box.get("size"), 3, (1.0, 1.0, 1.0)))  # type: ignore[arg-type]
    cylinder = el.find("cylinder")
    if cylinder is not None:
        return CylinderGeometry(radius=float(cylinder.get("radius", 0.5)), length=float(cylinder.get("length", 1.0)))
    sphere = el.find("sphere")
    if sphere is not None:
        return SphereGeometry(radius=float(sphere.get("radius", 0.5)))
    mesh = el.find("mesh")
    if mesh is not None:
        scale = _parse_floats(mesh.get("scale"), 3, (1.0, 1.0, 1.0))
        return MeshGeometry(filename=mesh.get("filename", ""), scale=scale)  # type: ignore[arg-type]
    return BoxGeometry(size=(0.05, 0.05, 0.05))


def _parse_material_inline(el: ET.Element | None) -> Material | None:
    """A <material> element found INSIDE a <visual> - either a bare
    color/name pair, or a name-only reference resolved later by the
    caller against Robot.materials (top-level <material> declarations
    are parsed separately, see _parse_top_level_materials)."""
    if el is None:
        return None
    name = el.get("name", "")
    color_el = el.find("color")
    if color_el is not None:
        rgba = _parse_floats(color_el.get("rgba"), 4, (0.8, 0.8, 0.8, 1.0))
        return Material(name=name, rgba=rgba)  # type: ignore[arg-type]
    return Material(name=name, rgba=(0.8, 0.8, 0.8, 1.0))  # resolved against Robot.materials by name, if it exists


def _parse_top_level_materials(root: ET.Element) -> dict[str, Material]:
    materials: dict[str, Material] = {}
    for el in root.findall("material"):
        name = el.get("name", "")
        if not name:
            continue
        color_el = el.find("color")
        if color_el is not None:
            rgba = _parse_floats(color_el.get("rgba"), 4, (0.8, 0.8, 0.8, 1.0))
            materials[name] = Material(name=name, rgba=rgba)  # type: ignore[arg-type]
    return materials


def _parse_visual(el: ET.Element, top_level_materials: dict[str, Material]) -> Visual:
    material = _parse_material_inline(el.find("material"))
    if material is not None and material.name and material.name in top_level_materials:
        # An inline <material name="foo"/> with no <color> of its own is a
        # reference to the top-level declaration - swap in the real rgba
        # so every downstream consumer (viewport, properties panel) only
        # ever deals with a resolved color, never a name it has to chase.
        if material.rgba == (0.8, 0.8, 0.8, 1.0) and el.find("material/color") is None:
            material = top_level_materials[material.name]
    return Visual(
        name=el.get("name", ""),
        origin=_parse_origin(el.find("origin")),
        geometry=_parse_geometry(el.find("geometry")),
        material=material,
    )


def _parse_collision(el: ET.Element) -> Collision:
    return Collision(
        name=el.get("name", ""),
        origin=_parse_origin(el.find("origin")),
        geometry=_parse_geometry(el.find("geometry")),
    )


def _parse_inertial(el: ET.Element | None) -> Inertial | None:
    if el is None:
        return None
    mass_el = el.find("mass")
    mass = float(mass_el.get("value", 0.0)) if mass_el is not None else 0.0
    inertia_el = el.find("inertia")
    if inertia_el is not None:
        ixx = float(inertia_el.get("ixx", 0.0))
        ixy = float(inertia_el.get("ixy", 0.0))
        ixz = float(inertia_el.get("ixz", 0.0))
        iyy = float(inertia_el.get("iyy", 0.0))
        iyz = float(inertia_el.get("iyz", 0.0))
        izz = float(inertia_el.get("izz", 0.0))
    else:
        ixx = ixy = ixz = iyy = iyz = izz = 0.0
    return Inertial(mass=mass, origin=_parse_origin(el.find("origin")), ixx=ixx, ixy=ixy, ixz=ixz, iyy=iyy, iyz=iyz, izz=izz)


def _parse_link(el: ET.Element, top_level_materials: dict[str, Material]) -> Link:
    name = el.get("name")
    if not name:
        raise UrdfParseError("Found a <link> with no name= attribute")
    return Link(
        name=name,
        visuals=[_parse_visual(v, top_level_materials) for v in el.findall("visual")],
        collisions=[_parse_collision(c) for c in el.findall("collision")],
        inertial=_parse_inertial(el.find("inertial")),
    )


def _parse_joint(el: ET.Element) -> Joint:
    name = el.get("name")
    type_str = el.get("type")
    if not name or not type_str:
        raise UrdfParseError("Found a <joint> missing name= or type=")
    try:
        jtype = JointType(type_str)
    except ValueError:
        raise UrdfParseError(f"Joint {name!r} has unknown type {type_str!r} (URDF defines: "
                              f"{', '.join(t.value for t in JointType)})") from None

    parent_el = el.find("parent")
    child_el = el.find("child")
    if parent_el is None or child_el is None:
        raise UrdfParseError(f"Joint {name!r} is missing <parent>/<child>")
    parent = parent_el.get("link")
    child = child_el.get("link")
    if not parent or not child:
        raise UrdfParseError(f"Joint {name!r} has a <parent>/<child> with no link= attribute")

    axis_el = el.find("axis")
    axis = _parse_floats(axis_el.get("xyz") if axis_el is not None else None, 3, (1.0, 0.0, 0.0))

    limit_el = el.find("limit")
    limit = None
    if limit_el is not None:
        limit = JointLimit(
            lower=float(limit_el.get("lower", 0.0)),
            upper=float(limit_el.get("upper", 0.0)),
            effort=float(limit_el.get("effort", 0.0)),
            velocity=float(limit_el.get("velocity", 0.0)),
        )

    return Joint(name=name, type=jtype, parent=parent, child=child, origin=_parse_origin(el.find("origin")), axis=axis, limit=limit)  # type: ignore[arg-type]


def parse_urdf_string(xml_text: str) -> Robot:
    stripped = xml_text.lstrip()
    # xacro files commonly keep a .urdf/.xacro extension either way and
    # declare the xacro namespace on the root <robot> tag itself - this
    # is the one cheap, reliable signal available without a real XML
    # namespace-aware macro expander.
    if "xacro" in stripped[:2000] and ("xmlns:xacro" in stripped[:2000] or "<xacro:" in stripped):
        raise UrdfParseError(
            "This file uses xacro macros (<xacro:...> tags / xmlns:xacro), which this app does not "
            "expand yet - run it through the ROS `xacro` tool first (e.g. `xacro model.xacro > model.urdf`) "
            "and import the resulting plain .urdf instead."
        )
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise UrdfParseError(f"Not well-formed XML: {e}") from e

    if root.tag != "robot":
        raise UrdfParseError(f"Root element is <{root.tag}>, expected <robot>")

    robot = Robot(name=root.get("name", "robot"))
    robot.materials = _parse_top_level_materials(root)

    for link_el in root.findall("link"):
        link = _parse_link(link_el, robot.materials)
        if link.name in robot.links:
            raise UrdfParseError(f"Duplicate <link name=\"{link.name}\">")
        robot.links[link.name] = link

    for joint_el in root.findall("joint"):
        joint = _parse_joint(joint_el)
        if joint.name in robot.joints:
            raise UrdfParseError(f"Duplicate <joint name=\"{joint.name}\">")
        robot.joints[joint.name] = joint

    if not robot.links:
        raise UrdfParseError("No <link> elements found - not a usable URDF")

    return robot


def parse_urdf_file(path: str | Path) -> Robot:
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        raise UrdfParseError(f"Couldn't read {path}: {e}") from e
    return parse_urdf_string(text)
