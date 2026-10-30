# =============================================================================
# HYDRA-UMC EDITOR-URDF - tests/test_dropped_elements.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# What a URDF has that this editor does not keep is reported when the file is read (so a save or a push does not drop it silently),
# and a joint that follows another (<mimic>) is not counted as a degree of freedom.
# =============================================================================
from __future__ import annotations

import xml.etree.ElementTree as ET

from hydra_editor_urdf.urdf.dof import validate
from hydra_editor_urdf.urdf.parser import find_dropped_elements, parse_urdf_string
from hydra_editor_urdf.urdf.writer import robot_to_urdf_string

ARM = """<robot name="arm">
  <link name="base"/>
  <link name="l1"/><link name="l2"/><link name="l3"/><link name="l4"/><link name="l5"/><link name="l6"/>
  {joints}
  {extra}
</robot>"""


def joint(index: int, inside: str = "") -> str:
    return (
        f'<joint name="j{index}" type="revolute"><parent link="{"base" if index == 1 else f"l{index - 1}"}"/><child link="l{index}"/>'
        f'<axis xyz="0 0 1"/><limit lower="-1" upper="1" effort="5" velocity="1"/>{inside}</joint>'
    )


def arm(joints: str, extra: str = "") -> str:
    return ARM.format(joints=joints, extra=extra)


def test_a_plain_urdf_drops_nothing():
    robot = parse_urdf_string(arm("".join(joint(i) for i in range(1, 7))))
    assert robot.dropped_elements == {}
    assert not [w for w in validate(robot).warnings if "does not keep" in w]


def test_the_elements_the_model_has_no_place_for_are_counted_by_where_they_are():
    extra = '<transmission name="t1"><type>x</type></transmission><gazebo reference="l1"><material>Gazebo/Red</material></gazebo><gazebo/>'
    joints = joint(1, '<dynamics damping="0.1"/><safety_controller soft_lower_limit="-0.9" soft_upper_limit="0.9"/>') + "".join(joint(i) for i in range(2, 7))
    robot = parse_urdf_string(arm(joints, extra))
    assert robot.dropped_elements == {
        "<transmission>": 1,
        "<gazebo>": 2,
        "<joint><dynamics>": 1,
        "<joint><safety_controller>": 1,
    }


def test_things_inside_a_visual_and_a_material_are_counted_too():
    text = """<robot name="r"><link name="a"><visual><geometry><box size="1 1 1"/></geometry><material name="m"><color rgba="1 0 0 1"/><texture filename="x.png"/></material><verbose/></visual>
        <self_collision_checking><sphere/></self_collision_checking></link></robot>"""
    dropped = find_dropped_elements(ET.fromstring(text))
    assert dropped == {"<link><visual><verbose>": 1, "<link><self_collision_checking>": 1}


def test_the_warnings_of_the_dof_report_say_what_the_file_has_that_is_left_out():
    robot = parse_urdf_string(arm("".join(joint(i) for i in range(1, 7)), "<transmission name='t'/>"))
    warnings = validate(robot).warnings
    assert any("1 <transmission> element(s)" in w and "leaves them out" in w for w in warnings), warnings


def test_a_follower_is_not_a_degree_of_freedom():
    # six revolute joints, the sixth follows the fifth: five DOF
    joints = "".join(joint(i) for i in range(1, 6)) + joint(6, '<mimic joint="j5" multiplier="1"/>')
    robot = parse_urdf_string(arm(joints))
    report = validate(robot)
    assert report.dof_count == 5
    assert "j6" not in report.movable_joint_names and report.follower_joint_names == ["j6"]
    assert any("j6" in w and "follows 'j5'" in w and "not counted" in w for w in report.warnings)
    # the mimic itself is not repeated as a "dropped element" line
    assert not any("<joint><mimic>" in w for w in report.warnings)


def test_a_follower_does_not_turn_a_five_dof_arm_into_a_feasible_six():
    joints = "".join(joint(i) for i in range(1, 6)) + joint(6, '<mimic joint="j1"/>')
    no_follower = parse_urdf_string(arm("".join(joint(i) for i in range(1, 6))))
    assert validate(parse_urdf_string(arm(joints))).dof_count == validate(no_follower).dof_count == 5


def test_a_follower_still_needs_its_own_limit():
    bad = joint(6, '<mimic joint="j1"/>').replace('<limit lower="-1" upper="1" effort="5" velocity="1"/>', "")
    report = validate(parse_urdf_string(arm("".join(joint(i) for i in range(1, 6)) + bad)))
    assert any("j6" in reason and "no <limit>" in reason for reason in report.reasons)


def test_saving_leaves_the_dropped_elements_out_as_the_warning_says():
    robot = parse_urdf_string(arm("".join(joint(i) for i in range(1, 7)), "<transmission name='t'/>"))
    written = robot_to_urdf_string(robot)
    assert "transmission" not in written


# ---- keeping the elements the model has no field for

def test_the_unsupported_elements_are_left_out_by_default_and_written_back_on_request():
    inside = '<dynamics damping="0.5" friction="0.1"/><safety_controller k_velocity="3"/>'
    extra = '<transmission name="t1"><joint name="j1"/></transmission><gazebo reference="l1"><material>Gazebo/Red</material></gazebo>'
    robot = parse_urdf_string(arm("".join(joint(i, inside if i == 1 else "") for i in range(1, 7)), extra))
    assert len(robot.joints["j1"].extra_xml) == 2 and len(robot.extra_xml) == 2

    plain = robot_to_urdf_string(robot)
    assert "dynamics" not in plain and "transmission" not in plain and "gazebo" not in plain

    kept = robot_to_urdf_string(robot, keep_unsupported=True)
    again = parse_urdf_string(kept)
    assert again.dropped_elements == robot.dropped_elements
    assert 'damping="0.5"' in kept and "<safety_controller" in kept and "Gazebo/Red" in kept
    # and a second round trip changes nothing
    assert robot_to_urdf_string(again, keep_unsupported=True) == kept


def test_a_mimic_keeps_its_multiplier_and_offset_when_kept():
    robot = parse_urdf_string(arm("".join(joint(i, '<mimic joint="j1" multiplier="2" offset="0.1"/>' if i == 2 else "") for i in range(1, 7))))
    kept = robot_to_urdf_string(robot, keep_unsupported=True)
    assert 'multiplier="2"' in kept and 'offset="0.1"' in kept
    assert "multiplier" not in robot_to_urdf_string(robot)


def test_an_element_that_names_a_joint_that_was_deleted_is_not_written_back():
    robot = parse_urdf_string(arm("".join(joint(i) for i in range(1, 7)), '<transmission name="t6"><joint name="j6"/></transmission>'))
    del robot.joints["j6"]
    assert "transmission" not in robot_to_urdf_string(robot, keep_unsupported=True)
