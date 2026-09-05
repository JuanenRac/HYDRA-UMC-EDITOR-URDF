# =============================================================================
# HYDRA-UMC EDITOR-URDF - qt_editor_urdf.py (Qt Quick command-deck entry point)
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Qt Quick front end for HYDRA-UMC EDITOR-URDF - the same real "video game
menu" command deck HYDRA-UMC-OS-REBUILDER/HYDRA-UMC-UPDATER/URTC-TESTER/
URTC-FLASHER/HYDRA-UMC-SUITE already have. This app's own classic
QMainWindow+QDockWidget UI already tried to get this look once, by embedding
a QQuickWidget inside its own QToolBar command deck - that painted solid
black (see this repo's own CHANGELOG.md "Unreleased" history and
ui/main_window.py's own _build_command_deck() docstring), the exact same
real bug HYDRA-UMC-SUITE's own first attempt hit. This file is the OTHER,
proven-safe shape instead: a STANDALONE pure-QML ApplicationWindow, the same
real pattern as every sibling app above (none of which embed QML inside a
QMainWindow at all) - launched via `python main.py --qtquick` alongside the
unchanged classic entry point, never replacing it.

EditorController (app.py) is reused completely unchanged here - it was
already a plain QObject with Qt Signals, never tied to QtWidgets, so it
needs zero changes to serve a QML front end too. This bridge (EditorQtBridge)
only owns things with no meaning outside a UI: which panel is on screen,
QML-shaped list/dict projections of the real domain state, and the offscreen
3D renderer - the exact same thin-bridge-over-an-unmodified-backend split
URTC-TESTER/URTC-FLASHER/HYDRA-UMC-SUITE's own bridges already use.

The 5 classic docks (Source/DOF/Viewport/Properties/Upload) all show at
once in the classic layout (Source+DOF tabbed on the left, Viewport+
Properties split on the right, Upload docked at the bottom - see
ui/main_window.py's own _build_panels()) rather than one-at-a-time nav
sidebar pages the way HYDRA-UMC-SUITE's own 26-panel deck works - this
deck's own Main.qml mirrors that same real spatial arrangement instead of
inventing a tabbed/paged layout this app never had.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Callable

from PySide6.QtCore import Property, QObject, QSize, QUrl, Signal, Slot
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QImage
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickImageProvider
from PySide6.QtQuickControls2 import QQuickStyle

from hydra_editor_urdf import __version__
from hydra_editor_urdf.app import EditorController
from hydra_editor_urdf.gallery import GALLERY
from hydra_editor_urdf.i18n import _
from hydra_editor_urdf.inertia_calc import estimate_inertial
from hydra_editor_urdf.models import Inertial, JointLimit, JointType, MeshGeometry, Robot
from hydra_editor_urdf.render.kinematics import default_joint_values
from hydra_editor_urdf.render.viewport import OffscreenUrdfRenderer
from hydra_editor_urdf.server.client import StudioClient, StudioClientError
from hydra_editor_urdf.ui.about_dialog import AUTHOR_EMAIL, AUTHOR_NAME, LICENSE_NAME
# Reused directly, not reimplemented - both already fix a real "QThread
# destroyed while still running" crash by tracking every live thread in a
# set until its own `finished` signal confirms run() actually returned (see
# each class's own docstring in its home module). The Qt Quick bridge below
# hits the exact same real hazard (Fetch/Connect/Push/Refresh/Pull can all
# be triggered again before a previous background call finishes) so it
# reuses the SAME fix rather than a second, drifting copy of it.
from hydra_editor_urdf.ui.panels.source_panel import _GithubFetchThread
from hydra_editor_urdf.ui.panels.upload_panel import CATEGORIES, _ServerCallThread
from hydra_editor_urdf.urdf.dof import MAX_SUPPORTED_DOF, MIN_SUPPORTED_DOF

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
QML_PATH = ASSETS_DIR / "qml" / "EditorDeck.qml"
ICON_PATH = ASSETS_DIR / "HYDRA_UMC_ICON.svg"

DEFAULT_COLOR_RGBA = (0.72, 0.75, 0.80, 1.0)


def _rgba_to_hex(rgba: tuple[float, float, float, float]) -> str:
    r, g, b = (max(0, min(255, round(c * 255))) for c in rgba[:3])
    return f"#{r:02x}{g:02x}{b:02x}"


def _url_to_local_path(value: str) -> str:
    """QML's own FolderDialog/FileDialog hand back a `file:///...` URL
    string, not a plain path - QUrl.toLocalFile() is the real, correct
    cross-platform way to recover a path from one (handles Windows drive
    letters/UNC paths properly, unlike a naive "file:///" string
    replace). A bare path (already local, e.g. typed by hand into a
    TextField) passes through unchanged."""
    if value.startswith("file:"):
        return QUrl(value).toLocalFile()
    return value


class ViewportFrameProvider(QQuickImageProvider):
    """Feeds the 3D Viewport panel's own real rendered frame into QML -
    one real `QImage`, refreshed by EditorQtBridge's own real
    `_render_viewport_frame()` every time render/viewport.py's own
    `OffscreenUrdfRenderer.render()` produces a new one. QML re-fetches on
    every frame by requesting `image://viewportFrame/<frameVersion>` - a
    changing suffix per frame, since QQuickImageProvider results are
    otherwise cached by their own request id and would never refresh a
    live view (the exact same real pattern HYDRA-UMC-SUITE's own
    ViewportFrameProvider already uses)."""

    def __init__(self) -> None:
        super().__init__(QQuickImageProvider.ImageType.Image)
        self._image: QImage | None = None

    def set_image(self, image: QImage) -> None:
        self._image = image

    def requestImage(self, id: str, size: QSize, requestedSize: QSize) -> QImage:  # noqa: N802 - Qt override signature
        image = self._image
        if image is None:
            image = QImage(1, 1, QImage.Format.Format_RGB32)
            image.fill(0xFFFFFF)
        if size is not None:
            size.setWidth(image.width())
            size.setHeight(image.height())
        return image


class EditorQtBridge(QObject):
    """Thin, UI-only bridge - real domain state stays on EditorController
    (exposed to QML unchanged, as context property 'controller'). This
    class only owns what has no meaning outside a UI: QML-shaped list/dict
    projections of the real state, the offscreen 3D renderer, and the
    handful of background threads a slow network call needs."""

    changed = Signal()
    # Own dedicated signal (not the shared `changed` above) - a live 3D
    # render can update on every orbit/pan/zoom drag tick, and `changed`
    # is read by dozens of unrelated Properties across every other panel;
    # firing it that often would re-evaluate all of them for no reason.
    # Same real reasoning as HYDRA-UMC-SUITE's own _viewportChanged.
    _viewportChanged = Signal()

    def __init__(self, controller: EditorController, viewport_frame_provider: "ViewportFrameProvider | None" = None) -> None:
        super().__init__()
        self._controller = controller
        self._viewport_frame_provider = viewport_frame_provider

        self._status_message = _("SOURCE_STATUS_IDLE")
        self._source_busy = False
        self._found_urdf_entries: list[tuple[str, str, str | None]] = []  # (display, path, mesh_root)

        self._link_tree: list[dict[str, object]] = []
        self._joint_sliders: list[dict[str, object]] = []
        self._selected_link: str | None = None

        # -- Properties panel's own per-selection state (mirrors
        # PropertiesPanel's own _selected_material/_selected_mesh_geometry/
        # _selected_joint_name/_selected_visual_geometry instance
        # attributes exactly - see that class's own _on_selection_changed).
        self._props_selected_material = None
        self._props_selected_mesh_geometry: MeshGeometry | None = None
        self._props_selected_joint_name: str | None = None
        self._props_selected_visual_geometry = None
        self._props_color_hex = _rgba_to_hex(DEFAULT_COLOR_RGBA)
        self._props_color_enabled = False
        self._props_is_mesh = False
        self._props_scale = (1.0, 1.0, 1.0)
        self._props_has_joint = False
        self._props_joint_type_index = 0
        self._props_joint_lower = 0.0
        self._props_joint_upper = 0.0
        self._props_inertial_mass = 0.0
        self._props_inertial_ixx = 0.0
        self._props_inertial_iyy = 0.0
        self._props_inertial_izz = 0.0
        self._props_inertial_note = ""

        # -- Viewport (3D) - see HYDRA-UMC-SUITE's own qt_suite.py for the
        # exact same real degrade-honestly pattern this mirrors.
        self._viewport_renderer: OffscreenUrdfRenderer | None = None
        self._viewport_render_failed = False
        self._viewport_render_error = ""
        self._viewport_frame_version = 0

        # -- Upload panel
        self._upload_client: StudioClient | None = None
        self._upload_connecting = False
        self._upload_status_text = _("UPLOAD_STATUS_NOT_CONNECTED")
        self._upload_models: list[dict[str, object]] = []
        self._upload_models_by_index: list[dict] = []
        self._upload_can_push = False

        # Real thread-lifetime tracking - see this module's own header for
        # why these are reused verbatim from source_panel.py/upload_panel.py
        # rather than reimplemented.
        self._live_fetch_threads: set[_GithubFetchThread] = set()
        self._live_server_threads: set[_ServerCallThread] = set()

        controller.status_message.connect(self._on_status_message)
        controller.load_failed.connect(self._on_load_failed)
        controller.robot_loaded.connect(self._on_robot_loaded)
        controller.urdf_candidates_found.connect(self._on_candidates_found)
        controller.selected_link_changed.connect(self._on_selection_changed)
        controller.tree_changed.connect(self._on_tree_changed)

    # --- meta ---------------------------------------------------------------

    @Property(str, constant=True)
    def title(self) -> str:
        return "HYDRA-UMC EDITOR-URDF"

    @Property(str, constant=True)
    def version(self) -> str:
        return __version__

    @Property(str, constant=True)
    def iconSource(self) -> str:
        return QUrl.fromLocalFile(str(ICON_PATH)).toString()

    @Property(str, constant=True)
    def aboutAuthor(self) -> str:
        return AUTHOR_NAME

    @Property(str, constant=True)
    def aboutEmail(self) -> str:
        return AUTHOR_EMAIL

    @Property(str, constant=True)
    def aboutLicense(self) -> str:
        return LICENSE_NAME

    @Slot(str, result=str)
    def uiText(self, key: str) -> str:
        """Expose the established .lng lookup to the QML surface - every
        real string this deck shows already has a key in language/*.lng
        (this port adds zero new user-facing strings, reusing the exact
        same 5-panel vocabulary the classic docks already translate), so
        the fallback dict below only exists for the same real reason
        every sibling deck's own uiText() keeps one: a stale/incomplete
        .lng file degrades to readable English instead of a raw key."""
        translated = _(key)
        return translated if translated != key else {
            "QT_TAGLINE": "URDF EDITOR • LIVE 3D PREVIEW",
            "QT_EXPORT": "EXPORT URDF",
            "QT_NO_URDF_YET": "No URDF loaded yet.",
        }.get(key, key)

    @Property(str, notify=changed)
    def statusMessage(self) -> str:
        return self._status_message

    @Property(str, notify=changed)
    def sourceDescription(self) -> str:
        return self._controller.source_description

    @Property(str, notify=changed)
    def robotName(self) -> str:
        return self._controller.robot.name if self._controller.robot is not None else ""

    @Property(str, notify=changed)
    def deckSummaryText(self) -> str:
        """The header chip's own text - mirrors main_window.py's own
        _on_deck_model_summary() exactly (same "{name} • DOF {n} •
        READY/REVIEW" shape), just read out of the bridge's own reactive
        state instead of the classic dock chip's imperative setText()."""
        robot, report = self._controller.robot, self._controller.dof_report
        if robot is None or report is None:
            return f"{_('DECK_STUDIO')}  •  {_('DECK_NO_MODEL')}"
        feasible_text = _("DECK_READY") if report.is_feasible else _("DECK_REVIEW")
        return f"{robot.name}  •  {_('DECK_DOF')} {report.dof_count}  •  {feasible_text}"

    def _on_status_message(self, message: str) -> None:
        self._status_message = message
        self.changed.emit()

    def _on_load_failed(self, message: str) -> None:
        self._status_message = message
        self.changed.emit()

    # --- Source -------------------------------------------------------------

    @Property("QVariantList", constant=True)
    def gallery(self) -> list[dict[str, str]]:
        # Index 0 is a real, inert placeholder entry - mirrors
        # SourcePanel's own _gallery_combo, whose first real QComboBox
        # item IS "-- Pick a robot --" (empty url/description, `onClicked`
        # a no-op for it) rather than a separate combo "placeholder mode"
        # layered on top of the real entry list.
        placeholder = {"name": _("SOURCE_GALLERY_PLACEHOLDER"), "description": "", "url": ""}
        return [placeholder] + [{"name": entry.name, "description": entry.description, "url": entry.github_url} for entry in GALLERY]

    @Property(bool, notify=changed)
    def sourceBusy(self) -> bool:
        return self._source_busy

    @Slot(str)
    def fetchGithub(self, url: str) -> None:
        url = url.strip()
        if not url or self._source_busy:
            return
        self._source_busy = True
        self._status_message = _("SOURCE_STATUS_FETCHING", url=url)
        self.changed.emit()
        thread = _GithubFetchThread(self._controller, url)
        self._live_fetch_threads.add(thread)
        thread.finished_ok.connect(self._on_fetch_thread_done)
        thread.finished_error.connect(self._on_fetch_thread_done)
        thread.finished.connect(lambda t=thread: self._reap_fetch_thread(t))
        thread.start()

    def _on_fetch_thread_done(self, *_args) -> None:
        self._source_busy = False
        self.changed.emit()

    def _reap_fetch_thread(self, thread: "_GithubFetchThread") -> None:
        self._live_fetch_threads.discard(thread)
        thread.deleteLater()

    @Slot(str, result=str)
    def toLocalPath(self, url: str) -> str:
        """QML-facing wrapper over _url_to_local_path() - lets the Source
        panel's own local-folder TextField show a real OS path after a
        FolderDialog pick instead of a raw file:/// URL."""
        return _url_to_local_path(url)

    @Slot(str)
    def openLocalFolder(self, path: str) -> None:
        path = _url_to_local_path(path.strip())
        if not path:
            return
        self._controller.load_from_local_folder(path)

    @Property("QVariantList", notify=changed)
    def foundUrdfCandidates(self) -> list[str]:
        return [entry[0] for entry in self._found_urdf_entries]

    def _on_candidates_found(self, urdf_files: list, mesh_root) -> None:
        self._found_urdf_entries = []
        for path in urdf_files:
            display = str(path.relative_to(mesh_root)) if str(path).startswith(str(mesh_root)) else str(path)
            self._found_urdf_entries.append((display, str(path), str(mesh_root)))
        self.changed.emit()

    @Slot(int)
    def pickFoundUrdf(self, index: int) -> None:
        if index < 0 or index >= len(self._found_urdf_entries):
            return
        _display, urdf_path, mesh_root = self._found_urdf_entries[index]
        self._controller.load_urdf_file(urdf_path, mesh_root)

    # --- DOF ------------------------------------------------------------------

    @Property(str, constant=True)
    def dofRangeText(self) -> str:
        return _("DOF_SUPPORTED_RANGE", min=MIN_SUPPORTED_DOF, max=MAX_SUPPORTED_DOF)

    @Property(bool, notify=changed)
    def dofHasRobot(self) -> bool:
        return self._controller.dof_report is not None

    @Property(bool, notify=changed)
    def dofFeasible(self) -> bool:
        report = self._controller.dof_report
        return report is not None and report.is_feasible

    @Property(str, notify=changed)
    def dofVerdictText(self) -> str:
        report = self._controller.dof_report
        if report is None:
            return _("DOF_NO_ROBOT_LOADED")
        return _("DOF_VERDICT_FEASIBLE", dof=report.dof_count) if report.is_feasible else _("DOF_VERDICT_INFEASIBLE", dof=report.dof_count)

    @Property("QVariantList", notify=changed)
    def dofIssues(self) -> list[str]:
        report = self._controller.dof_report
        if report is None:
            return []
        return list(report.reasons) if report.reasons else [_("DOF_NO_ISSUES")]

    # --- shared load/edit handlers ---------------------------------------

    def _on_robot_loaded(self, robot: Robot, _report) -> None:
        self._status_message = _("SOURCE_STATUS_LOADED", source=self._controller.source_description)
        self._rebuild_link_tree(robot)
        self._rebuild_joint_sliders(robot)
        self._selected_link = None
        self._reset_properties_selection()
        self._refresh_upload_gate()
        renderer = self._ensure_viewport_renderer()
        if renderer is not None:
            renderer.rebuild_buffers(robot)
            renderer.set_joint_values(default_joint_values(robot))
            self._report_mesh_warning(renderer)
            self._render_viewport_frame_only(renderer)
        self.changed.emit()

    def _on_tree_changed(self) -> None:
        if self._controller.robot is None:
            return
        self._refresh_upload_gate()
        renderer = self._ensure_viewport_renderer()
        if renderer is not None:
            renderer.rebuild_buffers(self._controller.robot)
            renderer.refresh_colors()
            self._report_mesh_warning(renderer)
            self._render_viewport_frame_only(renderer)
        # A retype/rescale can change which properties fields apply
        # (e.g. FIXED no longer shows joint limits) - re-derive the
        # currently-selected link's own displayed fields, same as the
        # classic panel's own tree_changed handler re-rendering DOF.
        self._on_selection_changed(self._selected_link)
        self.changed.emit()

    def _report_mesh_warning(self, renderer: OffscreenUrdfRenderer) -> None:
        if renderer.last_mesh_warning:
            self._controller.status_message.emit(renderer.last_mesh_warning)

    # --- Viewport (3D) -----------------------------------------------------

    def _ensure_viewport_renderer(self) -> "OffscreenUrdfRenderer | None":
        # Real, honest degradation, not a hypothetical - see
        # HYDRA-UMC-SUITE's own qt_suite.py::_ensure_viewport_renderer()
        # for the full account of why constructing a genuine
        # QOpenGLContext/QOffscreenSurface can fail for real and must
        # never be allowed to propagate uncaught out of a Qt slot.
        if self._viewport_renderer is None and not self._viewport_render_failed:
            try:
                self._viewport_renderer = OffscreenUrdfRenderer(lambda name: self._controller.mesh_resolver(name))
            except Exception as exc:  # noqa: BLE001 - see docstring above
                self._viewport_render_failed = True
                self._viewport_render_error = str(exc)
        return self._viewport_renderer

    def _render_viewport_frame_only(self, renderer: "OffscreenUrdfRenderer | None" = None) -> None:
        renderer = renderer or self._viewport_renderer
        if renderer is None:
            return
        image = renderer.render()
        if self._viewport_frame_provider is not None:
            self._viewport_frame_provider.set_image(image)
        self._viewport_frame_version += 1
        self._viewportChanged.emit()

    @Property(bool, notify=changed)
    def viewportHasRobot(self) -> bool:
        return self._controller.robot is not None

    @Property(bool, notify=changed)
    def viewportSupported(self) -> bool:
        return self._controller.robot is not None and not self._viewport_render_failed

    @Property(str, notify=changed)
    def viewportUnsupportedMessage(self) -> str:
        if self._controller.robot is None:
            return _("QT_NO_URDF_YET")
        if self._viewport_render_failed:
            return f"3D rendering unavailable on this machine: {self._viewport_render_error}"
        return ""

    @Property(int, notify=_viewportChanged)
    def viewportFrameVersion(self) -> int:
        return self._viewport_frame_version

    @Slot(float, float)
    def viewportOrbit(self, dx: float, dy: float) -> None:
        if self._viewport_renderer is None:
            return
        self._viewport_renderer.orbit(dx, dy)
        self._render_viewport_frame_only()

    @Slot(float, float)
    def viewportPan(self, dx: float, dy: float) -> None:
        if self._viewport_renderer is None:
            return
        self._viewport_renderer.pan(dx, dy)
        self._render_viewport_frame_only()

    @Slot(float)
    def viewportZoom(self, factor: float) -> None:
        if self._viewport_renderer is None:
            return
        self._viewport_renderer.zoom(factor)
        self._render_viewport_frame_only()

    @Slot(int, int)
    def viewportResize(self, width: int, height: int) -> None:
        if self._viewport_renderer is None:
            return
        self._viewport_renderer.resize(width, height)
        self._render_viewport_frame_only()

    # --- link tree + jog sliders (shared by Viewport panel) ----------------

    def _rebuild_link_tree(self, robot: Robot) -> None:
        rows: list[dict[str, object]] = []
        root_name = robot.root_link_name()
        by_parent = robot.joints_by_parent()

        def add_link(name: str, depth: int) -> None:
            rows.append({"name": name, "depth": depth})
            for joint in by_parent.get(name, []):
                add_link(joint.child, depth + 1)

        if root_name is not None:
            add_link(root_name, 0)
        else:
            # No single root (dof_panel.py's own DofReport already
            # explains why) - list every link flat, same fallback the
            # classic link tree's own _rebuild_link_tree() uses.
            for name in robot.links:
                rows.append({"name": name, "depth": 0})
        self._link_tree = rows

    @Property("QVariantList", notify=changed)
    def linkTree(self) -> list[dict[str, object]]:
        return self._link_tree

    @Property(str, notify=changed)
    def selectedLink(self) -> str:
        return self._selected_link or ""

    @Slot(str)
    def selectLink(self, name: str) -> None:
        self._controller.set_selected_link(name or None)

    def _on_selection_changed(self, link_name: str | None) -> None:
        self._selected_link = link_name
        if self._viewport_renderer is not None:
            self._viewport_renderer.set_selected_link(link_name)
            self._render_viewport_frame_only()
        self._refresh_properties_selection(link_name)
        self.changed.emit()

    def _rebuild_joint_sliders(self, robot: Robot) -> None:
        rows: list[dict[str, object]] = []
        for joint in robot.movable_joints():
            unit = _("UNIT_DEGREES") if joint.type != JointType.PRISMATIC else _("UNIT_METERS")
            if joint.limit is not None:
                lower, upper = joint.limit.lower, joint.limit.upper
            else:
                # CONTINUOUS with no meaningful limit - offer a full turn
                # each way as a reasonable jog range for a live preview,
                # same real fallback _JointSlider.__init__ uses.
                lower, upper = -math.pi, math.pi
            if upper <= lower:
                upper = lower + 1e-6  # degenerate <limit> in the source file - keep the slider usable instead of a divide-by-zero
            # Faithful port note: the classic _JointSlider always starts
            # at its own midpoint ((lower+upper)/2), independent of
            # default_joint_values() - which is what the viewport is
            # ACTUALLY posed at right after load (see _on_robot_loaded
            # above). That's a real, pre-existing mismatch in the classic
            # UI (the sliders don't reflect the pose on screen until the
            # operator first touches one) - reproduced here as-is rather
            # than silently invented away, since fixing it isn't part of
            # this port.
            rows.append({"name": joint.name, "unit": unit, "lower": lower, "upper": upper, "value": (lower + upper) / 2.0})
        self._joint_sliders = rows

    @Property("QVariantList", notify=changed)
    def jointSliders(self) -> list[dict[str, object]]:
        return self._joint_sliders

    @Slot(str, float)
    def setJointValue(self, joint_name: str, value: float) -> None:
        self._controller.set_joint_value(joint_name, value)
        if self._viewport_renderer is not None:
            self._viewport_renderer.set_joint_values(self._controller.joint_values)
            self._render_viewport_frame_only()

    # --- Properties -----------------------------------------------------------

    def _reset_properties_selection(self) -> None:
        self._props_selected_material = None
        self._props_selected_mesh_geometry = None
        self._props_selected_joint_name = None
        self._props_selected_visual_geometry = None
        self._props_color_enabled = False
        self._props_is_mesh = False
        self._props_has_joint = False
        self._props_inertial_note = ""

    def _refresh_properties_selection(self, link_name: str | None) -> None:
        robot = self._controller.robot
        if robot is None or link_name is None or link_name not in robot.links:
            self._reset_properties_selection()
            return

        link = robot.links[link_name]
        first_visual = link.visuals[0] if link.visuals else None
        self._props_selected_material = first_visual.material if first_visual is not None else None
        self._props_color_enabled = first_visual is not None
        self._props_color_hex = _rgba_to_hex(self._props_selected_material.rgba if self._props_selected_material is not None else DEFAULT_COLOR_RGBA)

        is_mesh = first_visual is not None and isinstance(first_visual.geometry, MeshGeometry)
        self._props_selected_mesh_geometry = first_visual.geometry if is_mesh else None
        self._props_is_mesh = is_mesh
        self._props_scale = first_visual.geometry.scale if is_mesh else (1.0, 1.0, 1.0)

        self._props_selected_visual_geometry = first_visual.geometry if first_visual is not None else None
        self._props_inertial_note = ""
        existing = link.inertial
        self._props_inertial_mass = existing.mass if existing is not None else 0.0
        self._props_inertial_ixx = existing.ixx if existing is not None else 0.0
        self._props_inertial_iyy = existing.iyy if existing is not None else 0.0
        self._props_inertial_izz = existing.izz if existing is not None else 0.0

        owning_joint = next((j for j in robot.joints.values() if j.child == link_name), None)
        self._props_selected_joint_name = owning_joint.name if owning_joint is not None else None
        self._props_has_joint = owning_joint is not None
        if owning_joint is not None:
            self._props_joint_type_index = list(JointType).index(owning_joint.type)
            if owning_joint.limit is not None:
                self._props_joint_lower = owning_joint.limit.lower
                self._props_joint_upper = owning_joint.limit.upper
            else:
                self._props_joint_lower = 0.0
                self._props_joint_upper = 0.0

    @Property(bool, notify=changed)
    def propsHasSelection(self) -> bool:
        return self._selected_link is not None and self._controller.robot is not None and self._selected_link in self._controller.robot.links

    @Property(str, notify=changed)
    def propsTitleText(self) -> str:
        return _("PROPS_SELECTED_LINK", link=self._selected_link) if self.propsHasSelection else _("PROPS_NO_SELECTION")

    @Property(bool, notify=changed)
    def propsColorEnabled(self) -> bool:
        return self._props_color_enabled

    @Property(str, notify=changed)
    def propsColorHex(self) -> str:
        return self._props_color_hex

    @Slot(QColor)
    def applyColor(self, color: QColor) -> None:
        if self._props_selected_material is None or self._controller.robot is None or self._selected_link is None:
            return
        new_rgba = (color.redF(), color.greenF(), color.blueF(), color.alphaF())
        link = self._controller.robot.links[self._selected_link]
        for visual in link.visuals:
            # Every visual sharing the SAME material object (a top-level
            # <material name> referenced by more than one link) recolors
            # together - same real shared-material semantics
            # PropertiesPanel._on_pick_color() already reproduces.
            if visual.material is self._props_selected_material:
                visual.material.rgba = new_rgba
            elif visual.material is not None and visual.material.name and visual.material.name == self._props_selected_material.name:
                visual.material.rgba = new_rgba
        self._controller.notify_tree_changed()

    @Property(bool, notify=changed)
    def propsIsMesh(self) -> bool:
        return self._props_is_mesh

    @Property("QVariantList", notify=changed)
    def propsScale(self) -> list[float]:
        return list(self._props_scale)

    @Slot(float, float, float)
    def applyScale(self, x: float, y: float, z: float) -> None:
        if self._props_selected_mesh_geometry is None:
            return
        self._props_selected_mesh_geometry.scale = (x, y, z)
        self._controller.notify_tree_changed()

    @Property(bool, notify=changed)
    def propsHasJoint(self) -> bool:
        return self._props_has_joint

    @Property("QVariantList", constant=True)
    def propsJointTypeNames(self) -> list[str]:
        return [jt.value for jt in JointType]

    @Property(int, notify=changed)
    def propsJointTypeIndex(self) -> int:
        return self._props_joint_type_index

    @Property(float, notify=changed)
    def propsJointLower(self) -> float:
        return self._props_joint_lower

    @Property(float, notify=changed)
    def propsJointUpper(self) -> float:
        return self._props_joint_upper

    @Slot(int, float, float)
    def applyJoint(self, type_index: int, lower: float, upper: float) -> None:
        if self._controller.robot is None or self._props_selected_joint_name is None:
            return
        joint = self._controller.robot.joints[self._props_selected_joint_name]
        joint.type = list(JointType)[type_index]
        if joint.type in (JointType.REVOLUTE, JointType.PRISMATIC):
            joint.limit = JointLimit(
                lower=lower,
                upper=upper,
                effort=joint.limit.effort if joint.limit is not None else 100.0,
                velocity=joint.limit.velocity if joint.limit is not None else 1.0,
            )
        else:
            # See PropertiesPanel._on_apply_joint()'s own "BUG (found in
            # audit)" comment for why CONTINUOUS is the one exception
            # that keeps its existing limit instead of clearing it.
            if joint.type != JointType.CONTINUOUS:
                joint.limit = None
        self._controller.notify_tree_changed()

    @Property(float, notify=changed)
    def propsInertialMass(self) -> float:
        return self._props_inertial_mass

    @Property(float, notify=changed)
    def propsInertialIxx(self) -> float:
        return self._props_inertial_ixx

    @Property(float, notify=changed)
    def propsInertialIyy(self) -> float:
        return self._props_inertial_iyy

    @Property(float, notify=changed)
    def propsInertialIzz(self) -> float:
        return self._props_inertial_izz

    @Property(str, notify=changed)
    def propsInertialNote(self) -> str:
        return self._props_inertial_note

    @Slot(float)
    def calcInertial(self, current_mass: float) -> None:
        if self._props_selected_visual_geometry is None:
            return
        geometry = self._props_selected_visual_geometry
        mesh_bbox_size: tuple[float, float, float] | None = None
        if isinstance(geometry, MeshGeometry):
            resolved = self._controller.mesh_resolver(geometry.filename)
            if resolved is None:
                self._props_inertial_note = _("PROPS_INERTIAL_MESH_UNRESOLVED")
                self.changed.emit()
                return
            try:
                from hydra_editor_urdf.render.mesh import load_mesh_file
                mesh = load_mesh_file(resolved).scaled(geometry.scale)
                mins = mesh.vertices.min(axis=0)
                maxs = mesh.vertices.max(axis=0)
                extents = maxs - mins
                mesh_bbox_size = (float(extents[0]), float(extents[1]), float(extents[2]))
            except Exception:  # noqa: BLE001 - same last-resort guard as the classic panel
                self._props_inertial_note = _("PROPS_INERTIAL_MESH_LOAD_FAILED")
                self.changed.emit()
                return

        known_mass = current_mass or None
        result = estimate_inertial(geometry, known_mass=known_mass, mesh_bbox_size=mesh_bbox_size)
        if result is None:
            self._props_inertial_note = _("PROPS_INERTIAL_MESH_UNRESOLVED")
            self.changed.emit()
            return

        self._props_inertial_mass = result.mass
        self._props_inertial_ixx = result.ixx
        self._props_inertial_iyy = result.iyy
        self._props_inertial_izz = result.izz

        notes = []
        if result.mass_is_assumed:
            notes.append(_("PROPS_INERTIAL_MASS_ASSUMED"))
        if result.is_mesh_approximation:
            notes.append(_("PROPS_INERTIAL_MESH_APPROX"))
        self._props_inertial_note = " ".join(notes)
        self.changed.emit()

    @Slot(float, float, float, float)
    def applyInertial(self, mass: float, ixx: float, iyy: float, izz: float) -> None:
        if self._controller.robot is None or self._selected_link is None:
            return
        link = self._controller.robot.links[self._selected_link]
        link.inertial = Inertial(mass=mass, ixx=ixx, iyy=iyy, izz=izz)
        self._controller.notify_tree_changed()

    # --- Upload ---------------------------------------------------------------

    @Property("QVariantList", constant=True)
    def uploadCategories(self) -> list[str]:
        return list(CATEGORIES)

    @Property(bool, notify=changed)
    def uploadConnected(self) -> bool:
        return self._upload_client is not None

    @Property(bool, notify=changed)
    def uploadConnecting(self) -> bool:
        return self._upload_connecting

    @Property(str, notify=changed)
    def uploadStatusText(self) -> str:
        return self._upload_status_text

    @Property(bool, notify=changed)
    def uploadCanPush(self) -> bool:
        return self._upload_can_push

    def _refresh_upload_gate(self) -> None:
        report = self._controller.dof_report
        self._upload_can_push = self._upload_client is not None and report is not None and report.is_feasible

    @Slot(str, int, str, str)
    def connectToServer(self, host: str, port: int, username: str, password: str) -> None:
        client = StudioClient(host.strip(), port)
        self._upload_connecting = True
        self._upload_status_text = _("UPLOAD_STATUS_CONNECTING")
        self.changed.emit()

        def do_login():
            client.login(username, password)
            return client

        self._run_on_server_thread(do_login, self._on_connected, self._on_connect_error)

    def _on_connected(self, client: StudioClient) -> None:
        self._upload_client = client
        self._upload_connecting = False
        self._upload_status_text = _("UPLOAD_STATUS_CONNECTED", host=client.base_url)
        self._refresh_upload_gate()
        self.changed.emit()
        self.refreshModels()

    def _on_connect_error(self, message: str) -> None:
        self._upload_connecting = False
        self._upload_status_text = _("UPLOAD_STATUS_NOT_CONNECTED")
        self._status_message = message
        self.changed.emit()

    @Slot(int, bool)
    def pushToServer(self, category_index: int, overwrite: bool) -> None:
        if self._upload_client is None or self._controller.robot is None:
            return
        if self._controller.dof_report is not None and not self._controller.dof_report.is_feasible:
            self._status_message = _("UPLOAD_INFEASIBLE_WARNING")
            self.changed.emit()
            return

        client = self._upload_client
        robot = self._controller.robot
        mesh_resolver = self._controller.mesh_resolver
        category = CATEGORIES[category_index] if 0 <= category_index < len(CATEGORIES) else CATEGORIES[0]

        def do_push():
            return client.push_model(robot, category, mesh_resolver, overwrite)

        self._run_on_server_thread(do_push, self._on_push_ok, self._on_push_error)

    def _on_push_ok(self, slug: str) -> None:
        self._status_message = _("UPLOAD_SUCCESS_BODY", slug=slug)
        self.changed.emit()
        self.refreshModels()

    def _on_push_error(self, message: str) -> None:
        self._status_message = message
        self.changed.emit()

    @Property("QVariantList", notify=changed)
    def uploadModels(self) -> list[str]:
        return [entry["display"] for entry in self._upload_models_by_index]

    @Slot()
    def refreshModels(self) -> None:
        if self._upload_client is None:
            return
        client = self._upload_client
        self._run_on_server_thread(client.list_models, self._on_models_listed, lambda _msg: None)  # a failed background refresh isn't worth interrupting the operator, same as the classic panel

    def _on_models_listed(self, models: list) -> None:
        self._upload_models_by_index = [
            {"display": f"{entry.get('category', '?')} / {entry.get('name', entry.get('slug', '?'))}", "entry": entry}
            for entry in models
        ]
        self.changed.emit()

    @Slot(int)
    def pullModel(self, index: int) -> None:
        if self._upload_client is None or index < 0 or index >= len(self._upload_models_by_index):
            return
        entry = self._upload_models_by_index[index]["entry"]
        client = self._upload_client
        category, slug = entry.get("category"), entry.get("slug")
        from hydra_editor_urdf.app import WORK_DIR

        def do_pull():
            return client.pull_model(category, slug, WORK_DIR / "pulled")

        self._run_on_server_thread(do_pull, self._on_pull_ok, self._on_push_error)

    def _on_pull_ok(self, urdf_path) -> None:
        self._controller.load_urdf_file(urdf_path, urdf_path.parent)

    def _run_on_server_thread(self, fn: Callable[[], object], on_ok: Callable[[object], None], on_error: Callable[[str], None]) -> None:
        thread = _ServerCallThread(fn)
        self._live_server_threads.add(thread)
        thread.finished_ok.connect(on_ok)
        thread.finished_error.connect(on_error)
        thread.finished.connect(lambda t=thread: self._reap_server_thread(t))
        thread.start()

    def _reap_server_thread(self, thread: "_ServerCallThread") -> None:
        self._live_server_threads.discard(thread)
        thread.deleteLater()

    # --- Export ---------------------------------------------------------------

    @Property(bool, notify=changed)
    def canExport(self) -> bool:
        return self._controller.robot is not None

    @Property(str, notify=changed)
    def exportDefaultFileName(self) -> str:
        return f"{self._controller.robot.name}.urdf" if self._controller.robot is not None else "robot.urdf"

    @Slot(str, result=str)
    def exportUrdf(self, path: str) -> str:
        """Returns an empty string on success, or a human-readable error -
        QML has no try/except of its own to report a real OSError with."""
        path = _url_to_local_path(path)
        try:
            self._controller.export_urdf_file(path)
            self._status_message = _("EXPORT_SUCCESS", path=path)
            self.changed.emit()
            return ""
        except (OSError, ValueError) as exc:
            return str(exc)


def run_qtquick() -> int:
    """Run the QML command deck explicitly selected through ``--qtquick``."""
    from PySide6.QtCore import Qt

    # Same real reason main.py's own classic entry point cares about this:
    # Qt6's default rounding policy snaps a fractional OS scale factor
    # (125%/150%/175%, common on a 27"-32" 4K monitor) to the nearest whole
    # integer - PassThrough applies the OS's exact factor instead, and must
    # be set before the QGuiApplication exists.
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QQuickStyle.setStyle("Basic")
    app = QGuiApplication(sys.argv)
    app.setApplicationName("HYDRA-UMC EDITOR-URDF")
    app.setApplicationDisplayName("HYDRA-UMC EDITOR-URDF")
    app.setOrganizationName("Electro Hobby 3D")
    icon = QIcon(str(ICON_PATH))
    if not icon.isNull():
        app.setWindowIcon(icon)

    controller = EditorController()
    viewport_frame_provider = ViewportFrameProvider()
    bridge = EditorQtBridge(controller, viewport_frame_provider=viewport_frame_provider)

    engine = QQmlApplicationEngine()
    engine.addImageProvider("viewportFrame", viewport_frame_provider)
    engine.rootContext().setContextProperty("editorBackend", bridge)
    engine.rootContext().setContextProperty("controller", controller)
    engine.load(QUrl.fromLocalFile(str(QML_PATH)))
    if not engine.rootObjects():
        return 1
    return app.exec()


if __name__ == "__main__":
    sys.exit(run_qtquick())
