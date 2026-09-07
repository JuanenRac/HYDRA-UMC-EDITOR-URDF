# =============================================================================
# HYDRA-UMC EDITOR-URDF - tests/test_urdf_parser.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Real unit tests for hydra_editor_urdf/urdf/parser.py - previously
# untested pure logic (found in an ecosystem-wide software-improvements
# audit). No Qt import anywhere in this file, so this runs with just the
# stdlib - no PySide6 install needed to verify the actual parsing rules.
# =============================================================================
from __future__ import annotations

import pytest

from hydra_editor_urdf.models import (
    BoxGeometry,
    CylinderGeometry,
    JointType,
    MeshGeometry,
    SphereGeometry,
)
from hydra_editor_urdf.urdf.parser import UrdfParseError, parse_urdf_file, parse_urdf_string

MINIMAL_ROBOT = """<robot name="r"><link name="base"/></robot>"""


def two_link_robot(extra_joint_attrs: str = "") -> str:
    return f"""
    <robot name="arm">
      <link name="base"/>
      <link name="shoulder"/>
      <joint name="j1" type="revolute" {extra_joint_attrs}>
        <origin xyz="0 0 0.1" rpy="0 0 0"/>
        <parent link="base"/>
        <child link="shoulder"/>
        <axis xyz="0 0 1"/>
        <limit lower="-1.57" upper="1.57" effort="10" velocity="1"/>
      </joint>
    </robot>
    """


# --- robot/link/joint basics -------------------------------------------------


def test_parses_minimal_single_link_robot():
    robot = parse_urdf_string(MINIMAL_ROBOT)
    assert robot.name == "r"
    assert list(robot.links) == ["base"]
    assert robot.joints == {}


def test_root_tag_must_be_robot():
    with pytest.raises(UrdfParseError, match="expected <robot>"):
        parse_urdf_string("<not_a_robot/>")


def test_malformed_xml_is_a_parse_error():
    with pytest.raises(UrdfParseError, match="Not well-formed XML"):
        parse_urdf_string("<robot><link")


def test_no_links_is_an_error():
    with pytest.raises(UrdfParseError, match="No <link> elements"):
        parse_urdf_string('<robot name="empty"></robot>')


def test_missing_robot_name_defaults_to_robot():
    robot = parse_urdf_string("<robot><link name='base'/></robot>")
    assert robot.name == "robot"


def test_duplicate_link_name_is_an_error():
    xml = """<robot><link name="a"/><link name="a"/></robot>"""
    with pytest.raises(UrdfParseError, match="Duplicate <link"):
        parse_urdf_string(xml)


def test_duplicate_joint_name_is_an_error():
    xml = """
    <robot>
      <link name="a"/><link name="b"/><link name="c"/>
      <joint name="j" type="fixed"><parent link="a"/><child link="b"/></joint>
      <joint name="j" type="fixed"><parent link="b"/><child link="c"/></joint>
    </robot>
    """
    with pytest.raises(UrdfParseError, match="Duplicate <joint"):
        parse_urdf_string(xml)


def test_link_without_name_is_an_error():
    with pytest.raises(UrdfParseError, match="no name="):
        parse_urdf_string("<robot><link/></robot>")


# --- joints -------------------------------------------------------------


def test_parses_a_full_revolute_joint():
    robot = parse_urdf_string(two_link_robot())
    joint = robot.joints["j1"]
    assert joint.type == JointType.REVOLUTE
    assert joint.parent == "base"
    assert joint.child == "shoulder"
    assert joint.origin.xyz == (0.0, 0.0, 0.1)
    assert joint.axis == (0.0, 0.0, 1.0)
    assert joint.limit is not None
    assert joint.limit.lower == pytest.approx(-1.57)
    assert joint.limit.upper == pytest.approx(1.57)
    assert joint.limit.effort == pytest.approx(10.0)
    assert joint.limit.velocity == pytest.approx(1.0)


def test_joint_missing_name_or_type_is_an_error():
    with pytest.raises(UrdfParseError, match="missing name= or type="):
        parse_urdf_string(
            '<robot><link name="a"/><link name="b"/><joint type="fixed">'
            '<parent link="a"/><child link="b"/></joint></robot>'
        )
    with pytest.raises(UrdfParseError, match="missing name= or type="):
        parse_urdf_string(
            '<robot><link name="a"/><link name="b"/><joint name="j">'
            '<parent link="a"/><child link="b"/></joint></robot>'
        )


def test_joint_with_unknown_type_is_an_error_naming_the_valid_types():
    xml = (
        '<robot><link name="a"/><link name="b"/>'
        '<joint name="j" type="floating_saucer"><parent link="a"/><child link="b"/></joint></robot>'
    )
    with pytest.raises(UrdfParseError, match="unknown type 'floating_saucer'") as exc:
        parse_urdf_string(xml)
    # every real URDF joint type should be named in the error so the
    # operator knows what IS accepted, not just that this one wasn't.
    for real_type in JointType:
        assert real_type.value in str(exc.value)


def test_joint_missing_parent_or_child_element_is_an_error():
    with pytest.raises(UrdfParseError, match="missing <parent>/<child>"):
        parse_urdf_string(
            '<robot><link name="a"/><link name="b"/>'
            '<joint name="j" type="fixed"><child link="b"/></joint></robot>'
        )
    with pytest.raises(UrdfParseError, match="missing <parent>/<child>"):
        parse_urdf_string(
            '<robot><link name="a"/><link name="b"/>'
            '<joint name="j" type="fixed"><parent link="a"/></joint></robot>'
        )


def test_joint_parent_or_child_element_missing_link_attribute_is_an_error():
    with pytest.raises(UrdfParseError, match="no link= attribute"):
        parse_urdf_string(
            '<robot><link name="a"/><link name="b"/>'
            '<joint name="j" type="fixed"><parent/><child link="b"/></joint></robot>'
        )


def test_axis_defaults_to_x_when_absent():
    xml = '<robot><link name="a"/><link name="b"/><joint name="j" type="revolute"><parent link="a"/><child link="b"/></joint></robot>'
    robot = parse_urdf_string(xml)
    assert robot.joints["j"].axis == (1.0, 0.0, 0.0)


def test_joint_with_no_limit_element_has_none_limit():
    robot = parse_urdf_string(two_link_robot().replace('<limit lower="-1.57" upper="1.57" effort="10" velocity="1"/>', ""))
    assert robot.joints["j1"].limit is None


# --- origin/float parsing -------------------------------------------------


def test_origin_defaults_to_identity_when_absent():
    xml = '<robot><link name="a"/><link name="b"/><joint name="j" type="fixed"><parent link="a"/><child link="b"/></joint></robot>'
    robot = parse_urdf_string(xml)
    assert robot.joints["j"].origin.xyz == (0.0, 0.0, 0.0)
    assert robot.joints["j"].origin.rpy == (0.0, 0.0, 0.0)


def test_wrong_float_count_is_a_clear_error():
    xml = (
        '<robot><link name="a"/><link name="b"/>'
        '<joint name="j" type="fixed"><origin xyz="0 0"/><parent link="a"/><child link="b"/></joint></robot>'
    )
    with pytest.raises(UrdfParseError, match="Expected 3 numbers"):
        parse_urdf_string(xml)


def test_empty_xyz_attribute_falls_back_to_default():
    xml = (
        '<robot><link name="a"/><link name="b"/>'
        '<joint name="j" type="fixed"><origin xyz="" rpy="0 0 0"/><parent link="a"/><child link="b"/></joint></robot>'
    )
    robot = parse_urdf_string(xml)
    assert robot.joints["j"].origin.xyz == (0.0, 0.0, 0.0)


# --- geometry -------------------------------------------------------------


def link_with_visual_geometry(geometry_xml: str) -> str:
    return f'<robot><link name="a"><visual><geometry>{geometry_xml}</geometry></visual></link></robot>'


def test_box_geometry():
    robot = parse_urdf_string(link_with_visual_geometry('<box size="1 2 3"/>'))
    geom = robot.links["a"].visuals[0].geometry
    assert isinstance(geom, BoxGeometry)
    assert geom.size == (1.0, 2.0, 3.0)


def test_cylinder_geometry():
    robot = parse_urdf_string(link_with_visual_geometry('<cylinder radius="0.5" length="2"/>'))
    geom = robot.links["a"].visuals[0].geometry
    assert isinstance(geom, CylinderGeometry)
    assert geom.radius == pytest.approx(0.5)
    assert geom.length == pytest.approx(2.0)


def test_sphere_geometry():
    robot = parse_urdf_string(link_with_visual_geometry('<sphere radius="0.3"/>'))
    geom = robot.links["a"].visuals[0].geometry
    assert isinstance(geom, SphereGeometry)
    assert geom.radius == pytest.approx(0.3)


def test_mesh_geometry_keeps_filename_and_default_scale():
    robot = parse_urdf_string(link_with_visual_geometry('<mesh filename="package://pkg/meshes/link.stl"/>'))
    geom = robot.links["a"].visuals[0].geometry
    assert isinstance(geom, MeshGeometry)
    assert geom.filename == "package://pkg/meshes/link.stl"
    assert geom.scale == (1.0, 1.0, 1.0)


def test_missing_geometry_element_substitutes_a_small_placeholder_box():
    robot = parse_urdf_string('<robot><link name="a"><visual/></link></robot>')
    geom = robot.links["a"].visuals[0].geometry
    assert isinstance(geom, BoxGeometry)
    assert geom.size == (0.05, 0.05, 0.05)


def test_empty_geometry_element_also_substitutes_the_placeholder_box():
    robot = parse_urdf_string(link_with_visual_geometry(""))
    geom = robot.links["a"].visuals[0].geometry
    assert isinstance(geom, BoxGeometry)
    assert geom.size == (0.05, 0.05, 0.05)


# --- materials -------------------------------------------------------------


def test_inline_bare_color_material():
    xml = (
        '<robot><link name="a"><visual><geometry><box size="1 1 1"/></geometry>'
        '<material name="red"><color rgba="1 0 0 1"/></material></visual></link></robot>'
    )
    robot = parse_urdf_string(xml)
    material = robot.links["a"].visuals[0].material
    assert material.name == "red"
    assert material.rgba == (1.0, 0.0, 0.0, 1.0)


def test_material_name_reference_resolves_against_top_level_declaration():
    xml = (
        '<robot>'
        '<material name="blue"><color rgba="0 0 1 1"/></material>'
        '<link name="a"><visual><geometry><box size="1 1 1"/></geometry>'
        '<material name="blue"/></visual></link>'
        "</robot>"
    )
    robot = parse_urdf_string(xml)
    assert robot.materials["blue"].rgba == (0.0, 0.0, 1.0, 1.0)
    material = robot.links["a"].visuals[0].material
    assert material.rgba == (0.0, 0.0, 1.0, 1.0)


def test_material_reference_to_unknown_name_keeps_the_grey_default():
    xml = (
        '<robot><link name="a"><visual><geometry><box size="1 1 1"/></geometry>'
        '<material name="does-not-exist"/></visual></link></robot>'
    )
    robot = parse_urdf_string(xml)
    material = robot.links["a"].visuals[0].material
    assert material.name == "does-not-exist"
    assert material.rgba == (0.8, 0.8, 0.8, 1.0)


def test_visual_with_no_material_element_has_none_material():
    robot = parse_urdf_string(link_with_visual_geometry('<box size="1 1 1"/>'))
    assert robot.links["a"].visuals[0].material is None


# --- inertial -------------------------------------------------------------


def test_inertial_parsed_in_full():
    xml = (
        '<robot><link name="a"><inertial><origin xyz="0 0 0.1"/>'
        '<mass value="2.5"/><inertia ixx="0.1" ixy="0.01" ixz="0.02" iyy="0.2" iyz="0.03" izz="0.3"/>'
        "</inertial></link></robot>"
    )
    robot = parse_urdf_string(xml)
    inertial = robot.links["a"].inertial
    assert inertial.mass == pytest.approx(2.5)
    assert inertial.ixx == pytest.approx(0.1)
    assert inertial.izz == pytest.approx(0.3)
    assert inertial.origin.xyz == (0.0, 0.0, 0.1)


def test_link_without_inertial_element_has_none_inertial():
    robot = parse_urdf_string('<robot><link name="a"/></robot>')
    assert robot.links["a"].inertial is None


def test_negative_mass_is_parsed_through_unchanged():
    # This module's own job is a faithful parse - urdf/dof.py's own
    # validate() is what turns a real negative mass into a reported
    # problem (see test_dof.py), never this module silently correcting it.
    xml = '<robot><link name="a"><inertial><mass value="-1"/></inertial></link></robot>'
    robot = parse_urdf_string(xml)
    assert robot.links["a"].inertial.mass == pytest.approx(-1.0)


# --- xacro detection --------------------------------------------------------


def test_xacro_namespace_is_refused_with_a_clear_message():
    xml = '<robot name="r" xmlns:xacro="http://ros.org/wiki/xacro"><link name="a"/></robot>'
    with pytest.raises(UrdfParseError, match="xacro"):
        parse_urdf_string(xml)


def test_xacro_tag_is_refused_even_without_the_namespace_declared_first():
    xml = '<robot name="r"><xacro:property name="x" value="1"/><link name="a"/></robot>'
    # No xmlns:xacro in the first 2000 chars in this fixture, but
    # "<xacro:" is present - per parser.py's own condition, BOTH the
    # literal "xacro" substring AND ("xmlns:xacro" OR "<xacro:") must be
    # present for this to fire, and they are here.
    with pytest.raises(UrdfParseError, match="xacro"):
        parse_urdf_string(xml)


def test_plain_urdf_mentioning_the_word_xacro_in_a_comment_is_not_refused():
    # Sanity check on the heuristic's own precision: the word "xacro"
    # alone (e.g. in a comment) must NOT trip the guard without either
    # xmlns:xacro or a literal <xacro: tag alongside it.
    xml = '<robot name="r"><!-- ported from a xacro file --><link name="a"/></robot>'
    robot = parse_urdf_string(xml)
    assert robot.name == "r"


# --- file I/O ---------------------------------------------------------------


def test_parse_urdf_file_reads_a_real_file(tmp_path):
    path = tmp_path / "arm.urdf"
    path.write_text(two_link_robot(), encoding="utf-8")
    robot = parse_urdf_file(path)
    assert robot.name == "arm"
    assert "j1" in robot.joints


def test_parse_urdf_file_missing_path_is_a_clear_error(tmp_path):
    missing = tmp_path / "does-not-exist.urdf"
    with pytest.raises(UrdfParseError, match="Couldn't read"):
        parse_urdf_file(missing)
