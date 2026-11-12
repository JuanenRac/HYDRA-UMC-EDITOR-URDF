# =============================================================================
# HYDRA-UMC EDITOR-URDF - ui/panels/viewport_panel.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# Hosts the real OpenGL 3D view (render/viewport.py's own UrdfViewport)
# plus a link tree (click to select - drives the properties panel and
# the viewport's own highlight) and one jog slider per movable joint, so
# the operator can preview the URDF moving through its own real range
# before ever touching HYDRA-UMC-STUDIO - this is the "ver resultado en
# vivo" half of the owner's own Photoshop/Fusion-360 reference.
# =============================================================================
from __future__ import annotations


from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QPushButton,
    QSlider,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from hydra_editor_urdf.app import EditorController
from hydra_editor_urdf.i18n import _
from hydra_editor_urdf.models import Joint, JointType, Robot
from hydra_editor_urdf.render.kinematics import default_joint_values, jog_range
from hydra_editor_urdf.render.mesh_prefetch import mesh_jobs, prefetch_meshes
from hydra_editor_urdf.render.viewport import UrdfViewport

SLIDER_STEPS = 1000  # QSlider is integer-only - joint radians/meters are mapped onto [0, SLIDER_STEPS]


class _JointSlider(QWidget):
    value_changed = Signal(str, float)  # (joint_name, value)

    def __init__(self, joint: Joint, initial: float | None = None, parent=None):
        super().__init__(parent)
        self._joint = joint
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)

        unit = _("UNIT_RADIANS") if joint.type != JointType.PRISMATIC else _("UNIT_METERS")
        self._label = QLabel(f"{joint.name} ({unit})")
        layout.addWidget(self._label)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, SLIDER_STEPS)
        # A full turn each way for a CONTINUOUS joint (it has no real limit), the <limit> otherwise: see kinematics.jog_range.
        self._lower, self._upper = jog_range(joint)
        self._slider.valueChanged.connect(self._on_slider_changed)
        layout.addWidget(self._slider)

        # The pose the viewport is actually drawn at (kinematics.default_joint_values), not the middle of the range: they agree for
        # a joint with a sane limit, but not for a CONTINUOUS joint or a degenerate limit.
        self.set_value((self._lower + self._upper) / 2.0 if initial is None else initial)

    def _on_slider_changed(self, step: int) -> None:
        t = step / SLIDER_STEPS
        value = self._lower + t * (self._upper - self._lower)
        self.value_changed.emit(self._joint.name, value)

    def set_value(self, value: float) -> None:
        t = (value - self._lower) / (self._upper - self._lower)
        self._slider.blockSignals(True)
        self._slider.setValue(int(round(max(0.0, min(1.0, t)) * SLIDER_STEPS)))
        self._slider.blockSignals(False)


class _MeshPrefetchThread(QThread):
    """Reads the meshes of one robot into the mesh cache so the interface thread only uploads them afterwards."""

    def __init__(self, robot: Robot, resolver, parent=None):
        super().__init__(parent)
        self._robot = robot
        self._resolver = resolver
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        prefetch_meshes(self._robot, self._resolver, should_stop=lambda: self._cancelled)


class ViewportPanel(QWidget):
    def __init__(self, controller: EditorController, parent=None):
        super().__init__(parent)
        self._controller = controller

        outer = QVBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        outer.addWidget(splitter)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel(_("VIEWPORT_LINKS_LABEL")))
        self._link_tree = QTreeWidget()
        self._link_tree.setHeaderHidden(True)
        self._link_tree.itemClicked.connect(self._on_link_clicked)
        left_layout.addWidget(self._link_tree, stretch=1)
        splitter.addWidget(left)

        center = QWidget()
        center_layout = QVBoxLayout(center)
        self._viewport = UrdfViewport(mesh_resolver=lambda name: controller.mesh_resolver(name))
        # See UrdfViewport's own mesh_warning Signal docstring (see there)
        # finding: a missing/broken mesh reference used to fail silently,
        # rendering a "ghost" robot with no indication anything was
        # skipped) - routed through the same status_message path
        # ui/main_window.py already wires to the status bar, not a new
        # UI mechanism.
        self._viewport.mesh_warning.connect(self._on_mesh_warning)
        center_layout.addWidget(self._viewport, stretch=1)

        # Graphical fallback for when source/scan.py's own heuristic
        # package:// resolution (relative path, then basename search
        # under the fetched/opened folder) can't find a referenced mesh -
        # e.g. the URDF references a sibling ROS package that lives in a
        # separate checkout the original fetch/open never saw. Hidden
        # until a real mesh_warning actually fires, so it doesn't clutter
        # the viewport for the common case where resolution already
        # worked for everything.
        self._locate_meshes_btn = QPushButton(_("VIEWPORT_LOCATE_MESHES_BUTTON"))
        self._locate_meshes_btn.setVisible(False)
        self._locate_meshes_btn.clicked.connect(self._on_locate_meshes_clicked)
        center_layout.addWidget(self._locate_meshes_btn)
        splitter.addWidget(center)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(QLabel(_("VIEWPORT_JOG_LABEL")))
        self._jog_container = QVBoxLayout()
        jog_host = QWidget()
        jog_host.setLayout(self._jog_container)
        right_layout.addWidget(jog_host)
        right_layout.addStretch(1)
        splitter.addWidget(right)

        splitter.setSizes([200, 700, 260])

        self._joint_sliders: list[_JointSlider] = []
        self._prefetch: _MeshPrefetchThread | None = None
        self._retired_prefetches: list[_MeshPrefetchThread] = []  # cancelled reads that Qt still runs: keep a Python reference until they end

        controller.robot_loaded.connect(self._on_robot_loaded)
        controller.tree_changed.connect(self._on_tree_changed)
        controller.selected_link_changed.connect(self._viewport.set_selected_link)
        self._viewport.set_gizmo_listener(self._on_gizmo)

    def _on_robot_loaded(self, robot: Robot, _report) -> None:
        self._locate_meshes_btn.setVisible(False)  # a fresh load starts without any known-missing mesh from a previous file
        self._rebuild_link_tree(robot)
        self._rebuild_jog_sliders(robot)
        self._rebuild_viewport(robot)
        self._viewport.set_joint_values(default_joint_values(robot))

    def _on_tree_changed(self) -> None:
        if self._controller.robot is None:
            return
        self._locate_meshes_btn.setVisible(False)  # rebuild_buffers() below re-raises mesh_warning (and re-shows the button) if anything is still missing after this
        self._rebuild_viewport(self._controller.robot)
        self._viewport.refresh_colors()

    def _rebuild_viewport(self, robot: Robot) -> None:
        """Rebuilds the GPU buffers. A robot with meshes reads them on a worker thread first (a large STL would freeze
        the window), then uploads on this thread once the cache is warm; a newer request cancels the one in flight."""
        if self._prefetch is not None:
            self._prefetch.cancel()
            self._retired_prefetches.append(self._prefetch)
            self._prefetch = None
        if not mesh_jobs(robot, lambda name: self._controller.mesh_resolver(name)):
            self._viewport.rebuild_buffers(robot)
            return
        thread = _MeshPrefetchThread(robot, lambda name: self._controller.mesh_resolver(name))
        thread.finished.connect(lambda t=thread: self._on_prefetch_finished(t, robot))
        self._prefetch = thread
        thread.start()

    def _on_prefetch_finished(self, thread: "_MeshPrefetchThread", robot: Robot) -> None:
        if thread in self._retired_prefetches:
            self._retired_prefetches.remove(thread)
        if thread is not self._prefetch:
            return  # a newer load replaced this one
        self._prefetch = None
        if self._controller.robot is robot:
            self._viewport.rebuild_buffers(robot)
            self._viewport.refresh_colors()

    def wait_for_meshes(self, timeout_ms: int = 30000) -> None:
        """Blocks until the mesh read in flight (if any) has ended and its result was applied (used by tests)."""
        thread = self._prefetch
        if thread is not None:
            thread.wait(timeout_ms)
            from PySide6.QtCore import QCoreApplication

            QCoreApplication.processEvents()

    def _on_mesh_warning(self, message: str) -> None:
        self._controller.status_message.emit(message)
        self._locate_meshes_btn.setVisible(True)

    def _on_locate_meshes_clicked(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, _("VIEWPORT_LOCATE_MESHES_DIALOG_TITLE"))
        if not folder:
            return
        self._controller.add_mesh_search_folder(folder)

    def _rebuild_link_tree(self, robot: Robot) -> None:
        self._link_tree.clear()
        root_name = robot.root_link_name()
        by_parent = robot.joints_by_parent()

        added: set[str] = set()

        def add_link(name: str, parent_item: QTreeWidgetItem | None) -> None:
            if name in added:
                return  # a cycle in the joints must not recurse forever
            added.add(name)
            item = QTreeWidgetItem([name])
            if parent_item is None:
                self._link_tree.addTopLevelItem(item)
            else:
                parent_item.addChild(item)
            for joint in by_parent.get(name, []):
                add_link(joint.child, item)

        if root_name is not None:
            add_link(root_name, None)
            self._link_tree.expandAll()
        else:
            # No single root (dof_panel.py's own DofReport already
            # explains why) - list every link flat rather than showing
            # an empty tree with no way to even select a link to inspect.
            for name in robot.links:
                self._link_tree.addTopLevelItem(QTreeWidgetItem([name]))

    def _rebuild_jog_sliders(self, robot: Robot) -> None:
        while self._jog_container.count():
            item = self._jog_container.takeAt(0)
            if item.widget():  # type: ignore[union-attr]
                item.widget().deleteLater()  # type: ignore[union-attr]
        self._joint_sliders = []
        starting_pose = default_joint_values(robot)
        for joint in robot.movable_joints():
            slider = _JointSlider(joint, starting_pose.get(joint.name))
            slider.value_changed.connect(self._on_jog)
            self._jog_container.addWidget(slider)
            self._joint_sliders.append(slider)

    def _on_gizmo(self, phase: str, joint_name: str, xyz: tuple) -> None:
        """A drag of the translation gizmo: preview while it goes on, one undo step when it ends."""
        if phase == "begin":
            self._controller.begin_origin_drag()
        elif phase == "move":
            self._controller.preview_joint_origin(joint_name, xyz)
        else:
            self._controller.finish_origin_drag()

    def _on_jog(self, joint_name: str, value: float) -> None:
        self._controller.set_joint_value(joint_name, value)
        self._viewport.set_joint_values(self._controller.joint_values)

    def _on_link_clicked(self, item: QTreeWidgetItem, _column: int) -> None:
        self._controller.set_selected_link(item.text(0))
