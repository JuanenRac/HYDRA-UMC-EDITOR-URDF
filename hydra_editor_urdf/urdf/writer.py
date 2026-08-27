# =============================================================================
# HYDRA-UMC EDITOR-URDF - urdf/writer.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# models.Robot -> URDF XML string - the exact inverse of parser.py, used
# both for "Export URDF" (ui/panels/upload_panel.py) and for the payload
# server/client.py uploads to a HYDRA-UMC-STUDIO server. Re-serializes
# from the in-memory tree rather than patching the original XML text, so
# every live edit (recolor/rescale/retype a joint/change DOF) is reflected
# exactly once, through one code path, regardless of which UI panel made it.
# =============================================================================
from __future__ import annotations

import xml.etree.ElementTree as ET
from xml.dom import minidom

from hydra_editor_urdf.models import (
    BoxGeometry,
    Collision,
    CylinderGeometry,
    Geometry,
    Inertial,
    Joint,
    Link,
    MeshGeometry,
    Origin,
    Robot,
    SphereGeometry,
    Visual,
)


def _fmt(values: tuple[float, ...]) -> str:
    return " ".join(_fmt_one(v) for v in values)


def _fmt_one(v: float) -> str:
    # Trim to a sane precision (URDF values are physical dimensions/angles,
    # not exact binary floats) without dropping to scientific notation,
    # which some URDF consumers (including this app's own parser, and
    # plenty of real-world ones) don't reliably round-trip.
    text = f"{v:.8f}".rstrip("0").rstrip(".")
    return text if text else "0"


def _set_origin(parent: ET.Element, origin: Origin) -> None:
    if origin.xyz == (0.0, 0.0, 0.0) and origin.rpy == (0.0, 0.0, 0.0):
        return  # identity - omit, matches how most hand-written URDFs skip it too
    el = ET.SubElement(parent, "origin")
    el.set("xyz", _fmt(origin.xyz))
    el.set("rpy", _fmt(origin.rpy))


def _set_geometry(parent: ET.Element, geometry: Geometry) -> None:
    geom_el = ET.SubElement(parent, "geometry")
    if isinstance(geometry, BoxGeometry):
        ET.SubElement(geom_el, "box").set("size", _fmt(geometry.size))
    elif isinstance(geometry, CylinderGeometry):
        cyl = ET.SubElement(geom_el, "cylinder")
        cyl.set("radius", _fmt_one(geometry.radius))
        cyl.set("length", _fmt_one(geometry.length))
    elif isinstance(geometry, SphereGeometry):
        ET.SubElement(geom_el, "sphere").set("radius", _fmt_one(geometry.radius))
    elif isinstance(geometry, MeshGeometry):
        mesh_el = ET.SubElement(geom_el, "mesh")
        mesh_el.set("filename", geometry.filename)
        if geometry.scale != (1.0, 1.0, 1.0):
            mesh_el.set("scale", _fmt(geometry.scale))


def _set_visual(link_el: ET.Element, visual: Visual) -> None:
    v_el = ET.SubElement(link_el, "visual")
    if visual.name:
        v_el.set("name", visual.name)
    _set_origin(v_el, visual.origin)
    _set_geometry(v_el, visual.geometry)
    if visual.material is not None:
        mat_el = ET.SubElement(v_el, "material")
        if visual.material.name:
            mat_el.set("name", visual.material.name)
        color_el = ET.SubElement(mat_el, "color")
        color_el.set("rgba", _fmt(visual.material.rgba))


def _set_collision(link_el: ET.Element, collision: Collision) -> None:
    c_el = ET.SubElement(link_el, "collision")
    if collision.name:
        c_el.set("name", collision.name)
    _set_origin(c_el, collision.origin)
    _set_geometry(c_el, collision.geometry)


def _set_inertial(link_el: ET.Element, inertial: Inertial | None) -> None:
    if inertial is None:
        return
    i_el = ET.SubElement(link_el, "inertial")
    _set_origin(i_el, inertial.origin)
    ET.SubElement(i_el, "mass").set("value", _fmt_one(inertial.mass))
    inertia_el = ET.SubElement(i_el, "inertia")
    inertia_el.set("ixx", _fmt_one(inertial.ixx))
    inertia_el.set("ixy", _fmt_one(inertial.ixy))
    inertia_el.set("ixz", _fmt_one(inertial.ixz))
    inertia_el.set("iyy", _fmt_one(inertial.iyy))
    inertia_el.set("iyz", _fmt_one(inertial.iyz))
    inertia_el.set("izz", _fmt_one(inertial.izz))


def _set_link(root: ET.Element, link: Link) -> None:
    link_el = ET.SubElement(root, "link")
    link_el.set("name", link.name)
    for visual in link.visuals:
        _set_visual(link_el, visual)
    for collision in link.collisions:
        _set_collision(link_el, collision)
    _set_inertial(link_el, link.inertial)


def _set_joint(root: ET.Element, joint: Joint) -> None:
    joint_el = ET.SubElement(root, "joint")
    joint_el.set("name", joint.name)
    joint_el.set("type", joint.type.value)
    _set_origin(joint_el, joint.origin)
    ET.SubElement(joint_el, "parent").set("link", joint.parent)
    ET.SubElement(joint_el, "child").set("link", joint.child)
    if joint.axis != (1.0, 0.0, 0.0):
        ET.SubElement(joint_el, "axis").set("xyz", _fmt(joint.axis))
    if joint.limit is not None:
        limit_el = ET.SubElement(joint_el, "limit")
        limit_el.set("lower", _fmt_one(joint.limit.lower))
        limit_el.set("upper", _fmt_one(joint.limit.upper))
        limit_el.set("effort", _fmt_one(joint.limit.effort))
        limit_el.set("velocity", _fmt_one(joint.limit.velocity))


def robot_to_urdf_string(robot: Robot, pretty: bool = True) -> str:
    root = ET.Element("robot")
    root.set("name", robot.name)

    for material in robot.materials.values():
        mat_el = ET.SubElement(root, "material")
        mat_el.set("name", material.name)
        ET.SubElement(mat_el, "color").set("rgba", _fmt(material.rgba))

    for link in robot.links.values():
        _set_link(root, link)
    for joint in robot.joints.values():
        _set_joint(root, joint)

    raw = ET.tostring(root, encoding="unicode")
    if not pretty:
        return raw
    # minidom's own toprettyxml is good enough for a human-readable export
    # and needs no extra dependency - not used for the parse path (only
    # ever consumed by parser.py, which doesn't care about whitespace).
    reparsed = minidom.parseString(raw)
    pretty_text = reparsed.toprettyxml(indent="  ")
    # minidom emits a `<?xml version="1.0" ?>` prologue and scatters blank
    # lines between every element from the raw string's own lack of
    # existing whitespace - strip both for an output that reads like a
    # normal hand-written URDF rather than minidom's own default styling.
    lines = [line for line in pretty_text.split("\n") if line.strip()]
    return "\n".join(lines[1:]) + "\n"
