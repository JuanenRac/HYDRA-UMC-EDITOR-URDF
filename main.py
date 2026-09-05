#!/usr/bin/env python3
# =============================================================================
# HYDRA-UMC EDITOR-URDF - main.py (entry point)
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Starts MAXIMIZED (not true OS-level fullscreen), same reasoning as
# HYDRA-UMC-SUITE's own main.py: keeps the native title bar/window
# controls visible rather than hiding them the way showFullScreen() does.
# F11 still toggles real borderless fullscreen and back.
#
# No qasync/asyncio event loop here, unlike HYDRA-UMC-SUITE's own
# main.py - this app's own network calls (source/github_fetcher.py,
# server/client.py) are synchronous and run on a plain QThread per call
# (see ui/panels/source_panel.py's own _GithubFetchThread and
# ui/panels/upload_panel.py's own _ServerCallThread) rather than needing
# every long call to share Qt's own event loop the way SUITE's
# continuous WebSocket connection does - a plain QApplication.exec() is
# the simpler, sufficient choice for this app's own actual usage pattern
# (occasional blocking calls, not a persistent live connection).
# =============================================================================
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication

from hydra_editor_urdf.ui.main_window import MainWindow
from hydra_editor_urdf.ui.theme import apply_theme


def main() -> int:
    if "--qtquick" in sys.argv:
        # The real standalone Qt Quick "command deck" this app's own
        # CHANGELOG.md history shows was already attempted once by
        # EMBEDDING a QQuickWidget inside the classic QToolBar - that
        # painted solid black and was reverted (see
        # ui/main_window.py's own _build_command_deck() docstring). This
        # is the OTHER, proven-safe shape instead: a standalone QML
        # ApplicationWindow, never embedded in the classic
        # QMainWindow - the same real pattern URTC-TESTER/URTC-FLASHER/
        # HYDRA-UMC-SUITE/HYDRA-UMC-UPDATER/HYDRA-UMC-OS-REBUILDER already
        # use. The classic QMainWindow+QDockWidget app below remains the
        # default entry point either way.
        try:
            from qt_editor_urdf import run_qtquick
        except ImportError as exc:
            print(
                "ERROR: Qt Quick mode requires PySide6. "
                "Install this repository's requirements.txt first. "
                f"Details: {exc}",
                file=sys.stderr,
            )
            return 2
        return run_qtquick()

    # Qt Quick's portable Basic style honors the deck's custom rounded
    # backgrounds on every desktop. The native Windows style can discard
    # those QML backgrounds, making the shared Updater visual language vanish.
    QQuickStyle.setStyle("Basic")
    app = QApplication(sys.argv)
    app.setApplicationName("HYDRA-UMC EDITOR-URDF")
    app.setOrganizationName("Electro Hobby 3D")
    apply_theme(app)

    window = MainWindow()

    def toggle_fullscreen() -> None:
        if window.isFullScreen():
            window.showMaximized()
        else:
            window.showFullScreen()

    shortcut = QShortcut(QKeySequence(Qt.Key.Key_F11), window)
    shortcut.activated.connect(toggle_fullscreen)

    window.showMaximized()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
