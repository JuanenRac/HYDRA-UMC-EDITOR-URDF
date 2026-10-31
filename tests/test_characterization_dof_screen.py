# =============================================================================
# HYDRA-UMC EDITOR-URDF - tests/test_characterization_dof_screen.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# Characterization: what the DOF screen shows today, in the classic interface (DofPanel) and in the Qt Quick one (the
# bridge properties the QML reads), with the physical check off and on. These pin what must stay identical when the
# physical check is off (its default) and when it is on without its own panel.
# =============================================================================
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from hydra_editor_urdf import i18n
from hydra_editor_urdf.app import EditorController
from hydra_editor_urdf.urdf.dof import issue_lines
from qt_support import FEASIBLE_COHERENT, INCOHERENT, qt_app, set_config, write_urdf

ROOT = Path(__file__).resolve().parent.parent


def _items(panel) -> list[str]:
    lst = panel._issues_list
    return [lst.item(i).text() for i in range(lst.count())]


def test_classic_dof_screen_without_a_robot(monkeypatch, tmp_path) -> None:
    qt_app()
    set_config(monkeypatch, tmp_path)
    from hydra_editor_urdf.ui.panels.dof_panel import DofPanel

    panel = DofPanel(EditorController())
    assert panel._verdict_label.text() == i18n._("DOF_NO_ROBOT_LOADED")
    assert _items(panel) == []


def test_classic_dof_screen_lists_the_reasons_and_nothing_physical_when_off(monkeypatch, tmp_path) -> None:
    qt_app()
    set_config(monkeypatch, tmp_path)
    from hydra_editor_urdf.ui.panels.dof_panel import DofPanel

    controller = EditorController()
    panel = DofPanel(controller)
    controller.load_urdf_file(write_urdf(tmp_path, INCOHERENT))
    report = controller.dof_report
    assert report is not None and not report.is_feasible
    assert _items(panel) == issue_lines(report, i18n._("DOF_WARNING_PREFIX"), i18n._("DOF_NO_ISSUES"))
    assert report.warnings == []
    assert not any("[mass_not_positive]" in line for line in _items(panel))


def test_classic_dof_screen_of_a_coherent_robot_says_no_issues(monkeypatch, tmp_path) -> None:
    qt_app()
    set_config(monkeypatch, tmp_path)
    from hydra_editor_urdf.ui.panels.dof_panel import DofPanel

    controller = EditorController()
    panel = DofPanel(controller)
    controller.load_urdf_file(write_urdf(tmp_path, FEASIBLE_COHERENT))
    assert _items(panel) == [i18n._("DOF_NO_ISSUES")]


def test_classic_dof_screen_carries_the_physical_warnings_when_the_switch_is_on(monkeypatch, tmp_path) -> None:
    qt_app()
    set_config(monkeypatch, tmp_path, physical_check=True)
    from hydra_editor_urdf.ui.panels.dof_panel import DofPanel

    controller = EditorController()
    panel = DofPanel(controller)
    controller.load_urdf_file(write_urdf(tmp_path, INCOHERENT))
    lines = _items(panel)
    prefix = i18n._("DOF_WARNING_PREFIX")
    physical = [line for line in lines if "[mass_not_positive]" in line]
    assert len(physical) == 1 and physical[0].startswith(prefix)
    assert lines == issue_lines(controller.dof_report, prefix, i18n._("DOF_NO_ISSUES"))


def test_a_physical_warning_never_changes_the_verdict(monkeypatch, tmp_path) -> None:
    set_config(monkeypatch, tmp_path)
    off = EditorController()
    off.load_urdf_file(write_urdf(tmp_path, INCOHERENT))
    set_config(monkeypatch, tmp_path, physical_check=True)
    on = EditorController()
    on.load_urdf_file(write_urdf(tmp_path, INCOHERENT))
    assert off.dof_report is not None and on.dof_report is not None
    assert (off.dof_report.is_feasible, off.dof_report.dof_count, off.dof_report.reasons) == (
        on.dof_report.is_feasible,
        on.dof_report.dof_count,
        on.dof_report.reasons,
    )


def _bridge(controller: EditorController):
    qt_app()
    pytest.importorskip("OpenGL", reason="the Qt Quick bridge imports the 3D renderer")
    sys.path.insert(0, str(ROOT))
    from qt_editor_urdf import EditorQtBridge

    return EditorQtBridge(controller)


def test_qt_quick_dof_properties_follow_the_report(monkeypatch, tmp_path) -> None:
    set_config(monkeypatch, tmp_path)
    controller = EditorController()
    bridge = _bridge(controller)
    assert bridge.dofHasRobot is False
    assert bridge.dofVerdictText == i18n._("DOF_NO_ROBOT_LOADED")
    assert bridge.dofIssues == []
    controller.load_urdf_file(write_urdf(tmp_path, INCOHERENT))
    assert bridge.dofHasRobot is True and bridge.dofFeasible is False
    assert bridge.dofIssues == issue_lines(controller.dof_report, i18n._("DOF_WARNING_PREFIX"), i18n._("DOF_NO_ISSUES"))
    assert not any("[mass_not_positive]" in line for line in bridge.dofIssues)


def test_qt_quick_dof_issues_carry_the_physical_warnings_when_on(monkeypatch, tmp_path) -> None:
    set_config(monkeypatch, tmp_path, physical_check=True)
    controller = EditorController()
    bridge = _bridge(controller)
    controller.load_urdf_file(write_urdf(tmp_path, INCOHERENT))
    assert any("[mass_not_positive]" in line for line in bridge.dofIssues)


def test_the_classic_window_has_exactly_the_five_docks_today(monkeypatch, tmp_path) -> None:
    qt_app()
    set_config(monkeypatch, tmp_path)
    from PySide6.QtWidgets import QDockWidget

    try:
        from hydra_editor_urdf.ui.main_window import MainWindow

        window = MainWindow()
    except Exception as exc:  # pragma: no cover - the 3D view needs a working OpenGL stack
        pytest.skip(f"the main window cannot be created here: {exc}")
    names = sorted(d.objectName() for d in window.findChildren(QDockWidget))
    assert len(names) == 5
    assert set(window._deck_docks) == {"source", "dof", "viewport", "properties", "upload"}
    window.close()
