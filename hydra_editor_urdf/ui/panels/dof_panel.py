# =============================================================================
# HYDRA-UMC EDITOR-URDF - ui/panels/dof_panel.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# The automated feasibility verdict - the panel that replaces the manual
# "count the joints, check if HYDRA-UMC-STUDIO can take it" judgment call
# every past robot-porting session in this ecosystem made by hand (see
# urdf/dof.py's own header). Purely a read-out of urdf.dof.DofReport;
# owns no state of its own.
# =============================================================================
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QListWidget, QVBoxLayout, QWidget

from hydra_editor_urdf.app import EditorController
from hydra_editor_urdf.i18n import _
from hydra_editor_urdf.urdf.dof import MAX_SUPPORTED_DOF, MIN_SUPPORTED_DOF, DofReport


class DofPanel(QWidget):
    def __init__(self, controller: EditorController, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        self._range_label = QLabel(_("DOF_SUPPORTED_RANGE", min=MIN_SUPPORTED_DOF, max=MAX_SUPPORTED_DOF))
        self._range_label.setWordWrap(True)
        layout.addWidget(self._range_label)

        self._verdict_label = QLabel(_("DOF_NO_ROBOT_LOADED"))
        self._verdict_label.setWordWrap(True)
        self._verdict_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self._verdict_label)

        layout.addWidget(QLabel(_("DOF_ISSUES_LABEL")))
        self._issues_list = QListWidget()
        layout.addWidget(self._issues_list, stretch=1)

        controller.robot_loaded.connect(lambda _robot, report: self._render(report))
        controller.tree_changed.connect(lambda: self._render(controller.dof_report))

    def _render(self, report: DofReport | None) -> None:
        self._issues_list.clear()
        if report is None:
            self._verdict_label.setText(_("DOF_NO_ROBOT_LOADED"))
            return

        if report.is_feasible:
            self._verdict_label.setText(_("DOF_VERDICT_FEASIBLE", dof=report.dof_count))
            self._verdict_label.setStyleSheet("color: #4caf50; font-weight: bold;")
        else:
            self._verdict_label.setText(_("DOF_VERDICT_INFEASIBLE", dof=report.dof_count))
            self._verdict_label.setStyleSheet("color: #e05252; font-weight: bold;")

        for reason in report.reasons:
            self._issues_list.addItem(reason)
        if not report.reasons:
            self._issues_list.addItem(_("DOF_NO_ISSUES"))
