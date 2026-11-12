# =============================================================================
# HYDRA-UMC EDITOR-URDF - tests/test_undo_redo.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# Undo and redo of the edits of the properties panel: every edit is one step of the undo stack of the controller, undo puts the
# robot back as it was, redo applies the edit again, shared materials stay shared, a new robot starts a fresh stack, and the menu
# has the actions in every language. The robot is built from text; nothing is read from or written to a real file.
# =============================================================================
from __future__ import annotations

from pathlib import Path

import pytest

from tests.qt_support import qt_app

ROBOT = """<robot name="r">
  <material name="shared"><color rgba="1 0 0 1"/></material>
  <link name="a"><visual><geometry><box size="1 1 1"/></geometry><material name="shared"/></visual></link>
  <link name="b"><visual><geometry><mesh filename="m.stl" scale="1 1 1"/></geometry><material name="shared"/></visual></link>
  <joint name="j" type="revolute"><parent link="a"/><child link="b"/><axis xyz="0 0 1"/>
    <limit lower="-1" upper="1" effort="5" velocity="2"/></joint>
</robot>"""

LANGUAGE_DIR = Path(__file__).resolve().parent.parent / "language"


@pytest.fixture()
def controller():
    qt_app()
    from hydra_editor_urdf.app import EditorController
    from hydra_editor_urdf.urdf.parser import parse_urdf_string

    c = EditorController()
    c.robot = parse_urdf_string(ROBOT)
    c.dof_report = c._report(c.robot)
    return c


def test_an_edit_is_one_step_that_undo_and_redo_walk(controller) -> None:
    robot = controller.robot
    assert controller.edit("Joint", lambda: setattr(robot.joints["j"], "type", robot.joints["j"].type.__class__.FIXED))
    assert controller.undo_stack.count() == 1 and controller.undo_stack.undoText() == "Joint"
    assert robot.joints["j"].type.value == "fixed"
    controller.undo_stack.undo()
    assert robot.joints["j"].type.value == "revolute" and robot.joints["j"].limit is not None
    controller.undo_stack.redo()
    assert robot.joints["j"].type.value == "fixed"


def test_the_robot_object_stays_the_same_one_after_undo(controller) -> None:
    robot = controller.robot
    controller.edit("Name", lambda: setattr(robot, "name", "other"))
    controller.undo_stack.undo()
    assert controller.robot is robot and robot.name == "r"


def test_an_edit_that_changes_nothing_is_not_put_on_the_stack(controller) -> None:
    assert controller.edit("Nothing", lambda: None) is False
    assert controller.undo_stack.count() == 0


def test_there_is_nothing_to_edit_without_a_robot() -> None:
    qt_app()
    from hydra_editor_urdf.app import EditorController

    c = EditorController()
    assert c.edit("x", lambda: pytest.fail("must not run")) is False
    assert c.undo_stack.count() == 0


def test_a_material_shared_by_two_links_is_still_shared_after_undo_and_redo(controller) -> None:
    robot = controller.robot

    def recolor() -> None:
        robot.links["a"].visuals[0].material.rgba = (0.0, 1.0, 0.0, 1.0)

    controller.edit("Color", recolor)
    assert robot.links["b"].visuals[0].material.rgba == (0.0, 1.0, 0.0, 1.0)
    controller.undo_stack.undo()
    assert robot.links["a"].visuals[0].material is robot.links["b"].visuals[0].material
    assert robot.links["b"].visuals[0].material.rgba == (1.0, 0.0, 0.0, 1.0)
    controller.undo_stack.redo()
    assert robot.links["a"].visuals[0].material is robot.links["b"].visuals[0].material
    assert robot.links["a"].visuals[0].material.rgba == (0.0, 1.0, 0.0, 1.0)


def test_undo_tells_the_panels_with_the_tree_signal_and_the_selection_again(controller) -> None:
    seen: list[str] = []
    controller.tree_changed.connect(lambda: seen.append("tree"))
    controller.selected_link_changed.connect(lambda name: seen.append(f"select:{name}"))
    controller.set_selected_link("b")
    seen.clear()
    robot = controller.robot
    controller.edit("Scale", lambda: setattr(robot.links["b"].visuals[0].geometry, "scale", (2.0, 2.0, 2.0)))
    assert seen == ["tree"]
    seen.clear()
    controller.undo_stack.undo()
    assert seen == ["tree", "select:b"]
    assert robot.links["b"].visuals[0].geometry.scale == (1.0, 1.0, 1.0)


def test_the_dof_report_is_computed_again_after_undo(controller) -> None:
    robot = controller.robot
    before = controller.dof_report.dof_count
    controller.edit("Joint", lambda: setattr(robot.joints["j"], "type", robot.joints["j"].type.__class__.FIXED))
    assert controller.dof_report.dof_count == before - 1
    controller.undo_stack.undo()
    assert controller.dof_report.dof_count == before


def test_loading_a_robot_starts_a_fresh_stack(controller, tmp_path) -> None:
    robot = controller.robot
    controller.edit("Name", lambda: setattr(robot, "name", "other"))
    assert controller.undo_stack.canUndo()
    path = tmp_path / "r.urdf"
    path.write_text(ROBOT.replace("m.stl", "m2.stl"), encoding="utf-8")
    controller.load_urdf_file(path)
    assert controller.undo_stack.count() == 0 and not controller.undo_stack.canUndo()


def test_the_stack_keeps_at_most_the_limit_of_edits(controller) -> None:
    from hydra_editor_urdf.app import UNDO_LIMIT

    robot = controller.robot
    for i in range(UNDO_LIMIT + 5):
        controller.edit("Name", lambda i=i: setattr(robot, "name", f"n{i}"))
    assert controller.undo_stack.count() == UNDO_LIMIT


def test_a_new_edit_after_undo_drops_the_redo_branch(controller) -> None:
    robot = controller.robot
    controller.edit("A", lambda: setattr(robot, "name", "a"))
    controller.edit("B", lambda: setattr(robot, "name", "b"))
    controller.undo_stack.undo()
    controller.edit("C", lambda: setattr(robot, "name", "c"))
    assert not controller.undo_stack.canRedo() and controller.undo_stack.count() == 2


def test_the_inertial_apply_of_the_panel_can_be_undone(controller) -> None:
    from hydra_editor_urdf.ui.panels.properties_panel import PropertiesPanel

    panel = PropertiesPanel(controller)
    panel._on_robot_loaded(controller.robot)
    controller.set_selected_link("a")
    panel._inertial_mass.setValue(3.0)
    panel._inertial_ixx.setValue(0.5)
    panel._on_apply_inertial()
    assert controller.robot.links["a"].inertial.mass == 3.0
    controller.undo_stack.undo()
    assert controller.robot.links["a"].inertial is None
    controller.undo_stack.redo()
    assert controller.robot.links["a"].inertial.ixx == 0.5


def test_the_scale_and_joint_apply_of_the_panel_can_be_undone(controller) -> None:
    from hydra_editor_urdf.models import JointType
    from hydra_editor_urdf.ui.panels.properties_panel import PropertiesPanel

    panel = PropertiesPanel(controller)
    panel._on_robot_loaded(controller.robot)
    controller.set_selected_link("b")
    panel._scale_row.spins[0].setValue(2.0)
    panel._on_apply_scale()
    assert controller.robot.links["b"].visuals[0].geometry.scale[0] == 2.0
    panel._joint_type_combo.setCurrentIndex(panel._joint_type_combo.findData(JointType.FIXED))
    panel._on_apply_joint()
    assert controller.robot.joints["j"].type is JointType.FIXED and controller.robot.joints["j"].limit is None
    assert controller.undo_stack.count() == 2
    controller.undo_stack.undo()
    assert controller.robot.joints["j"].limit is not None and controller.robot.joints["j"].type is JointType.REVOLUTE
    controller.undo_stack.undo()
    assert controller.robot.links["b"].visuals[0].geometry.scale == (1.0, 1.0, 1.0)


def test_the_menu_has_undo_and_redo_with_the_standard_shortcuts(controller) -> None:
    from PySide6.QtGui import QKeySequence

    from hydra_editor_urdf.ui.main_window import MainWindow

    window = MainWindow()
    controller = window.controller
    from hydra_editor_urdf.urdf.parser import parse_urdf_string

    controller.robot = parse_urdf_string(ROBOT)
    assert window._undo_action.shortcut() == QKeySequence(QKeySequence.StandardKey.Undo)
    assert window._redo_action.shortcut() == QKeySequence(QKeySequence.StandardKey.Redo)
    assert not window._undo_action.isEnabled()
    robot = controller.robot
    controller.edit("Name", lambda: setattr(robot, "name", "x"))
    assert window._undo_action.isEnabled() and "Name" in window._undo_action.text()


@pytest.mark.parametrize("language", ["english", "spanish", "german", "french", "italian", "japanese", "chinese", "portuguese"])
def test_every_language_has_the_edit_texts(language: str) -> None:
    keys = {}
    for line in (LANGUAGE_DIR / f"{language}.lng").read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            keys[k] = v
    for name in ("MENU_EDIT", "EDIT_UNDO", "EDIT_REDO", "EDIT_COLOR", "EDIT_SCALE", "EDIT_JOINT", "EDIT_INERTIAL"):
        assert keys.get(name), f"{language}: {name}"
