# =============================================================================
# HYDRA-UMC EDITOR-URDF - tests/test_physical_panel.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The "Physical validation" panel: the rows, filters, order and JSON (urdf/physical_view.py, no Qt), the classic panel
# (offscreen Qt widgets) and the Qt Quick bridge and deck. With the switch off nothing of it exists; it is read-only.
# =============================================================================
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest
from qt_support import FEASIBLE_COHERENT, MULTI_ISSUES, qt_app, set_config, write_urdf

from hydra_editor_urdf import i18n
from hydra_editor_urdf.app import EditorController
from hydra_editor_urdf.urdf.parser import parse_urdf_string
from hydra_editor_urdf.urdf.physical_check import RULES, PhysicalWarning, check_robot
from hydra_editor_urdf.urdf.physical_view import (
    SEVERITIES,
    SEVERITY_OF_RULE,
    build_rows,
    counts_by_severity,
    filter_rows,
    rows_to_json,
    rules_present,
    severity_of,
    sort_rows,
)
from hydra_editor_urdf.urdf.writer import robot_to_urdf_string

ROOT = Path(__file__).resolve().parent.parent
LANGUAGES = ("english", "spanish", "german", "french", "italian", "japanese", "chinese", "portuguese")
NEW_KEYS = (
    "PHYS_PANEL_TITLE PHYS_PANEL_INTRO PHYS_PANEL_NO_ROBOT PHYS_PANEL_EMPTY PHYS_PANEL_NO_MATCH PHYS_COUNT "
    "PHYS_SEV_error PHYS_SEV_warning PHYS_SEV_hint PHYS_FILTER_SEVERITY PHYS_FILTER_RULE PHYS_FILTER_ELEMENT "
    "PHYS_FILTER_ALL PHYS_SORT_BY PHYS_COL_SEVERITY PHYS_COL_RULE PHYS_COL_ELEMENT PHYS_COL_VALUE PHYS_COL_LIMIT "
    "PHYS_COL_SUGGESTION PHYS_RECHECK PHYS_COPY_JSON PHYS_EXPORT_JSON PHYS_COPIED PHYS_EXPORTED PHYS_EXPORT_FAILED"
).split()


def _rows(text: str = MULTI_ISSUES):
    return build_rows(check_robot(parse_urdf_string(text)), i18n._)


# --- the view model, without Qt -------------------------------------------------------------------------------------


def test_every_rule_has_a_known_severity() -> None:
    assert set(SEVERITY_OF_RULE) == set(RULES)
    assert set(SEVERITY_OF_RULE.values()) <= set(SEVERITIES)
    assert severity_of("a_rule_from_the_future") == "warning"  # never hidden


def test_rows_carry_rule_element_value_limit_and_suggestion() -> None:
    rows = _rows()
    assert [(r.rule, r.severity) for r in rows] == [
        ("mass_not_positive", "error"),
        ("limit_missing", "warning"),
        ("units_length", "hint"),
    ]
    first = rows[0]
    assert (first.element, first.value, first.limit, first.fix) == ("link:l0", "0", "> 0", "0.001")
    assert first.what == i18n._("PHYS_R_mass_not_positive")
    assert first.suggestion == i18n._("PHYS_F_mass_not_positive", fix="0.001", value="0", limit="> 0")
    assert counts_by_severity(rows) == {"error": 1, "warning": 1, "hint": 1}


def test_filters_by_severity_rule_and_element() -> None:
    rows = _rows()
    assert [r.rule for r in filter_rows(rows)] == [r.rule for r in rows]
    assert [r.rule for r in filter_rows(rows, severity="hint")] == ["units_length"]
    assert [r.rule for r in filter_rows(rows, rule="limit_missing")] == ["limit_missing"]
    assert [r.rule for r in filter_rows(rows, element="  JOINT:")] == ["limit_missing", "units_length"]
    assert [r.rule for r in filter_rows(rows, element="j2")] == ["units_length"]
    assert filter_rows(rows, severity="error", rule="units_length") == []
    assert filter_rows(rows, element="nothing here") == []
    assert rules_present(rows) == ["mass_not_positive", "limit_missing", "units_length"]


def test_sorting_is_deterministic_and_does_not_lose_rows() -> None:
    rows = _rows()
    assert [r.severity for r in sort_rows(rows, "severity")] == ["error", "warning", "hint"]
    assert [r.severity for r in sort_rows(rows, "severity", descending=True)] == ["hint", "warning", "error"]
    assert [r.rule for r in sort_rows(rows, "rule")] == ["mass_not_positive", "limit_missing", "units_length"]
    assert [r.element for r in sort_rows(rows, "element")] == ["joint:j1", "joint:j2", "link:l0"]
    assert sort_rows(rows, "unknown") == rows
    shuffled = [rows[2], rows[0], rows[1]]
    assert sorted(map(id, sort_rows(shuffled, "element"))) == sorted(map(id, rows))
    assert sort_rows(rows, "element") == sort_rows(list(reversed(rows)), "element")


def test_json_has_fixed_keys_and_is_the_same_text_each_time() -> None:
    rows = _rows()
    text = rows_to_json(rows)
    assert text == rows_to_json(_rows())
    data = json.loads(text)
    assert [list(item) for item in data] == [["severity", "rule", "element", "value", "limit", "message", "suggestion", "fix"]] * 3
    assert data[0]["rule"] == "mass_not_positive" and data[0]["severity"] == "error"
    assert json.loads(rows_to_json([])) == []


def test_unicode_survives_the_json() -> None:
    row = build_rows([PhysicalWarning("units_mass", "link:é", "2", "<= 1", "0.002")], lambda key, **kw: key + "→日本")[0]
    assert "→日本" in rows_to_json([row])
    assert json.loads(rows_to_json([row]))[0]["element"] == "link:é"


def test_the_new_texts_exist_in_the_eight_languages_and_all_rule_texts_too() -> None:
    for language in LANGUAGES:
        texts = i18n.load_language(language)
        for key in NEW_KEYS:
            assert texts.get(key, "").strip(), (language, key)
        for rule in RULES:
            assert texts.get("PHYS_R_" + rule) and texts.get("PHYS_F_" + rule), (language, rule)
    english = i18n.load_language("english")
    for language in LANGUAGES:
        texts = i18n.load_language(language)
        for key in ("PHYS_COUNT", "PHYS_COPIED", "PHYS_EXPORTED", "PHYS_EXPORT_FAILED"):
            placeholders = {p for p in ("shown", "total", "error", "warning", "hint", "count", "path") if "{" + p + "}" in english[key]}
            assert all("{" + p + "}" in texts[key] for p in placeholders), (language, key)


def test_portuguese_is_european() -> None:
    texts = i18n.load_language("portuguese")
    joined = " ".join(texts[key] for key in NEW_KEYS)
    for brazilian in ("arquivo", "tela", "celular", "atualizar"):
        assert brazilian not in joined.lower()
    assert texts["PHYS_PANEL_TITLE"] == "Validação física"


# --- the controller --------------------------------------------------------------------------------------------------


def test_the_controller_gives_no_rows_when_the_switch_is_off(monkeypatch, tmp_path) -> None:
    set_config(monkeypatch, tmp_path)
    controller = EditorController()
    controller.load_urdf_file(write_urdf(tmp_path, MULTI_ISSUES))
    assert controller.physical_check_enabled() is False
    assert controller.physical_rows() == []
    set_config(monkeypatch, tmp_path, physical_check="yes")  # not the boolean true
    assert controller.physical_check_enabled() is False


def test_the_controller_rows_match_the_check_and_change_nothing(monkeypatch, tmp_path) -> None:
    set_config(monkeypatch, tmp_path, physical_check=True)
    controller = EditorController()
    assert controller.physical_rows() == []  # no robot
    controller.load_urdf_file(write_urdf(tmp_path, MULTI_ISSUES))
    assert controller.robot is not None and controller.dof_report is not None
    before = robot_to_urdf_string(controller.robot)
    report_before = (controller.dof_report.is_feasible, list(controller.dof_report.reasons), list(controller.dof_report.warnings))
    rows = controller.physical_rows()
    assert [r.rule for r in rows] == ["mass_not_positive", "limit_missing", "units_length"]
    assert robot_to_urdf_string(controller.robot) == before
    assert (controller.dof_report.is_feasible, list(controller.dof_report.reasons), list(controller.dof_report.warnings)) == report_before


# --- the classic panel ----------------------------------------------------------------------------------------------


def _panel(monkeypatch, tmp_path, text: str | None = MULTI_ISSUES):
    qt_app()
    set_config(monkeypatch, tmp_path, physical_check=True)
    from hydra_editor_urdf.ui.panels.physical_panel import PhysicalPanel

    controller = EditorController()
    panel = PhysicalPanel(controller)
    if text is not None:
        controller.load_urdf_file(write_urdf(tmp_path, text))
    return controller, panel


def _cells(panel) -> list[list[str]]:
    table = panel._table
    return [[table.item(r, c).text() for c in range(table.columnCount())] for r in range(table.rowCount())]


def test_panel_without_a_robot_says_so(monkeypatch, tmp_path) -> None:
    _controller, panel = _panel(monkeypatch, tmp_path, text=None)
    assert panel._table.rowCount() == 0
    assert panel._message.text() == i18n._("PHYS_PANEL_NO_ROBOT")
    assert not panel._copy_button.isEnabled() and not panel._export_button.isEnabled()


def test_panel_lists_every_warning_with_its_columns_and_a_counter(monkeypatch, tmp_path) -> None:
    _controller, panel = _panel(monkeypatch, tmp_path)
    cells = _cells(panel)
    assert len(cells) == 3
    assert cells[0][0] == i18n._("PHYS_SEV_error")
    assert "[mass_not_positive]" in cells[0][1] and cells[0][2:5] == ["link:l0", "0", "> 0"]
    assert cells[0][5] == i18n._("PHYS_F_mass_not_positive", fix="0.001", value="0", limit="> 0")
    assert panel._count_label.text() == i18n._("PHYS_COUNT", shown=3, total=3, error=1, warning=1, hint=1)
    assert panel._message.text() == ""


def test_panel_filters_by_severity_rule_and_element(monkeypatch, tmp_path) -> None:
    _controller, panel = _panel(monkeypatch, tmp_path)
    panel._severity.setCurrentIndex(panel._severity.findData("warning"))
    assert [r.rule for r in panel.visible_rows()] == ["limit_missing"]
    assert panel._count_label.text() == i18n._("PHYS_COUNT", shown=1, total=3, error=1, warning=1, hint=1)
    panel._severity.setCurrentIndex(0)
    panel._rule.setCurrentIndex(panel._rule.findData("units_length"))
    assert [r.rule for r in panel.visible_rows()] == ["units_length"]
    panel._rule.setCurrentIndex(0)
    panel._element.setText("LINK:")
    assert [r.rule for r in panel.visible_rows()] == ["mass_not_positive"]
    panel._element.setText("zzz")
    assert panel.visible_rows() == []
    assert panel._message.text() == i18n._("PHYS_PANEL_NO_MATCH")
    assert not panel._copy_button.isEnabled()
    panel._element.setText("")
    assert len(panel.visible_rows()) == 3


def test_panel_sorts_by_each_key(monkeypatch, tmp_path) -> None:
    _controller, panel = _panel(monkeypatch, tmp_path)
    panel._sort.setCurrentIndex(panel._sort.findData("element"))
    assert [r.element for r in panel.visible_rows()] == ["joint:j1", "joint:j2", "link:l0"]
    assert [row[2] for row in _cells(panel)] == ["joint:j1", "joint:j2", "link:l0"]
    panel._sort.setCurrentIndex(panel._sort.findData("severity"))
    assert [r.severity for r in panel.visible_rows()] == ["error", "warning", "hint"]


def test_panel_follows_edits_and_the_check_again_button(monkeypatch, tmp_path) -> None:
    controller, panel = _panel(monkeypatch, tmp_path)
    assert controller.robot is not None
    controller.robot.links["l0"].inertial.mass = 2.0  # type: ignore[union-attr]
    controller.notify_tree_changed()
    assert [r.rule for r in panel.visible_rows()] == ["limit_missing", "units_length"]
    # A change of the settings is seen by "Check again" (it reads them again).
    set_config(monkeypatch, tmp_path, physical_check=True, physical_max_length_m=1.0e9)
    panel._recheck_button.click()
    assert [r.rule for r in panel.visible_rows()] == ["limit_missing"]
    set_config(monkeypatch, tmp_path)  # switch removed: no rows
    panel._recheck_button.click()
    assert panel.visible_rows() == []


def test_a_coherent_model_says_there_is_nothing(monkeypatch, tmp_path) -> None:
    _controller, panel = _panel(monkeypatch, tmp_path, text=FEASIBLE_COHERENT)
    assert panel._table.rowCount() == 0
    assert panel._message.text() == i18n._("PHYS_PANEL_EMPTY")


def test_panel_copies_and_exports_the_rows_shown_as_json(monkeypatch, tmp_path) -> None:
    qt_app()  # skips here when the machine has no Qt platform libraries
    from PySide6.QtWidgets import QApplication

    _controller, panel = _panel(monkeypatch, tmp_path)
    panel._severity.setCurrentIndex(panel._severity.findData("error"))
    panel._copy_button.click()
    copied = json.loads(QApplication.clipboard().text())
    assert [item["rule"] for item in copied] == ["mass_not_positive"]
    assert panel._message.text() == i18n._("PHYS_COPIED", count=1)
    target = tmp_path / "out.json"
    assert panel.export_json(target) is True
    assert json.loads(target.read_text(encoding="utf-8")) == copied
    assert panel._message.text() == i18n._("PHYS_EXPORTED", path=str(target))
    assert panel.export_json(tmp_path / "no_such_folder" / "out.json") is False
    assert panel._message.text().startswith(i18n._("PHYS_EXPORT_FAILED", error="")[:10])


def test_panel_is_read_only_no_edit_and_no_apply_button(monkeypatch, tmp_path) -> None:
    qt_app()  # skips here when the machine has no Qt platform libraries
    from PySide6.QtWidgets import QPushButton, QTableWidget

    controller, panel = _panel(monkeypatch, tmp_path)
    assert panel._table.editTriggers() == QTableWidget.EditTrigger.NoEditTriggers
    assert sorted(b.text() for b in panel.findChildren(QPushButton)) == sorted(
        [i18n._("PHYS_RECHECK"), i18n._("PHYS_COPY_JSON"), i18n._("PHYS_EXPORT_JSON")]
    )
    assert controller.robot is not None
    before = robot_to_urdf_string(controller.robot)
    panel._recheck_button.click()
    panel._copy_button.click()
    assert robot_to_urdf_string(controller.robot) == before


# --- the classic window ----------------------------------------------------------------------------------------------


def _window():
    qt_app()
    try:
        from hydra_editor_urdf.ui.main_window import MainWindow

        return MainWindow()
    except Exception as exc:  # pragma: no cover - the 3D view needs a working OpenGL stack
        pytest.skip(f"the main window cannot be created here: {exc}")


def test_window_with_the_switch_off_is_the_same_as_before(monkeypatch, tmp_path) -> None:
    qt_app()  # skips here when the machine has no Qt platform libraries
    from PySide6.QtWidgets import QDockWidget

    set_config(monkeypatch, tmp_path)
    window = _window()
    names = sorted(d.objectName() for d in window.findChildren(QDockWidget))
    assert len(names) == 5 and not any("phys" in n for n in names)
    assert window.physical_panel is None
    assert list(window._deck_docks) == ["source", "dof", "viewport", "properties", "upload"]
    assert [a.text() for a in window._view_menu.actions()] == [d.windowTitle() for d in window._deck_docks.values()]
    window.close()


def test_window_with_the_switch_on_has_the_panel_tabbed_with_the_dof_screen(monkeypatch, tmp_path) -> None:
    qt_app()  # skips here when the machine has no Qt platform libraries
    from PySide6.QtWidgets import QDockWidget

    set_config(monkeypatch, tmp_path, physical_check=True)
    window = _window()
    docks = window.findChildren(QDockWidget)
    assert len(docks) == 6
    assert window.physical_panel is not None
    assert set(window._deck_docks) == {"source", "dof", "viewport", "properties", "upload", "physical"}
    tabbed = {d.windowTitle() for d in window.tabifiedDockWidgets(window._deck_docks["dof"])}
    assert i18n._("PHYS_PANEL_TITLE") in tabbed
    window.close()


# --- the Qt Quick bridge and deck ----------------------------------------------------------------------------------


def _bridge(controller: EditorController):
    qt_app()
    pytest.importorskip("OpenGL", reason="the Qt Quick bridge imports the 3D renderer")
    sys.path.insert(0, str(ROOT))
    import qt_editor_urdf

    return qt_editor_urdf.EditorQtBridge(controller)


def test_bridge_with_the_switch_off_shows_nothing(monkeypatch, tmp_path) -> None:
    set_config(monkeypatch, tmp_path)
    controller = EditorController()
    bridge = _bridge(controller)
    controller.load_urdf_file(write_urdf(tmp_path, MULTI_ISSUES))
    assert bridge.physicalEnabled is False
    assert bridge.physicalRows == []


def test_bridge_filters_sorts_counts_copies_and_exports(monkeypatch, tmp_path) -> None:
    qt_app()  # skips here when the machine has no Qt platform libraries
    from PySide6.QtGui import QGuiApplication

    set_config(monkeypatch, tmp_path, physical_check=True)
    controller = EditorController()
    bridge = _bridge(controller)
    controller.load_urdf_file(write_urdf(tmp_path, MULTI_ISSUES))
    assert bridge.physicalEnabled is True
    assert [r["rule"] for r in bridge.physicalRows] == ["mass_not_positive", "limit_missing", "units_length"]
    assert bridge.physicalRows[0]["severityLabel"] == i18n._("PHYS_SEV_error")
    assert bridge.physicalCountText == i18n._("PHYS_COUNT", shown=3, total=3, error=1, warning=1, hint=1)
    assert [o["value"] for o in bridge.physicalSeverityOptions] == ["", *SEVERITIES]
    assert [o["value"] for o in bridge.physicalRuleOptions] == ["", "mass_not_positive", "limit_missing", "units_length"]
    bridge.setPhysicalSeverity("hint")
    assert [r["rule"] for r in bridge.physicalRows] == ["units_length"]
    bridge.setPhysicalSeverity("")
    bridge.setPhysicalRule("limit_missing")
    assert [r["rule"] for r in bridge.physicalRows] == ["limit_missing"]
    bridge.setPhysicalRule("")
    bridge.setPhysicalElement("LINK")
    assert [r["rule"] for r in bridge.physicalRows] == ["mass_not_positive"]
    bridge.setPhysicalElement("zzz")
    assert bridge.physicalRows == [] and bridge.physicalMessage == i18n._("PHYS_PANEL_NO_MATCH")
    bridge.setPhysicalElement("")
    bridge.setPhysicalSort("element")
    assert [r["element"] for r in bridge.physicalRows] == ["joint:j1", "joint:j2", "link:l0"]
    bridge.physicalCopyJson()
    assert len(json.loads(QGuiApplication.clipboard().text())) == 3
    target = tmp_path / "bridge.json"
    assert bridge.physicalExportJson(str(target)) is True
    assert json.loads(target.read_text(encoding="utf-8")) == json.loads(QGuiApplication.clipboard().text())
    assert bridge.physicalExportJson(str(tmp_path / "missing" / "x.json")) is False
    assert controller.robot is not None


def test_deck_hides_the_tab_when_off_and_shows_it_when_on(monkeypatch, tmp_path) -> None:
    pytest.importorskip("OpenGL", reason="the Qt Quick bridge imports the 3D renderer")
    os.environ.setdefault("QT_QUICK_BACKEND", "software")
    qt_app()
    from PySide6.QtCore import QUrl
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuickControls2 import QQuickStyle

    sys.path.insert(0, str(ROOT))
    import qt_editor_urdf

    QQuickStyle.setStyle("Basic")
    seen = {}
    for label, config in (("off", {}), ("on", {"physical_check": True})):
        set_config(monkeypatch, tmp_path, **config)
        controller = EditorController()
        bridge = qt_editor_urdf.EditorQtBridge(controller, viewport_frame_provider=qt_editor_urdf.ViewportFrameProvider())
        engine = QQmlApplicationEngine()
        engine.rootContext().setContextProperty("editorBackend", bridge)
        engine.rootContext().setContextProperty("controller", controller)
        engine.load(QUrl.fromLocalFile(str(qt_editor_urdf.QML_PATH)))
        if not engine.rootObjects():
            pytest.skip("the Qt Quick deck cannot be loaded here")
        root = engine.rootObjects()[0]
        tab = root.findChild(object, "physicalTab")
        seen[label] = (tab.property("visible"), tab.property("width"))
        engine.deleteLater()
    assert seen["off"] == (False, 0.0)
    assert seen["on"][0] is True and seen["on"][1] > 0
