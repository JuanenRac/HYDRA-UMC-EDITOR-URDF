# =============================================================================
# HYDRA-UMC-EDITOR-URDF - pre-save check tests
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
import tempfile
from pathlib import Path

import pytest

from hydra_editor_urdf.app import EditorController
from hydra_editor_urdf.models import (
    BoxGeometry,
    CylinderGeometry,
    Joint,
    JointLimit,
    JointType,
    Link,
    MeshGeometry,
    Robot,
    SphereGeometry,
    Visual,
)
from hydra_editor_urdf.urdf.save_check import UrdfSaveError, check_before_save


def _robot(**joint_overrides):
    joint = Joint("j1", JointType.REVOLUTE, "base", "arm", axis=(0.0, 0.0, 1.0), limit=JointLimit(-1.0, 1.0, 10.0, 2.0))
    for key, value in joint_overrides.items():
        setattr(joint, key, value)
    return Robot(
        name="r",
        links={"base": Link("base", visuals=[Visual(geometry=BoxGeometry((1.0, 1.0, 1.0)))]), "arm": Link("arm")},
        joints={"j1": joint},
    )


def test_a_sound_robot_has_no_issues():
    assert check_before_save(_robot()) == []


def test_limits_must_be_ordered_finite_and_non_negative():
    assert any("above upper" in i for i in check_before_save(_robot(limit=JointLimit(2.0, 1.0, 1.0, 1.0))))
    assert any("finite" in i for i in check_before_save(_robot(limit=JointLimit(float("nan"), 1.0, 1.0, 1.0))))
    assert any("negative" in i for i in check_before_save(_robot(limit=JointLimit(-1.0, 1.0, -5.0, 1.0))))
    assert any("needs a limit" in i for i in check_before_save(_robot(limit=None)))


def test_a_zero_or_non_finite_axis_is_refused_only_for_movable_joints():
    assert any("not a direction" in i for i in check_before_save(_robot(axis=(0.0, 0.0, 0.0))))
    assert any("not a direction" in i for i in check_before_save(_robot(axis=(float("inf"), 0.0, 0.0))))
    assert check_before_save(_robot(type=JointType.FIXED, axis=(0.0, 0.0, 0.0), limit=None)) == []


@pytest.mark.parametrize(
    "geometry",
    [BoxGeometry((1.0, 0.0, 1.0)), CylinderGeometry(-1.0, 1.0), SphereGeometry(float("nan")), MeshGeometry("", (1.0, 1.0, 1.0)), MeshGeometry("m.stl", (0.0, 1.0, 1.0))],
)
def test_bad_geometry_is_reported(geometry):
    robot = _robot()
    robot.links["arm"].visuals.append(Visual(geometry=geometry))
    assert check_before_save(robot), geometry


def test_a_missing_mesh_file_is_reported_and_a_present_one_is_not():
    robot = _robot()
    robot.links["arm"].visuals.append(Visual(geometry=MeshGeometry("parts/arm.stl", (1.0, 1.0, 1.0))))
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        assert any("was not found" in i for i in check_before_save(robot, root))
        (root / "parts").mkdir()
        (root / "parts" / "arm.stl").write_bytes(b"x")
        assert check_before_save(robot, root) == []
    assert check_before_save(robot) == []  # no mesh root known: not checked


def test_export_refuses_an_invalid_robot_and_writes_nothing():
    controller = EditorController()
    controller.robot = _robot(limit=JointLimit(2.0, 1.0, 1.0, 1.0))
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "out.urdf"
        with pytest.raises(UrdfSaveError) as caught:
            controller.export_urdf_file(target)
        assert caught.value.issues
        assert not target.exists()


def test_export_of_a_sound_robot_still_works():
    controller = EditorController()
    controller.robot = _robot()
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "out.urdf"
        controller.export_urdf_file(target)
        assert "<robot" in target.read_text(encoding="utf-8")
