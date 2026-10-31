# =============================================================================
# HYDRA-UMC EDITOR-URDF - ui/panels/physical_panel.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The "Physical validation" panel of the classic interface: the warnings of the physical check as a table (severity, rule,
# element, value, limit, suggestion) with filters, a counter, "Check again" and copy/export as JSON. It is read-only: the
# suggestion is text and nothing here changes the robot. The panel is created only when `physical_check` is true in the
# configuration (ui/main_window.py), so with the switch off nothing of it exists. What it shows is decided by
# urdf/physical_view.py, which the Qt Quick deck uses too.
# =============================================================================
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from hydra_editor_urdf.app import EditorController
from hydra_editor_urdf.i18n import _
from hydra_editor_urdf.urdf.physical_view import (
    SEVERITIES,
    SORT_KEYS,
    PhysicalRow,
    counts_by_severity,
    filter_rows,
    rows_to_json,
    rules_present,
    sort_rows,
)

COLUMNS = ("SEVERITY", "RULE", "ELEMENT", "VALUE", "LIMIT", "SUGGESTION")


class PhysicalPanel(QWidget):
    def __init__(self, controller: EditorController, parent=None):
        super().__init__(parent)
        self._controller = controller
        self._all_rows: list[PhysicalRow] = []
        self._shown: list[PhysicalRow] = []

        layout = QVBoxLayout(self)
        intro = QLabel(_("PHYS_PANEL_INTRO"))
        intro.setWordWrap(True)
        layout.addWidget(intro)

        filters = QHBoxLayout()
        self._severity = QComboBox()
        self._severity.addItem(_("PHYS_FILTER_ALL"), "")
        for name in SEVERITIES:
            self._severity.addItem(_("PHYS_SEV_" + name), name)
        self._rule = QComboBox()
        self._rule.addItem(_("PHYS_FILTER_ALL"), "")
        self._element = QLineEdit()
        self._sort = QComboBox()
        for key in SORT_KEYS:
            self._sort.addItem(_("PHYS_COL_" + key.upper()), key)
        for caption, widget in (
            (_("PHYS_FILTER_SEVERITY"), self._severity),
            (_("PHYS_FILTER_RULE"), self._rule),
            (_("PHYS_FILTER_ELEMENT"), self._element),
            (_("PHYS_SORT_BY"), self._sort),
        ):
            filters.addWidget(QLabel(caption))
            filters.addWidget(widget, stretch=1)
        layout.addLayout(filters)

        self._count_label = QLabel()
        layout.addWidget(self._count_label)

        self._table = QTableWidget(0, len(COLUMNS))
        self._table.setHorizontalHeaderLabels([_("PHYS_COL_" + c) for c in COLUMNS])
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setWordWrap(True)
        self._table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self._table, stretch=1)

        buttons = QHBoxLayout()
        self._recheck_button = QPushButton(_("PHYS_RECHECK"))
        self._copy_button = QPushButton(_("PHYS_COPY_JSON"))
        self._export_button = QPushButton(_("PHYS_EXPORT_JSON"))
        for button in (self._recheck_button, self._copy_button, self._export_button):
            buttons.addWidget(button)
        buttons.addStretch(1)
        layout.addLayout(buttons)

        self._message = QLabel()
        self._message.setWordWrap(True)
        layout.addWidget(self._message)

        self._severity.currentIndexChanged.connect(self._apply_filters)
        self._rule.currentIndexChanged.connect(self._apply_filters)
        self._sort.currentIndexChanged.connect(self._apply_filters)
        self._element.textChanged.connect(self._apply_filters)
        self._recheck_button.clicked.connect(self.recheck)
        self._copy_button.clicked.connect(self.copy_json)
        self._export_button.clicked.connect(self._choose_export_path)

        controller.robot_loaded.connect(lambda _robot, _report: self.recheck())
        controller.tree_changed.connect(self.recheck)
        self.recheck()

    # --- data ---------------------------------------------------------------

    def recheck(self) -> None:
        """Runs the physical check again on the loaded robot (and reads the settings again) and refreshes the table."""
        self._all_rows = self._controller.physical_rows()
        selected = self._rule.currentData() or ""
        self._rule.blockSignals(True)
        self._rule.clear()
        self._rule.addItem(_("PHYS_FILTER_ALL"), "")
        for rule in rules_present(self._all_rows):
            self._rule.addItem(rule, rule)
        index = self._rule.findData(selected)
        self._rule.setCurrentIndex(index if index >= 0 else 0)
        self._rule.blockSignals(False)
        self._apply_filters()

    def visible_rows(self) -> list[PhysicalRow]:
        """The rows the table shows now (filtered and sorted)."""
        return list(self._shown)

    def json_text(self) -> str:
        """The JSON of the rows shown now."""
        return rows_to_json(self._shown)

    def _apply_filters(self) -> None:
        filtered = filter_rows(
            self._all_rows,
            severity=self._severity.currentData() or "",
            rule=self._rule.currentData() or "",
            element=self._element.text(),
        )
        self._shown = sort_rows(filtered, self._sort.currentData() or "severity")
        self._table.setRowCount(len(self._shown))
        for row_index, row in enumerate(self._shown):
            cells = (
                _("PHYS_SEV_" + row.severity),
                f"{row.what} [{row.rule}]",
                row.element,
                row.value,
                row.limit,
                row.suggestion,
            )
            for column, text in enumerate(cells):
                item = QTableWidgetItem(text)
                item.setToolTip(text)
                self._table.setItem(row_index, column, item)
        self._table.resizeRowsToContents()
        counts = counts_by_severity(self._all_rows)
        self._count_label.setText(
            _("PHYS_COUNT", shown=len(self._shown), total=len(self._all_rows), error=counts["error"], warning=counts["warning"], hint=counts["hint"])
        )
        self._copy_button.setEnabled(bool(self._shown))
        self._export_button.setEnabled(bool(self._shown))
        if self._controller.robot is None:
            self._message.setText(_("PHYS_PANEL_NO_ROBOT"))
        elif not self._all_rows:
            self._message.setText(_("PHYS_PANEL_EMPTY"))
        elif not self._shown:
            self._message.setText(_("PHYS_PANEL_NO_MATCH"))
        else:
            self._message.setText("")

    # --- copy and export --------------------------------------------------------

    def copy_json(self) -> None:
        QApplication.clipboard().setText(self.json_text())
        self._message.setText(_("PHYS_COPIED", count=len(self._shown)))

    def export_json(self, path: str | Path) -> bool:
        """Writes the JSON of the rows shown now to `path`; returns False (and says why) when it cannot."""
        try:
            Path(path).write_text(self.json_text(), encoding="utf-8")
        except OSError as exc:
            self._message.setText(_("PHYS_EXPORT_FAILED", error=exc))
            return False
        self._message.setText(_("PHYS_EXPORTED", path=str(path)))
        return True

    def _choose_export_path(self) -> None:
        name = self._controller.robot.name if self._controller.robot is not None else "model"
        path, _filter = QFileDialog.getSaveFileName(self, _("PHYS_EXPORT_JSON"), f"{name}_physical.json", "JSON (*.json)")
        if path:
            self.export_json(path)
