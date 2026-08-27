# =============================================================================
# HYDRA-UMC EDITOR-URDF - app.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# EditorController - the single owner of "what URDF is currently loaded
# and where did it come from", same role HYDRA-UMC-SUITE's own
# hydra_suite/app.py SuiteController plays there: every UI panel reads/
# mutates state through this object and listens to its Qt signals,
# instead of panels reaching into each other directly. Not itself a
# QWidget - ui/main_window.py owns the actual window and hands this
# controller to every panel's constructor.
# =============================================================================
from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, Signal

from hydra_editor_urdf.models import Robot
from hydra_editor_urdf.source.github_fetcher import GithubFetchError, fetch_github_repo
from hydra_editor_urdf.source.local_folder import LocalFolderError, validate_local_folder
from hydra_editor_urdf.source.scan import build_mesh_resolver, find_urdf_files
from hydra_editor_urdf.urdf.dof import DofReport, validate
from hydra_editor_urdf.urdf.parser import UrdfParseError, parse_urdf_file
from hydra_editor_urdf.urdf.writer import robot_to_urdf_string

# Where fetched-from-GitHub repos land - a real subfolder of this app's
# own install/checkout, NOT a bare OS temp dir, so a fetch survives a
# crash/restart for inspection and isn't silently swept by an unrelated
# OS temp-cleanup pass mid-session (a full GitHub fetch can be tens of
# MB and take real time - losing it to a temp sweep between "fetch" and
# "review the result" would be a bad surprise). See .gitignore's own
# `work/` entry - never meant to be committed.
#
# BUG (found in audit): plain `Path(__file__).resolve().parent.parent`
# is only "this app's own install/checkout" when running from source.
# build_exe.bat packages this app with PyInstaller's own --onefile mode
# (see that script's own [5/6] step) - under --onefile, every bundled
# module's __file__ resolves inside the PyInstaller run's own extraction
# temp dir (sys._MEIPASS, a fresh path under the OS temp folder EVERY
# launch), not next to the real .exe. The old code would have put
# WORK_DIR exactly in the bare OS temp dir this comment says it
# deliberately avoids, and silently lost it the moment the .exe process
# exits (PyInstaller cleans up _MEIPASS on normal exit) - the opposite of
# "survives a crash/restart for inspection" for every packaged build.
# i18n.py's own LANGUAGE_FOLDER/CONFIG_FILE_PATH already solve this
# exact problem (see its own header comment) by keying off
# `sys.executable`'s directory when frozen instead of `__file__` -
# reusing that same pattern here rather than inventing a second one.
if getattr(sys, "frozen", False):
    _base_dir = Path(sys.executable).resolve().parent
else:
    _base_dir = Path(__file__).resolve().parent.parent
WORK_DIR = _base_dir / "work"


class EditorController(QObject):
    robot_loaded = Signal(object, object)  # (Robot, DofReport) - emitted on every successful import, even an infeasible one (the report itself carries why)
    load_failed = Signal(str)  # human-readable error - GithubFetchError/LocalFolderError/UrdfParseError message
    status_message = Signal(str)  # short progress text for the status bar, e.g. "Fetching owner/repo..."
    urdf_candidates_found = Signal(list, object)  # (list[Path], mesh_search_root: Path) - every .urdf/.xacro found under a fetched/opened folder, before auto-picking one
    selected_link_changed = Signal(object)  # str | None
    joint_values_changed = Signal(dict)  # str -> float, current preview pose
    tree_changed = Signal()  # emitted after any edit that changes geometry/material/joint-type - viewport must rebuild_buffers()

    def __init__(self):
        super().__init__()
        self.robot: Robot | None = None
        self.dof_report: DofReport | None = None
        self.mesh_resolver: Callable[[str], "Path | None"] = lambda _name: None
        self.selected_link: str | None = None
        self.joint_values: dict[str, float] = {}
        self._source_description: str = ""

    # --- loading ---------------------------------------------------------------

    def load_from_github(self, url: str) -> None:
        self.status_message.emit(f"Fetching {url}...")
        try:
            extracted_root = fetch_github_repo(url, WORK_DIR)
        except GithubFetchError as e:
            self.load_failed.emit(str(e))
            return
        self._source_description = f"GitHub: {url}"
        self._load_from_folder(extracted_root)

    def load_from_local_folder(self, path: str) -> None:
        try:
            folder = validate_local_folder(path)
        except LocalFolderError as e:
            self.load_failed.emit(str(e))
            return
        self._source_description = f"Local folder: {folder}"
        self._load_from_folder(folder)

    def _load_from_folder(self, folder: Path) -> None:
        urdf_files = find_urdf_files(folder)
        if not urdf_files:
            self.load_failed.emit(f"No .urdf or .xacro files found under {folder}.")
            return
        self.urdf_candidates_found.emit(urdf_files, folder)
        # Several real robot description repos ship more than one .urdf
        # (a bare arm + a "with gripper" variant is common) - picking the
        # largest by file size is a cheap, usually-right heuristic for
        # "the main/most complete one" without asking the operator to
        # choose blind before they've seen any of them; ui/panels/
        # source_panel.py lists every candidate found (via the signal
        # just above) so switching away from this default pick is always
        # one double-click, not a re-fetch.
        chosen = max(urdf_files, key=lambda p: p.stat().st_size)
        self.load_urdf_file(chosen, folder)

    def load_urdf_file(self, urdf_path: str | Path, mesh_search_root: str | Path | None = None) -> None:
        urdf_path = Path(urdf_path)
        try:
            robot = parse_urdf_file(urdf_path)
        except UrdfParseError as e:
            self.load_failed.emit(f"{urdf_path.name}: {e}")
            return

        search_root = Path(mesh_search_root) if mesh_search_root is not None else urdf_path.parent
        self.mesh_resolver = build_mesh_resolver(search_root, urdf_path.parent)
        self.robot = robot
        self.dof_report = validate(robot)
        self.joint_values = {}  # render/kinematics.default_joint_values() fills this in once the viewport asks for a pose
        self.selected_link = None
        self.robot_loaded.emit(robot, self.dof_report)

    # --- editing (each of these re-validates and re-emits, so every panel
    #     stays consistent without polling) --------------------------------

    def set_selected_link(self, link_name: str | None) -> None:
        self.selected_link = link_name
        self.selected_link_changed.emit(link_name)

    def set_joint_value(self, joint_name: str, value: float) -> None:
        self.joint_values[joint_name] = value
        self.joint_values_changed.emit(dict(self.joint_values))

    def notify_tree_changed(self) -> None:
        """Called by a properties-editing panel after mutating
        self.robot in place (recolor/rescale/retype/rename) - re-runs DOF
        validation (a joint retype can change the DOF count or introduce
        an unsupported type) and tells every listener (mainly the
        viewport, whose GPU buffers may now be stale) to refresh."""
        if self.robot is None:
            return
        self.dof_report = validate(self.robot)
        self.tree_changed.emit()

    # --- export ------------------------------------------------------------

    def export_urdf_string(self) -> str | None:
        if self.robot is None:
            return None
        return robot_to_urdf_string(self.robot)

    def export_urdf_file(self, path: str | Path) -> None:
        text = self.export_urdf_string()
        if text is None:
            raise ValueError("No robot loaded to export.")
        path = Path(path)
        # BUG (found in audit): this used to call write_text() directly
        # over whatever file the operator picked - if that path already
        # existed (the overwhelmingly common case: "Export" onto the same
        # .urdf just imported, after a live edit) and the process died
        # mid-write (disk full, power loss, OS kill), write_text()'s own
        # open(mode="w") had already truncated the original file to 0
        # bytes before writing a single new byte, so the operator's
        # original source file - not just the new export - was the thing
        # actually at risk. Back up the existing file first (a single
        # `.bak` copy, not a versioned history - matches the scope of a
        # crash-safety net, not a full undo mechanism, which is tracked
        # separately in mejoras_futuras.txt item 7) so a failed write
        # still leaves a recoverable copy of what was there before.
        if path.exists():
            path.replace(path.with_name(path.name + ".bak"))
        path.write_text(text, encoding="utf-8")

    @property
    def source_description(self) -> str:
        return self._source_description
