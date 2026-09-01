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

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QActionGroup
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSizePolicy,
    QToolBar,
    QToolButton,
    QWidget,
)

from hydra_editor_urdf import __version__
from hydra_editor_urdf.app import EditorController
from hydra_editor_urdf.i18n import _, AVAILABLE_LANGUAGES, current_language, save_config, CONFIG_FILE_PATH
from hydra_editor_urdf.ui.about_dialog import AboutDialog
from hydra_editor_urdf.ui.panels.dof_panel import DofPanel
from hydra_editor_urdf.ui.panels.properties_panel import PropertiesPanel
from hydra_editor_urdf.ui.panels.source_panel import SourcePanel
from hydra_editor_urdf.ui.panels.upload_panel import UploadPanel
from hydra_editor_urdf.ui.panels.viewport_panel import ViewportPanel

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
        self.controller.tree_changed.connect(self._on_tree_changed)

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
        """Real QToolBar/QLabel/QToolButton command deck, not a Qt Quick/QML
        island - a QQuickWidget embedded inside a QToolBar inside this
        QMainWindow's real QDockWidget layout rendered as a solid black
        rectangle in practice (its own OpenGL/RHI surface never composited
        correctly once the toolbar/dock layout settled), the same bug
        HYDRA-UMC-SUITE's own command deck had and fixed the same way -
        see that project's own CHANGELOG for the full root-cause account.
        """
        toolbar = QToolBar("HYDRA-UMC command deck", self)
        toolbar.setObjectName("commandDeck")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setIconSize(QSize(34, 34))
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)
        self._command_deck = toolbar

        icon_path = ASSETS_DIR / "HYDRA_UMC_ICON.svg"
        if icon_path.is_file():
            brand = QSvgWidget(str(icon_path), toolbar)
            brand.renderer().setAnimationEnabled(True)
        else:
            brand = QLabel("H", toolbar)
        brand.setObjectName("suiteBrand")
        brand.setFixedSize(44, 44)
        toolbar.addWidget(brand)

        title = QLabel("HYDRA-UMC EDITOR-URDF", toolbar)
        title.setObjectName("commandDeckTitle")
        toolbar.addWidget(title)
        toolbar.addSeparator()

        for label_key, destination in (
            ("DOCK_SOURCE", "source"),
            ("DOCK_DOF", "dof"),
            ("DOCK_VIEWPORT", "viewport"),
            ("DOCK_PROPERTIES", "properties"),
            ("DOCK_UPLOAD", "upload"),
        ):
            self._add_deck_navigation(label_key, destination)

        export_button = QToolButton(toolbar)
        export_button.setObjectName("commandDeckNav")
        export_button.setText(_("MENU_EXPORT_URDF"))
        export_button.clicked.connect(self._on_export_urdf)
        toolbar.addWidget(export_button)

        spacer = QWidget(toolbar)
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)

        self._deck_model_chip = QLabel(toolbar)
        self._deck_model_chip.setObjectName("commandDeckTarget")
        toolbar.addWidget(self._deck_model_chip)

        self._deck_status_chip = QLabel(toolbar)
        self._deck_status_chip.setObjectName("commandDeckState")
        toolbar.addWidget(self._deck_status_chip)

        about = QToolButton(toolbar)
        about.setObjectName("commandDeckAbout")
        about.setText(_("MENU_ABOUT"))
        about.clicked.connect(self._show_about)
        toolbar.addWidget(about)

        # Set the chip text directly rather than through _on_status_message()
        # - that also writes to self._status, the QMainWindow status bar
        # _build_status_bar() creates right after this method returns.
        self._deck_status_chip.setText(f"{_('DECK_STATUS')}\n{_('STATUS_READY')}")
        self._on_deck_model_summary(None, None)

    def _add_deck_navigation(self, label_key: str, destination: str) -> None:
        button = QToolButton(self._command_deck)
        button.setObjectName("commandDeckNav")
        button.setText(_(label_key))
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        button.clicked.connect(lambda _checked=False, dest=destination: self._navigate_deck(dest))
        self._command_deck.addWidget(button)

    def _navigate_deck(self, destination: str) -> None:
        dock = self._deck_docks.get(destination)
        if dock is not None:
            dock.show()
            dock.raise_()

    def _on_status_message(self, message: str) -> None:
        self._status.showMessage(message, 8000)
        self._deck_status_chip.setText(f"{_('DECK_STATUS')}\n{message}" if message else "")

    def _on_robot_loaded(self, robot, report) -> None:
        self._on_deck_model_summary(robot, report)

    def _on_tree_changed(self) -> None:
        """Keep the deck's summary synchronized with live property edits."""
        if self.controller.robot is not None and self.controller.dof_report is not None:
            self._on_deck_model_summary(self.controller.robot, self.controller.dof_report)

    def _on_deck_model_summary(self, robot, report) -> None:
        if robot is None or report is None:
            self._deck_model_chip.setText(f"{_('DECK_STUDIO')}\n{_('DECK_NO_MODEL')}")
            return
        feasible_text = _("DECK_READY") if report.is_feasible else _("DECK_REVIEW")
        self._deck_model_chip.setText(
            f"{robot.name}  •  {_('DECK_DOF')} {report.dof_count}  •  {feasible_text}"
        )

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
        logo_path = ASSETS_DIR / "HYDRA_UMC_ICON.svg"
        AboutDialog(__version__, logo_path, self).exec()

    def _on_language_change(self, code: str) -> None:
        if save_config({"language": code}):
            QMessageBox.information(self, _("TITLE_RESTART_NEEDED"), _("MSG_RESTART_NEEDED"))
        else:
            QMessageBox.critical(self, _("TITLE_COULDNT_SAVE"), _("MSG_LANGUAGE_NOT_SAVED", path=str(CONFIG_FILE_PATH)))
