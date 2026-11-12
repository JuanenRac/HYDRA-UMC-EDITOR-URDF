# =============================================================================
# HYDRA-UMC EDITOR-URDF - tests/test_gizmo_edit.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# Dragging the gizmo of the 3D view moves the origin of a joint: the preview changes the robot at once, the whole
# drag is ONE step of the undo stack, a drag that goes nowhere pushes nothing, and the name of the step exists in
# the eight languages. The robot is built from text; no window is opened.
# =============================================================================
from __future__ import annotations

from pathlib import Path

import pytest

from tests.qt_support import qt_app

ROBOT = """<robot name="r">
  <link name="a"/>
  <link name="b"/>
  <joint name="j" type="fixed"><parent link="a"/><child link="b"/><origin xyz="0.1 0 0" rpy="0 0 0.5"/></joint>
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


def test_a_whole_drag_is_one_undo_step(controller) -> None:
    joint = controller.robot.joints["j"]
    controller.begin_origin_drag()
    for x in (0.2, 0.3, 0.4):
        assert controller.preview_joint_origin("j", (x, 0.0, 0.0))
    assert joint.origin.xyz == (0.4, 0.0, 0.0)
    assert controller.undo_stack.count() == 0  # nothing is pushed while the drag goes on

    assert controller.finish_origin_drag()
    assert controller.undo_stack.count() == 1

    controller.undo_stack.undo()
    assert controller.robot.joints["j"].origin.xyz == (0.1, 0.0, 0.0)
    controller.undo_stack.redo()
    assert controller.robot.joints["j"].origin.xyz == (0.4, 0.0, 0.0)


def test_the_drag_keeps_the_rotation_of_the_origin(controller) -> None:
    controller.begin_origin_drag()
    controller.preview_joint_origin("j", (0.5, 0.5, 0.5))
    assert controller.robot.joints["j"].origin.rpy == (0.0, 0.0, 0.5)


def test_a_drag_that_ends_where_it_began_pushes_nothing(controller) -> None:
    controller.begin_origin_drag()
    controller.preview_joint_origin("j", (0.3, 0.0, 0.0))
    controller.preview_joint_origin("j", (0.1, 0.0, 0.0))
    assert controller.finish_origin_drag() is False
    assert controller.undo_stack.count() == 0


def test_an_unknown_joint_or_a_finish_without_begin_changes_nothing(controller) -> None:
    assert controller.preview_joint_origin("nope", (1.0, 1.0, 1.0)) is False
    assert controller.finish_origin_drag() is False
    assert controller.undo_stack.count() == 0


def test_the_step_is_named_in_every_language(controller) -> None:
    controller.begin_origin_drag()
    controller.preview_joint_origin("j", (0.9, 0.0, 0.0))
    controller.finish_origin_drag()
    assert controller.undo_stack.undoText() not in ("", "EDIT_GIZMO_MOVE")
    for path in sorted(LANGUAGE_DIR.glob("*.lng")):
        assert any(line.startswith("EDIT_GIZMO_MOVE=") for line in path.read_text(encoding="utf-8").splitlines()), path.name


def test_the_renderer_picks_and_drags_an_axis_without_a_gpu(controller) -> None:
    """The renderer keeps all its GL calls to drawing: picking and dragging run on the camera maths alone."""
    import numpy as np

    from hydra_editor_urdf.render import gizmo
    pytest.importorskip("OpenGL")  # the renderer module imports PyOpenGL; CI has only the core requirements
    from hydra_editor_urdf.render.viewport import UrdfGLRenderer

    renderer = UrdfGLRenderer(lambda: None, lambda: None, lambda name: None)
    renderer._robot = controller.robot
    renderer._selected_link = "b"
    renderer._width = renderer._height = 400
    events: list[tuple] = []
    renderer.gizmo_listener = lambda phase, name, xyz: events.append((phase, name, xyz))

    joint, parent, origin = renderer._gizmo_context()
    assert joint.name == "j"
    view, proj = renderer._view_projection()
    length = renderer._gizmo_length()
    # The pixel of a point halfway along the world X axis of the gizmo.
    clip = proj.astype(np.float64) @ view.astype(np.float64) @ np.append(origin + gizmo.AXIS_DIRECTIONS[0] * length / 2, 1.0)
    ndc = clip[:3] / clip[3]
    x, y = (ndc[0] + 1.0) * 200, (1.0 - ndc[1]) * 200

    assert renderer.gizmo_press(x, y)
    assert renderer.gizmo_dragging and events[0][0] == "begin"
    renderer.gizmo_move(x + 10, y)
    assert events[-1][0] == "move" and events[-1][2] != events[0][2]
    assert renderer.gizmo_release() and events[-1][0] == "end" and not renderer.gizmo_dragging


def test_the_root_link_has_no_gizmo(controller) -> None:
    pytest.importorskip("OpenGL")  # the renderer module imports PyOpenGL; CI has only the core requirements
    from hydra_editor_urdf.render.viewport import UrdfGLRenderer

    renderer = UrdfGLRenderer(lambda: None, lambda: None, lambda name: None)
    renderer._robot = controller.robot
    renderer._selected_link = "a"
    assert renderer._gizmo_context() is None
    assert renderer.gizmo_press(10, 10) is False
