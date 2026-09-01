# =============================================================================
# HYDRA-UMC EDITOR-URDF - ui/main_window.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# The Photoshop/Fusion-360-style dockable workspace the owner's own spec
# asked for - real QDockWidget panels (drag to float/dock/tab/split),
# same mechanism and the same reasoning HYDRA-UMC-SUITE's own
# ui/main_window.py already documents: Qt's own docking system already
# does exactly this, a hand-rolled one would just reinvent it with more
# bugs. Ported structurally from that file per [[No reference -> reuse,
# don't invent]], swapping SUITE's own robot-swarm panels for this app's
# own source/DOF/viewport/properties/upload ones.
# =============================================================================
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QActionGroup
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtWidgets import QDockWidget, QFileDialog, QMainWindow, QMessageBox, QToolBar

from hydra_editor_urdf import __version__
from hydra_editor_urdf.app import EditorController
from hydra_editor_urdf.i18n import _, AVAILABLE_LANGUAGES, current_language, save_config, CONFIG_FILE_PATH
from hydra_editor_urdf.ui.panels.dof_panel import DofPanel
from hydra_editor_urdf.ui.panels.properties_panel import PropertiesPanel
from hydra_editor_urdf.ui.panels.source_panel import SourcePanel
from hydra_editor_urdf.ui.panels.upload_panel import UploadPanel
from hydra_editor_urdf.ui.panels.viewport_panel import ViewportPanel
from hydra_editor_urdf.ui.qtquick_deck import UrdfDeckBridge

ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / "assets"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HYDRA-UMC EDITOR-URDF")
        self.setMinimumSize(1600, 900)

        self.controller = EditorController()

        self.setDockOptions(
            QMainWindow.DockOption.AnimatedDocks
            | QMainWindow.DockOption.AllowNestedDocks
            | QMainWindow.DockOption.AllowTabbedDocks
        )
        self.setTabPosition(Qt.DockWidgetArea.AllDockWidgetAreas, self.tabPosition(Qt.DockWidgetArea.LeftDockWidgetArea))

        self._build_menu()
        self._build_panels()
        self._build_command_deck()
        self._build_status_bar()

        self.controller.load_failed.connect(self._on_status_message)
        self.controller.status_message.connect(self._on_status_message)
        self.controller.robot_loaded.connect(self._on_robot_loaded)

    # --- panels ---------------------------------------------------------------

    def _make_dock(self, title: str, widget, area: Qt.DockWidgetArea) -> QDockWidget:
        dock = QDockWidget(title, self)
        dock.setObjectName(f"dock_{title.lower().replace(' ', '_')}")
        dock.setWidget(widget)
        dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        self.addDockWidget(area, dock)
        return dock

    def _build_panels(self) -> None:
        self.source_panel = SourcePanel(self.controller)
        self.dof_panel = DofPanel(self.controller)
        self.viewport_panel = ViewportPanel(self.controller)
        self.properties_panel = PropertiesPanel(self.controller)
        self.upload_panel = UploadPanel(self.controller)

        dock_source = self._make_dock(_("DOCK_SOURCE"), self.source_panel, Qt.DockWidgetArea.LeftDockWidgetArea)
        dock_dof = self._make_dock(_("DOCK_DOF"), self.dof_panel, Qt.DockWidgetArea.LeftDockWidgetArea)
        dock_viewport = self._make_dock(_("DOCK_VIEWPORT"), self.viewport_panel, Qt.DockWidgetArea.RightDockWidgetArea)
        dock_properties = self._make_dock(_("DOCK_PROPERTIES"), self.properties_panel, Qt.DockWidgetArea.RightDockWidgetArea)
        dock_upload = self._make_dock(_("DOCK_UPLOAD"), self.upload_panel, Qt.DockWidgetArea.BottomDockWidgetArea)
        self._deck_docks = {
            "source": dock_source, "dof": dock_dof, "viewport": dock_viewport,
            "properties": dock_properties, "upload": dock_upload,
        }

        # Sensible default arrangement - fully rearrangeable afterward
        # (float/merge/split/close), same as every other project in this
        # ecosystem's own dockable workspace.
        self.tabifyDockWidget(dock_source, dock_dof)
        dock_source.raise_()
        self.splitDockWidget(dock_viewport, dock_properties, Qt.Orientation.Horizontal)
        self.resizeDocks([dock_viewport, dock_properties], [1200, 400], Qt.Orientation.Horizontal)

        for dock in (dock_source, dock_dof, dock_viewport, dock_properties, dock_upload):
            self._view_menu.addAction(dock.toggleViewAction())

    def _build_command_deck(self) -> None:
        """Embed the shared QML shell without replacing the real editor docks."""
        toolbar = QToolBar("HYDRA-UMC command deck", self)
        toolbar.setObjectName("urdfQtQuickCommandDeck")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setMinimumHeight(76)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)
        icon_path = ASSETS_DIR / "HYDRA_UMC_ICON.svg"
        self._deck_bridge = UrdfDeckBridge(__version__, QUrl.fromLocalFile(str(icon_path)).toString())
        self._deck_bridge.navigateRequested.connect(self._navigate_deck)
        self._deck_bridge.exportRequested.connect(self._on_export_urdf)
        self._deck_bridge.aboutRequested.connect(self._show_about)
        quick_deck = QQuickWidget(toolbar)
        quick_deck.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
        quick_deck.setClearColor(Qt.GlobalColor.transparent)
        quick_deck.setMinimumWidth(1120)
        quick_deck.setMinimumHeight(64)
        quick_deck.setInitialProperties({"deckBackend": self._deck_bridge})
        quick_deck.setSource(QUrl.fromLocalFile(str(ASSETS_DIR / "qml" / "CommandDeck.qml")))
        toolbar.addWidget(quick_deck)

    def _navigate_deck(self, destination: str) -> None:
        dock = self._deck_docks.get(destination)
        if dock is not None:
            dock.show()
            dock.raise_()

    def _on_status_message(self, message: str) -> None:
        self._status.showMessage(message, 8000)
        self._deck_bridge.set_status(message.upper()[:64] if message else "READY")

    def _on_robot_loaded(self, robot, report) -> None:
        self._deck_bridge.set_model(robot.name)

    def _build_menu(self) -> None:
        menu = self.menuBar()

        file_menu = menu.addMenu(_("MENU_FILE"))
        export_action = file_menu.addAction(_("MENU_EXPORT_URDF"))
        export_action.triggered.connect(self._on_export_urdf)
        file_menu.addSeparator()
        quit_action = file_menu.addAction(_("MENU_QUIT"))
        quit_action.triggered.connect(self.close)

        view_menu = menu.addMenu(_("MENU_VIEW"))
        self._view_menu = view_menu

        language_menu = menu.addMenu(_("MENU_LANGUAGE"))
        language_group = QActionGroup(self)
        language_group.setExclusive(True)
        active_lang = current_language()
        for code, display in AVAILABLE_LANGUAGES:
            action = language_menu.addAction(display)
            action.setCheckable(True)
            action.setChecked(code == active_lang)
            action.triggered.connect(lambda checked=False, c=code: self._on_language_change(c))
            language_group.addAction(action)

        help_menu = menu.addMenu(_("MENU_HELP"))
        about_action = help_menu.addAction(_("MENU_ABOUT"))
        about_action.triggered.connect(self._show_about)

    def _build_status_bar(self) -> None:
        self._status = self.statusBar()
        self._status.showMessage(_("STATUS_READY"))

    def _on_export_urdf(self) -> None:
        if self.controller.robot is None:
            QMessageBox.information(self, _("MENU_EXPORT_URDF"), _("EXPORT_NO_ROBOT"))
            return
        path, _filter = QFileDialog.getSaveFileName(self, _("MENU_EXPORT_URDF"), f"{self.controller.robot.name}.urdf", "URDF (*.urdf)")
        if not path:
            return
        try:
            self.controller.export_urdf_file(path)
            self._status.showMessage(_("EXPORT_SUCCESS", path=path), 5000)
        except OSError as e:
            QMessageBox.critical(self, _("MENU_EXPORT_URDF"), str(e))

    def _show_about(self) -> None:
        QMessageBox.information(self, _("TITLE_ABOUT"), _("MSG_ABOUT_BODY", version=__version__))

    def _on_language_change(self, code: str) -> None:
        if save_config({"language": code}):
            QMessageBox.information(self, _("TITLE_RESTART_NEEDED"), _("MSG_RESTART_NEEDED"))
        else:
            QMessageBox.critical(self, _("TITLE_COULDNT_SAVE"), _("MSG_LANGUAGE_NOT_SAVED", path=str(CONFIG_FILE_PATH)))
