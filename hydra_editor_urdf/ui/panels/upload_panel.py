# =============================================================================
# HYDRA-UMC EDITOR-URDF - ui/panels/upload_panel.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Push the currently-loaded, DOF-feasible robot to a running
# HYDRA-UMC-STUDIO server's own catalog (server/client.py), or pull an
# already-submitted one back down for editing - both directions of the
# owner's own "extraer, modificar, volver a enviar" round-trip. Every
# server call runs on a background QThread (server/client.py's own HTTP
# calls are blocking) so a slow/unreachable server never freezes the UI,
# same pattern source_panel.py already uses for the GitHub fetch.
# =============================================================================
from __future__ import annotations

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from hydra_editor_urdf.app import EditorController
from hydra_editor_urdf.i18n import _
from hydra_editor_urdf.server.client import StudioClient, StudioClientError

# Mirrors HYDRA-UMC-STUDIO's own Config > UI > Module Visibility categories
# (Config.tsx's own moduleOptions) - the operator picks which of these the
# submitted model belongs under, since server.ts's own /api/models/submit
# stores it by category folder and has no way to infer this from the URDF
# itself (a URDF has no "this is a CNC vs a robot arm" field).
CATEGORIES = ["Robot 3-6DOF", "CNC", "PickAndPlace", "Laser", "Vacuum Table", "XY Table", "Heated Bed", "ATC Tools"]


class _ServerCallThread(QThread):
    finished_ok = Signal(object)  # whatever the wrapped call returned
    finished_error = Signal(str)

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self._fn = fn

    def run(self) -> None:
        try:
            result = self._fn()
            self.finished_ok.emit(result)
        except StudioClientError as e:
            self.finished_error.emit(str(e))
        except Exception as e:  # noqa: BLE001 - last-resort guard, same reasoning as source_panel.py's own fetch thread
            self.finished_error.emit(str(e))


class UploadPanel(QWidget):
    def __init__(self, controller: EditorController, parent=None):
        super().__init__(parent)
        self._controller = controller
        self._client: StudioClient | None = None
        self._thread: _ServerCallThread | None = None

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(_("UPLOAD_SERVER_LABEL")))
        conn_row = QHBoxLayout()
        self._host = QLineEdit("192.168.1.100")
        self._port = QSpinBox()
        self._port.setRange(1, 65535)
        self._port.setValue(3000)
        self._username = QLineEdit("admin")
        self._password = QLineEdit("admin")
        self._password.setEchoMode(QLineEdit.EchoMode.Password)
        self._connect_btn = QPushButton(_("UPLOAD_CONNECT_BUTTON"))
        self._connect_btn.clicked.connect(self._on_connect)
        conn_row.addWidget(self._host, stretch=2)
        conn_row.addWidget(self._port, stretch=1)
        conn_row.addWidget(self._username, stretch=1)
        conn_row.addWidget(self._password, stretch=1)
        conn_row.addWidget(self._connect_btn)
        layout.addLayout(conn_row)

        self._connection_status = QLabel(_("UPLOAD_STATUS_NOT_CONNECTED"))
        layout.addWidget(self._connection_status)

        layout.addWidget(QLabel(_("UPLOAD_CATEGORY_LABEL")))
        self._category_combo = QComboBox()
        self._category_combo.addItems(CATEGORIES)
        layout.addWidget(self._category_combo)

        self._overwrite_checkbox = QCheckBox(_("UPLOAD_OVERWRITE_CHECKBOX"))
        layout.addWidget(self._overwrite_checkbox)

        self._push_btn = QPushButton(_("UPLOAD_PUSH_BUTTON"))
        self._push_btn.clicked.connect(self._on_push)
        self._push_btn.setEnabled(False)
        layout.addWidget(self._push_btn)

        layout.addWidget(QLabel(_("UPLOAD_SERVER_MODELS_LABEL")))
        refresh_row = QHBoxLayout()
        self._refresh_btn = QPushButton(_("UPLOAD_REFRESH_BUTTON"))
        self._refresh_btn.clicked.connect(self._on_refresh_models)
        refresh_row.addWidget(self._refresh_btn)
        layout.addLayout(refresh_row)
        self._models_list = QListWidget()
        self._models_list.itemDoubleClicked.connect(self._on_pull_model)
        layout.addWidget(self._models_list, stretch=1)

        controller.robot_loaded.connect(lambda _robot, report: self._push_btn.setEnabled(self._client is not None and report.is_feasible))
        controller.tree_changed.connect(lambda: self._push_btn.setEnabled(self._client is not None and bool(controller.dof_report and controller.dof_report.is_feasible)))

        self._models_by_display: dict[str, dict] = {}

    # --- connect ------------------------------------------------------------

    def _on_connect(self) -> None:
        client = StudioClient(self._host.text().strip(), self._port.value())
        username, password = self._username.text(), self._password.text()
        self._connect_btn.setEnabled(False)
        self._connection_status.setText(_("UPLOAD_STATUS_CONNECTING"))

        def do_login():
            client.login(username, password)
            return client

        self._run_on_thread(do_login, self._on_connected, self._on_connect_error)

    def _on_connected(self, client: StudioClient) -> None:
        self._client = client
        self._connect_btn.setEnabled(True)
        self._connection_status.setText(_("UPLOAD_STATUS_CONNECTED", host=client.base_url))
        if self._controller.dof_report is not None:
            self._push_btn.setEnabled(self._controller.dof_report.is_feasible)
        self._on_refresh_models()

    def _on_connect_error(self, message: str) -> None:
        self._connect_btn.setEnabled(True)
        self._connection_status.setText(_("UPLOAD_STATUS_NOT_CONNECTED"))
        QMessageBox.critical(self, _("UPLOAD_ERROR_TITLE"), message)

    # --- push -----------------------------------------------------------------

    def _on_push(self) -> None:
        if self._client is None or self._controller.robot is None:
            return
        if self._controller.dof_report is not None and not self._controller.dof_report.is_feasible:
            QMessageBox.warning(self, _("UPLOAD_ERROR_TITLE"), _("UPLOAD_INFEASIBLE_WARNING"))
            return

        client = self._client
        robot = self._controller.robot
        mesh_resolver = self._controller.mesh_resolver
        category = self._category_combo.currentText()
        overwrite = self._overwrite_checkbox.isChecked()
        self._push_btn.setEnabled(False)

        def do_push():
            return client.push_model(robot, category, mesh_resolver, overwrite)

        self._run_on_thread(do_push, self._on_push_ok, self._on_push_error)

    def _on_push_ok(self, slug: str) -> None:
        self._push_btn.setEnabled(True)
        QMessageBox.information(self, _("UPLOAD_SUCCESS_TITLE"), _("UPLOAD_SUCCESS_BODY", slug=slug))
        self._on_refresh_models()

    def _on_push_error(self, message: str) -> None:
        self._push_btn.setEnabled(True)
        QMessageBox.critical(self, _("UPLOAD_ERROR_TITLE"), message)

    # --- pull -----------------------------------------------------------------

    def _on_refresh_models(self) -> None:
        if self._client is None:
            return
        client = self._client
        self._run_on_thread(client.list_models, self._on_models_listed, lambda msg: None)  # a failed background refresh isn't worth interrupting the operator with a dialog

    def _on_models_listed(self, models: list) -> None:
        self._models_list.clear()
        self._models_by_display.clear()
        for entry in models:
            display = f"{entry.get('category', '?')} / {entry.get('name', entry.get('slug', '?'))}"
            self._models_by_display[display] = entry
            self._models_list.addItem(display)

    def _on_pull_model(self) -> None:
        item = self._models_list.currentItem()
        if item is None or self._client is None:
            return
        entry = self._models_by_display.get(item.text())
        if entry is None:
            return
        client = self._client
        category, slug = entry.get("category"), entry.get("slug")
        from hydra_editor_urdf.app import WORK_DIR

        def do_pull():
            return client.pull_model(category, slug, WORK_DIR / "pulled")

        self._run_on_thread(do_pull, self._on_pull_ok, self._on_push_error)

    def _on_pull_ok(self, urdf_path) -> None:
        self._controller.load_urdf_file(urdf_path, urdf_path.parent)

    # --- thread helper ----------------------------------------------------

    def _run_on_thread(self, fn, on_ok, on_error) -> None:
        self._thread = _ServerCallThread(fn)
        self._thread.finished_ok.connect(on_ok)
        self._thread.finished_error.connect(on_error)
        self._thread.start()
