# =============================================================================
# HYDRA-UMC EDITOR-URDF - ui/panels/source_panel.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# "Pull from a GitHub URL, or point at a local folder" - the entry point
# to the whole app, per the owner's own spec ("coger de un GitHub
# concreto ... O leerlos de una carpeta local ... las 2 vias deben
# funcionar igual de bien"). Network fetch runs on a background QThread
# (fetch_github_repo does a blocking HTTP download) so a slow/large repo
# doesn't freeze the whole UI - same reasoning as every other "long
# network call from a Qt button" in this ecosystem (e.g. HYDRA-UMC-SUITE's
# own discovery scan).
# =============================================================================
from __future__ import annotations

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from hydra_editor_urdf.app import EditorController
from hydra_editor_urdf.gallery import GALLERY
from hydra_editor_urdf.i18n import _


class _GithubFetchThread(QThread):
    finished_ok = Signal()
    finished_error = Signal(str)

    def __init__(self, controller: EditorController, url: str):
        super().__init__()
        self._controller = controller
        self._url = url

    def run(self) -> None:
        # load_from_github() itself emits robot_loaded/load_failed on the
        # controller (a QObject created on the main thread, so its
        # signals are safely queued back there by Qt regardless of which
        # thread emits them) - this thread's own 2 signals exist only to
        # let the panel know the button/spinner can be re-enabled, not to
        # carry the actual result.
        try:
            self._controller.load_from_github(self._url)
            self.finished_ok.emit()
        except Exception as e:  # noqa: BLE001 - last-resort guard so a bug here surfaces as a message, not a silently-dead thread
            self.finished_error.emit(str(e))


class SourcePanel(QWidget):
    def __init__(self, controller: EditorController, parent=None):
        super().__init__(parent)
        self._controller = controller
        # BUG (found in audit): this used to be a single `_fetch_thread`
        # attribute, overwritten on every new fetch. The Fetch button is
        # disabled while a fetch runs so the UI itself can't retrigger
        # one, but the underlying QThread object still only stays alive
        # via this one Python reference - if this panel (or the whole
        # app) were torn down while a fetch was still in flight, the
        # QThread could be garbage-collected while Qt still had it
        # running, which PySide reports as a hard "QThread: Destroyed
        # while thread is still running" and can crash. Keeping every
        # started thread in this set (not just the latest) until its own
        # `finished` signal fires - and deleteLater()-ing it only then -
        # means a thread is never dropped by Python while Qt still owns
        # it, regardless of how/when this panel gets destroyed.
        self._live_fetch_threads: set[_GithubFetchThread] = set()

        layout = QVBoxLayout(self)

        # A short starter list of verified-real robot-description repos
        # (see gallery.py's own header for why this stays a short,
        # hand-checked list rather than an auto-scraped one) - picking an
        # entry just fills the GitHub URL field below and fetches it
        # exactly like typing that same URL by hand would, so this is
        # purely a discovery convenience, not a separate load path.
        layout.addWidget(QLabel(_("SOURCE_GALLERY_LABEL")))
        gallery_row = QHBoxLayout()
        self._gallery_combo = QComboBox()
        self._gallery_combo.addItem(_("SOURCE_GALLERY_PLACEHOLDER"), None)
        for entry in GALLERY:
            self._gallery_combo.addItem(entry.name, entry)
        self._gallery_combo.setToolTip("")
        self._gallery_combo.currentIndexChanged.connect(self._on_gallery_selection_changed)
        gallery_row.addWidget(self._gallery_combo, stretch=1)
        layout.addLayout(gallery_row)
        self._gallery_description = QLabel("")
        self._gallery_description.setWordWrap(True)
        layout.addWidget(self._gallery_description)

        layout.addWidget(QLabel(_("SOURCE_GITHUB_LABEL")))
        github_row = QHBoxLayout()
        self._github_url = QLineEdit()
        self._github_url.setPlaceholderText(_("SOURCE_GITHUB_PLACEHOLDER"))
        self._github_fetch_btn = QPushButton(_("SOURCE_FETCH_BUTTON"))
        self._github_fetch_btn.clicked.connect(self._on_fetch_github)
        github_row.addWidget(self._github_url, stretch=1)
        github_row.addWidget(self._github_fetch_btn)
        layout.addLayout(github_row)

        layout.addWidget(QLabel(_("SOURCE_LOCAL_LABEL")))
        local_row = QHBoxLayout()
        self._local_path = QLineEdit()
        self._local_path.setPlaceholderText(_("SOURCE_LOCAL_PLACEHOLDER"))
        browse_btn = QPushButton(_("SOURCE_BROWSE_BUTTON"))
        browse_btn.clicked.connect(self._on_browse)
        open_btn = QPushButton(_("SOURCE_OPEN_BUTTON"))
        open_btn.clicked.connect(self._on_open_local)
        local_row.addWidget(self._local_path, stretch=1)
        local_row.addWidget(browse_btn)
        local_row.addWidget(open_btn)
        layout.addLayout(local_row)

        layout.addWidget(QLabel(_("SOURCE_STATUS_LABEL")))
        self._status = QLabel(_("SOURCE_STATUS_IDLE"))
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        layout.addWidget(QLabel(_("SOURCE_FOUND_URDF_LABEL")))
        self._found_list = QListWidget()
        self._found_list.itemDoubleClicked.connect(self._on_pick_found_urdf)
        layout.addWidget(self._found_list, stretch=1)

        controller.status_message.connect(self._status.setText)
        controller.load_failed.connect(self._on_load_failed)
        controller.robot_loaded.connect(lambda _robot, _report: self._status.setText(_("SOURCE_STATUS_LOADED", source=controller.source_description)))
        controller.urdf_candidates_found.connect(self._on_candidates_found)

        self._urdf_dir_by_display: dict[str, tuple[str, str | None]] = {}  # display text -> (urdf_path, mesh_search_root)

    def _on_candidates_found(self, urdf_files: list, mesh_root) -> None:
        self._found_list.clear()
        self._urdf_dir_by_display.clear()
        for path in urdf_files:
            display = str(path.relative_to(mesh_root)) if str(path).startswith(str(mesh_root)) else str(path)
            self._urdf_dir_by_display[display] = (str(path), str(mesh_root))
            self._found_list.addItem(display)

    # --- Gallery ----------------------------------------------------------

    def _on_gallery_selection_changed(self, index: int) -> None:
        entry = self._gallery_combo.itemData(index)
        if entry is None:
            self._gallery_description.setText("")
            return
        # Only FILLS the URL field - doesn't fetch on its own, so picking
        # an entry to read its description never fires an unexpected
        # network request; the operator still presses Fetch themselves,
        # same as if they'd typed the URL by hand.
        self._github_url.setText(entry.github_url)
        self._gallery_description.setText(entry.description)

    # --- GitHub ---------------------------------------------------------------

    def _on_fetch_github(self) -> None:
        url = self._github_url.text().strip()
        if not url:
            return
        self._github_fetch_btn.setEnabled(False)
        self._status.setText(_("SOURCE_STATUS_FETCHING", url=url))
        thread = _GithubFetchThread(self._controller, url)
        self._live_fetch_threads.add(thread)
        thread.finished_ok.connect(lambda: self._github_fetch_btn.setEnabled(True))
        thread.finished_error.connect(self._on_fetch_thread_error)
        thread.finished.connect(lambda t=thread: self._reap_fetch_thread(t))
        thread.start()

    def _reap_fetch_thread(self, thread: "_GithubFetchThread") -> None:
        # QThread.finished fires once run() has actually returned - only
        # then is it safe to let go of Python's own reference (see the
        # comment on _live_fetch_threads above for why a bare local/
        # attribute reference isn't enough on its own).
        self._live_fetch_threads.discard(thread)
        thread.deleteLater()

    def _on_fetch_thread_error(self, message: str) -> None:
        self._github_fetch_btn.setEnabled(True)
        QMessageBox.critical(self, _("SOURCE_ERROR_TITLE"), message)

    def _on_load_failed(self, message: str) -> None:
        self._status.setText(_("SOURCE_STATUS_ERROR"))
        QMessageBox.critical(self, _("SOURCE_ERROR_TITLE"), message)

    # --- Local folder -----------------------------------------------------

    def _on_browse(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, _("SOURCE_BROWSE_DIALOG_TITLE"))
        if chosen:
            self._local_path.setText(chosen)

    def _on_open_local(self) -> None:
        path = self._local_path.text().strip()
        if not path:
            return
        self._controller.load_from_local_folder(path)

    def _on_pick_found_urdf(self) -> None:
        item = self._found_list.currentItem()
        if item is None:
            return
        entry = self._urdf_dir_by_display.get(item.text())
        if entry is None:
            return
        urdf_path, mesh_root = entry
        self._controller.load_urdf_file(urdf_path, mesh_root)
