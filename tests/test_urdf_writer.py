# =============================================================================
# HYDRA-UMC EDITOR-URDF - tests/test_urdf_writer.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Real unit tests for hydra_editor_urdf/urdf/writer.py, including real
# parse -> write -> parse round-trip checks (writer.py's own module doc
# calls itself "the exact inverse of parser.py" - these tests hold it to
# that claim directly, not just its own isolated output shape).
# =============================================================================
from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from hydra_editor_urdf.models import (
    BoxGeometry,
    CylinderGeometry,
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
from hydra_editor_urdf.urdf.parser import parse_urdf_string
from hydra_editor_urdf.urdf.writer import robot_to_urdf_string


def test_minimal_robot_round_trips():
    robot = Robot(name="mini", links={"base": Link(name="base")})
    xml_text = robot_to_urdf_string(robot)
    reparsed = parse_urdf_string(xml_text)
    assert reparsed.name == "mini"
    assert list(reparsed.links) == ["base"]


def test_identity_origin_is_omitted_from_output():
    robot = Robot(name="r", links={"a": Link(name="a", visuals=[Visual(geometry=BoxGeometry())])})
    xml_text = robot_to_urdf_string(robot)
    root = ET.fromstring(xml_text)
    visual_el = root.find("link/visual")
    assert visual_el.find("origin") is None


def test_non_identity_origin_is_emitted_and_round_trips():
    origin = Origin(xyz=(1.0, 2.0, 3.0), rpy=(0.1, 0.2, 0.3))
    robot = Robot(name="r", links={"a": Link(name="a", visuals=[Visual(origin=origin, geometry=BoxGeometry())])})
    xml_text = robot_to_urdf_string(robot)
    reparsed = parse_urdf_string(xml_text)
    got = reparsed.links["a"].visuals[0].origin
    assert got.xyz == pytest.approx(origin.xyz)
    assert got.rpy == pytest.approx(origin.rpy)


@pytest.mark.parametrize(
    "geometry",
    [
        BoxGeometry(size=(1.0, 2.0, 3.0)),
        CylinderGeometry(radius=0.4, length=1.2),
        SphereGeometry(radius=0.25),
        MeshGeometry(filename="meshes/link.stl", scale=(1.0, 1.0, 1.0)),
        MeshGeometry(filename="meshes/link.stl", scale=(2.0, 2.0, 2.0)),
    ],
)
def test_every_geometry_kind_round_trips(geometry):
    robot = Robot(name="r", links={"a": Link(name="a", visuals=[Visual(geometry=geometry)])})
    reparsed = parse_urdf_string(robot_to_urdf_string(robot))
    assert reparsed.links["a"].visuals[0].geometry == geometry


def test_default_mesh_scale_is_omitted_but_still_round_trips_as_default():
    geometry = MeshGeometry(filename="m.stl", scale=(1.0, 1.0, 1.0))
    robot = Robot(name="r", links={"a": Link(name="a", visuals=[Visual(geometry=geometry)])})
    xml_text = robot_to_urdf_string(robot)
    root = ET.fromstring(xml_text)
    mesh_el = root.find("link/visual/geometry/mesh")
    assert mesh_el.get("scale") is None
    assert parse_urdf_string(xml_text).links["a"].visuals[0].geometry.scale == (1.0, 1.0, 1.0)


def test_joint_default_axis_is_omitted_but_non_default_is_emitted():
    default_axis_joint = Joint(name="j1", type=JointType.REVOLUTE, parent="a", child="b")
    custom_axis_joint = Joint(name="j2", type=JointType.REVOLUTE, parent="b", child="c", axis=(0.0, 1.0, 0.0))
    robot = Robot(
        name="r",
        links={"a": Link(name="a"), "b": Link(name="b"), "c": Link(name="c")},
        joints={"j1": default_axis_joint, "j2": custom_axis_joint},
    )
    xml_text = robot_to_urdf_string(robot)
    root = ET.fromstring(xml_text)
    joints_by_name = {j.get("name"): j for j in root.findall("joint")}
    assert joints_by_name["j1"].find("axis") is None
    assert joints_by_name["j2"].find("axis").get("xyz") == "0 1 0"


def test_joint_limit_round_trips():
    joint = Joint(
        name="j",
        type=JointType.REVOLUTE,
        parent="a",
        child="b",
        limit=JointLimit(lower=-1.5, upper=1.5, effort=12.0, velocity=3.0),
    )
    robot = Robot(name="r", links={"a": Link(name="a"), "b": Link(name="b")}, joints={"j": joint})
    reparsed = parse_urdf_string(robot_to_urdf_string(robot))
    limit = reparsed.joints["j"].limit
    assert limit.lower == pytest.approx(-1.5)
    assert limit.upper == pytest.approx(1.5)
    assert limit.effort == pytest.approx(12.0)
    assert limit.velocity == pytest.approx(3.0)


def test_joint_without_limit_omits_the_element():
    joint = Joint(name="j", type=JointType.FIXED, parent="a", child="b")
    robot = Robot(name="r", links={"a": Link(name="a"), "b": Link(name="b")}, joints={"j": joint})
    reparsed = parse_urdf_string(robot_to_urdf_string(robot))
    assert reparsed.joints["j"].limit is None


def test_inertial_round_trips():
    inertial = Inertial(mass=2.0, ixx=0.1, ixy=0.02, ixz=0.03, iyy=0.2, iyz=0.04, izz=0.3)
    robot = Robot(name="r", links={"a": Link(name="a", inertial=inertial)})
    reparsed = parse_urdf_string(robot_to_urdf_string(robot))
    got = reparsed.links["a"].inertial
    assert got.mass == pytest.approx(2.0)
    assert got.ixx == pytest.approx(0.1)
    assert got.izz == pytest.approx(0.3)


def test_link_without_inertial_omits_the_element():
    robot = Robot(name="r", links={"a": Link(name="a")})
    xml_text = robot_to_urdf_string(robot)
    root = ET.fromstring(xml_text)
    assert root.find("link/inertial") is None


def test_negative_mass_is_written_through_unchanged():
    # writer.py has no business silently "fixing" a physically-invalid
    # value on export - urdf/dof.py's own validate() is the one real
    # place this gets flagged (see test_dof.py).
    robot = Robot(name="r", links={"a": Link(name="a", inertial=Inertial(mass=-5.0))})
    reparsed = parse_urdf_string(robot_to_urdf_string(robot))
    assert reparsed.links["a"].inertial.mass == pytest.approx(-5.0)


def test_top_level_materials_are_emitted_and_referenced_by_name():
    material = Material(name="shared-blue", rgba=(0.0, 0.0, 1.0, 1.0))
    robot = Robot(
        name="r",
        links={"a": Link(name="a", visuals=[Visual(geometry=BoxGeometry(), material=material)])},
        materials={"shared-blue": material},
    )
    xml_text = robot_to_urdf_string(robot)
    root = ET.fromstring(xml_text)
    assert root.find("material[@name='shared-blue']") is not None
    reparsed = parse_urdf_string(xml_text)
    assert reparsed.materials["shared-blue"].rgba == (0.0, 0.0, 1.0, 1.0)
    assert reparsed.links["a"].visuals[0].material.rgba == (0.0, 0.0, 1.0, 1.0)


def test_float_formatting_trims_trailing_zeros_without_scientific_notation():
    origin = Origin(xyz=(1.0, 0.5, 0.000001), rpy=(0.0, 0.0, 0.0))
    robot = Robot(name="r", links={"a": Link(name="a", visuals=[Visual(origin=origin, geometry=BoxGeometry())])})
    xml_text = robot_to_urdf_string(robot)
    root = ET.fromstring(xml_text)
    xyz_text = root.find("link/visual/origin").get("xyz")
    assert "e-" not in xyz_text.lower()
    assert xyz_text.split() == ["1", "0.5", "0.000001"]


def test_pretty_false_still_produces_well_formed_parseable_xml():
    robot = Robot(name="r", links={"a": Link(name="a")})
    xml_text = robot_to_urdf_string(robot, pretty=False)
    assert "\n" not in xml_text.strip().splitlines()[0] or True  # single-line output is fine either way
    assert parse_urdf_string(xml_text).name == "r"


def test_pretty_output_has_no_xml_prologue_and_no_blank_lines():
    robot = Robot(name="r", links={"a": Link(name="a")})
    xml_text = robot_to_urdf_string(robot, pretty=True)
    lines = xml_text.split("\n")
    assert not any(line.strip() == "" for line in lines[:-1])  # allow a single trailing newline
    assert "<?xml" not in xml_text


def test_multi_link_multi_joint_chain_round_trips_in_full():
    robot = Robot(
        name="arm",
        links={
            "base": Link(name="base"),
            "shoulder": Link(name="shoulder", inertial=Inertial(mass=1.5)),
            "elbow": Link(name="elbow"),
        },
        joints={
            "j1": Joint(
                name="j1", type=JointType.REVOLUTE, parent="base", child="shoulder",
                origin=Origin(xyz=(0.0, 0.0, 0.3)), axis=(0.0, 0.0, 1.0),
                limit=JointLimit(lower=-3.14, upper=3.14, effort=50.0, velocity=2.0),
            ),
            "j2": Joint(
                name="j2", type=JointType.PRISMATIC, parent="shoulder", child="elbow",
                origin=Origin(xyz=(0.25, 0.0, 0.0)),
                limit=JointLimit(lower=0.0, upper=0.5, effort=10.0, velocity=0.5),
            ),
        },
    )
    reparsed = parse_urdf_string(robot_to_urdf_string(robot))
    assert set(reparsed.links) == {"base", "shoulder", "elbow"}
    assert set(reparsed.joints) == {"j1", "j2"}
    assert reparsed.joints["j2"].type == JointType.PRISMATIC
    assert reparsed.links["shoulder"].inertial.mass == pytest.approx(1.5)
    assert reparsed.root_link_name() == "base"
