# =============================================================================
# HYDRA-UMC EDITOR-URDF - tests/test_characterization_physical.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# Characterization: what the editor does today with a model that is not physically coherent. These pin the behaviour
# that must not change when the physical check is off (its default).
# =============================================================================
from __future__ import annotations

from pathlib import Path

import pytest

from hydra_editor_urdf.urdf.dof import validate
from hydra_editor_urdf.urdf.parser import UrdfParseError, parse_urdf_string

ROOT = Path(__file__).resolve().parent.parent

INCOHERENT = """<robot name="r">
  <link name="a"><inertial><mass value="-1"/><inertia ixx="1" iyy="1" izz="9" ixy="0" ixz="0" iyz="0"/></inertial></link>
  <link name="b"/>
  <joint name="j" type="revolute"><parent link="a"/><child link="b"/><axis xyz="0 0 2"/>
    <limit lower="2" upper="1" effort="-1" velocity="0"/></joint>
</robot>"""

COHERENT = """<robot name="r">
  <link name="a"><inertial><mass value="1"/><inertia ixx="1" iyy="1" izz="1" ixy="0" ixz="0" iyz="0"/></inertial></link>
  <link name="b"/>
  <joint name="j" type="revolute"><parent link="a"/><child link="b"/><axis xyz="0 0 1"/>
    <limit lower="-1" upper="1" effort="5" velocity="2"/></joint>
</robot>"""


def test_negative_mass_and_inverted_limits_are_reasons_today() -> None:
    report = validate(parse_urdf_string(INCOHERENT))
    text = " ".join(report.reasons)
    assert "lower (2.0) is greater than upper (1.0)" in text
    assert "negative <inertial><mass>" in text
    assert report.warnings == []


def test_axis_is_normalised_by_the_parser() -> None:
    assert parse_urdf_string(INCOHERENT).joints["j"].axis == (0.0, 0.0, 1.0)


def test_a_coherent_robot_has_no_warnings_today() -> None:
    assert validate(parse_urdf_string(COHERENT)).warnings == []


def test_duplicate_names_are_refused_by_the_parser() -> None:
    with pytest.raises(UrdfParseError, match="Duplicate <link"):
        parse_urdf_string('<robot name="r"><link name="a"/><link name="a"/></robot>')
    with pytest.raises(UrdfParseError, match="Duplicate <joint"):
        parse_urdf_string(
            '<robot name="r"><link name="a"/><link name="b"/>'
            '<joint name="j" type="fixed"><parent link="a"/><child link="b"/></joint>'
            '<joint name="j" type="fixed"><parent link="a"/><child link="b"/></joint></robot>'
        )


def test_zero_axis_of_a_movable_joint_is_refused_by_the_parser() -> None:
    bad = COHERENT.replace('xyz="0 0 1"', 'xyz="0 0 0"')
    with pytest.raises(UrdfParseError, match="no direction"):
        parse_urdf_string(bad)


def test_the_physical_check_is_off_by_default_and_changes_nothing_of_the_report() -> None:
    from hydra_editor_urdf.app import EditorController

    assert EditorController._switch("physical_check") is False
    robot = parse_urdf_string(INCOHERENT)
    assert EditorController()._report(robot).warnings == []
