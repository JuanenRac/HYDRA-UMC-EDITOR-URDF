# =============================================================================
# HYDRA-UMC EDITOR-URDF - ui/panels/viewport_panel.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Hosts the real OpenGL 3D view (render/viewport.py's own UrdfViewport)
# plus a link tree (click to select - drives the properties panel and
# the viewport's own highlight) and one jog slider per movable joint, so
# the operator can preview the URDF moving through its own real range
# before ever touching HYDRA-UMC-STUDIO - this is the "ver resultado en
# vivo" half of the owner's own Photoshop/Fusion-360 reference.
# =============================================================================
from __future__ import annotations

import math

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSlider, QSplitter, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from hydra_editor_urdf.app import EditorController
from hydra_editor_urdf.i18n import _
from hydra_editor_urdf.models import Joint, JointType, Robot
from hydra_editor_urdf.render.kinematics import default_joint_values
from hydra_editor_urdf.render.viewport import UrdfViewport

SLIDER_STEPS = 1000  # QSlider is integer-only - joint radians/meters are mapped onto [0, SLIDER_STEPS]


class _JointSlider(QWidget):
    value_changed = Signal(str, float)  # (joint_name, value)

    def __init__(self, joint: Joint, parent=None):
        super().__init__(parent)
        self._joint = joint
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)

        unit = _("UNIT_DEGREES") if joint.type != JointType.PRISMATIC else _("UNIT_METERS")
        self._label = QLabel(f"{joint.name} ({unit})")
        layout.addWidget(self._label)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, SLIDER_STEPS)
        if joint.limit is not None:
            self._lower, self._upper = joint.limit.lower, joint.limit.upper
        else:
            # CONTINUOUS with no meaningful limit - offer a full turn each
            # way as a reasonable jog range for a live preview, not a
            # real hardware limit (CONTINUOUS has none by definition).
            self._lower, self._upper = -math.pi, math.pi
        if self._upper <= self._lower:
            self._upper = self._lower + 1e-6  # degenerate <limit> in the source file - keep the slider usable instead of a divide-by-zero
        self._slider.valueChanged.connect(self._on_slider_changed)
        layout.addWidget(self._slider)

        self.set_value((self._lower + self._upper) / 2.0)

    def _on_slider_changed(self, step: int) -> None:
        t = step / SLIDER_STEPS
        value = self._lower + t * (self._upper - self._lower)
        self.value_changed.emit(self._joint.name, value)

    def set_value(self, value: float) -> None:
        t = (value - self._lower) / (self._upper - self._lower)
        self._slider.blockSignals(True)
        self._slider.setValue(int(round(max(0.0, min(1.0, t)) * SLIDER_STEPS)))
        self._slider.blockSignals(False)


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
        center_layout.addWidget(self._viewport, stretch=1)
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

        controller.robot_loaded.connect(self._on_robot_loaded)
        controller.tree_changed.connect(self._on_tree_changed)
        controller.selected_link_changed.connect(self._viewport.set_selected_link)

    def _on_robot_loaded(self, robot: Robot, _report) -> None:
        self._rebuild_link_tree(robot)
        self._rebuild_jog_sliders(robot)
        self._viewport.rebuild_buffers(robot)
        self._viewport.set_joint_values(default_joint_values(robot))

    def _on_tree_changed(self) -> None:
        if self._controller.robot is None:
            return
        self._viewport.rebuild_buffers(self._controller.robot)
        self._viewport.refresh_colors()

    def _rebuild_link_tree(self, robot: Robot) -> None:
        self._link_tree.clear()
        root_name = robot.root_link_name()
        by_parent = robot.joints_by_parent()

        def add_link(name: str, parent_item: QTreeWidgetItem | None) -> None:
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
            if item.widget():
                item.widget().deleteLater()
        self._joint_sliders = []
        for joint in robot.movable_joints():
            slider = _JointSlider(joint)
            slider.value_changed.connect(self._on_jog)
            self._jog_container.addWidget(slider)
            self._joint_sliders.append(slider)

    def _on_jog(self, joint_name: str, value: float) -> None:
        self._controller.set_joint_value(joint_name, value)
        self._viewport.set_joint_values(self._controller.joint_values)

    def _on_link_clicked(self, item: QTreeWidgetItem, _column: int) -> None:
        self._controller.set_selected_link(item.text(0))
