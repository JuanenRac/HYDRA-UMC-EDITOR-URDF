# =============================================================================
# HYDRA-UMC EDITOR-URDF - ui/panels/properties_panel.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# The "editar al vuelo: colores, tamano, cinematica" panel - the 3 live-
# edit capabilities the owner's own spec calls out as genuinely NEW (not
# something any past manual robot-porting session in this ecosystem ever
# did), applied to whichever link is currently selected in
# viewport_panel.py's own link tree. Every edit here mutates the loaded
# Robot tree IN PLACE, then calls EditorController.notify_tree_changed()
# once at the end - the controller re-validates DOF and the viewport
# rebuilds its GPU buffers off that single signal, so this panel never
# has to know about either directly.
# =============================================================================
from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from hydra_editor_urdf.app import EditorController
from hydra_editor_urdf.i18n import _
from hydra_editor_urdf.models import JointLimit, JointType, Material, MeshGeometry, Robot


class _AxisSpinRow(QWidget):
    """3 QDoubleSpinBox in a row (X/Y/Z) - used for both mesh scale and
    joint axis, the 2 places this panel needs a plain 3-vector editor."""

    def __init__(self, value: tuple[float, float, float], step: float, minimum: float, parent=None):
        super().__init__(parent)
        layout = QFormLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.spins: list[QDoubleSpinBox] = []
        for axis_name, v in zip(("X", "Y", "Z"), value):
            spin = QDoubleSpinBox()
            spin.setRange(minimum, 1e6)
            spin.setSingleStep(step)
            spin.setDecimals(4)
            spin.setValue(v)
            layout.addRow(axis_name, spin)
            self.spins.append(spin)

    def value(self) -> tuple[float, float, float]:
        return (self.spins[0].value(), self.spins[1].value(), self.spins[2].value())


class PropertiesPanel(QWidget):
    def __init__(self, controller: EditorController, parent=None):
        super().__init__(parent)
        self._controller = controller
        self._robot: Robot | None = None
        self._link_name: str | None = None

        outer = QVBoxLayout(self)
        self._title = QLabel(_("PROPS_NO_SELECTION"))
        outer.addWidget(self._title)

        self._color_group = QGroupBox(_("PROPS_COLOR_GROUP"))
        color_layout = QVBoxLayout(self._color_group)
        self._color_button = QPushButton(_("PROPS_PICK_COLOR"))
        self._color_button.clicked.connect(self._on_pick_color)
        color_layout.addWidget(self._color_button)
        outer.addWidget(self._color_group)

        self._scale_group = QGroupBox(_("PROPS_SCALE_GROUP"))
        scale_layout = QVBoxLayout(self._scale_group)
        self._scale_row: _AxisSpinRow | None = None
        self._scale_apply = QPushButton(_("PROPS_APPLY_SCALE"))
        self._scale_apply.clicked.connect(self._on_apply_scale)
        self._scale_layout = scale_layout
        scale_layout.addWidget(self._scale_apply)
        outer.addWidget(self._scale_group)

        self._joint_group = QGroupBox(_("PROPS_JOINT_GROUP"))
        joint_form = QFormLayout(self._joint_group)
        self._joint_type_combo = QComboBox()
        for jt in JointType:
            self._joint_type_combo.addItem(jt.value, jt)
        joint_form.addRow(_("PROPS_JOINT_TYPE"), self._joint_type_combo)

        self._joint_lower = QDoubleSpinBox()
        self._joint_lower.setRange(-1e6, 1e6)
        self._joint_lower.setDecimals(4)
        joint_form.addRow(_("PROPS_JOINT_LOWER"), self._joint_lower)

        self._joint_upper = QDoubleSpinBox()
        self._joint_upper.setRange(-1e6, 1e6)
        self._joint_upper.setDecimals(4)
        joint_form.addRow(_("PROPS_JOINT_UPPER"), self._joint_upper)

        self._joint_apply = QPushButton(_("PROPS_APPLY_JOINT"))
        self._joint_apply.clicked.connect(self._on_apply_joint)
        joint_form.addRow(self._joint_apply)
        outer.addWidget(self._joint_group)

        outer.addStretch(1)

        self._selected_material: Material | None = None
        self._selected_mesh_geometry: MeshGeometry | None = None
        self._selected_joint_name: str | None = None

        controller.robot_loaded.connect(lambda robot, _report: self._on_robot_loaded(robot))
        controller.selected_link_changed.connect(self._on_selection_changed)
        self._set_editors_enabled(False)

    def _on_robot_loaded(self, robot: Robot) -> None:
        self._robot = robot
        self._link_name = None
        self._set_editors_enabled(False)
        self._title.setText(_("PROPS_NO_SELECTION"))

    def _set_editors_enabled(self, enabled: bool) -> None:
        self._color_group.setEnabled(enabled)
        self._scale_group.setEnabled(enabled)
        self._joint_group.setEnabled(enabled)

    def _on_selection_changed(self, link_name: str | None) -> None:
        self._link_name = link_name
        if self._robot is None or link_name is None or link_name not in self._robot.links:
            self._set_editors_enabled(False)
            self._title.setText(_("PROPS_NO_SELECTION"))
            return

        self._title.setText(_("PROPS_SELECTED_LINK", link=link_name))
        self._set_editors_enabled(True)

        link = self._robot.links[link_name]
        first_visual = link.visuals[0] if link.visuals else None
        self._selected_material = first_visual.material if first_visual is not None else None
        self._color_button.setEnabled(first_visual is not None)

        self._rebuild_scale_row(first_visual)

        owning_joint = next((j for j in self._robot.joints.values() if j.child == link_name), None)
        self._selected_joint_name = owning_joint.name if owning_joint is not None else None
        self._joint_group.setEnabled(owning_joint is not None)
        if owning_joint is not None:
            index = self._joint_type_combo.findData(owning_joint.type)
            self._joint_type_combo.setCurrentIndex(max(0, index))
            if owning_joint.limit is not None:
                self._joint_lower.setValue(owning_joint.limit.lower)
                self._joint_upper.setValue(owning_joint.limit.upper)
            else:
                self._joint_lower.setValue(0.0)
                self._joint_upper.setValue(0.0)

    def _rebuild_scale_row(self, visual) -> None:
        if self._scale_row is not None:
            self._scale_layout.removeWidget(self._scale_row)
            self._scale_row.deleteLater()
            self._scale_row = None

        is_mesh = visual is not None and isinstance(visual.geometry, MeshGeometry)
        self._selected_mesh_geometry = visual.geometry if is_mesh else None
        self._scale_group.setEnabled(is_mesh)
        if is_mesh:
            self._scale_row = _AxisSpinRow(visual.geometry.scale, step=0.1, minimum=0.001)
            self._scale_layout.insertWidget(0, self._scale_row)

    def _on_pick_color(self) -> None:
        if self._selected_material is None or self._robot is None or self._link_name is None:
            return
        r, g, b, a = self._selected_material.rgba
        initial = QColor.fromRgbF(r, g, b, a)
        chosen = QColorDialog.getColor(initial, self, _("PROPS_PICK_COLOR"), QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if not chosen.isValid():
            return
        new_rgba = (chosen.redF(), chosen.greenF(), chosen.blueF(), chosen.alphaF())
        link = self._robot.links[self._link_name]
        for visual in link.visuals:
            # Every visual sharing the SAME material object (a top-level
            # <material name> referenced by more than one link) recolors
            # together, matching what a real URDF's own shared-material
            # semantics mean - a single visual's own inline, unshared
            # material recolors alone.
            if visual.material is self._selected_material:
                visual.material.rgba = new_rgba
            elif visual.material is not None and visual.material.name and visual.material.name == self._selected_material.name:
                visual.material.rgba = new_rgba
        self._controller.notify_tree_changed()

    def _on_apply_scale(self) -> None:
        if self._scale_row is None or self._selected_mesh_geometry is None:
            return
        self._selected_mesh_geometry.scale = self._scale_row.value()
        self._controller.notify_tree_changed()

    def _on_apply_joint(self) -> None:
        if self._robot is None or self._selected_joint_name is None:
            return
        joint = self._robot.joints[self._selected_joint_name]
        joint.type = self._joint_type_combo.currentData()
        if joint.type in (JointType.REVOLUTE, JointType.PRISMATIC):
            joint.limit = JointLimit(
                lower=self._joint_lower.value(),
                upper=self._joint_upper.value(),
                effort=joint.limit.effort if joint.limit is not None else 100.0,
                velocity=joint.limit.velocity if joint.limit is not None else 1.0,
            )
        else:
            # BUG (found in audit): retyping a joint AWAY from REVOLUTE/
            # PRISMATIC (e.g. to FIXED) used to leave the previous
            # JointLimit object sitting on joint.limit untouched - urdf/
            # writer.py emits a <limit> element whenever joint.limit is
            # not None, regardless of type, so a FIXED joint that used to
            # be REVOLUTE would round-trip back out with a meaningless
            # <limit lower=... upper=.../> a real URDF consumer has no
            # use for on a joint with no motion. CONTINUOUS is the one
            # exception that keeps whatever limit it had (the URDF spec
            # allows an optional <limit> there too, and this app's own
            # jog slider - ui/panels/viewport_panel.py's own
            # _JointSlider - already treats a CONTINUOUS joint with no
            # limit as a full-turn default, so clearing it here would
            # just lose real user-entered data for no benefit).
            if joint.type != JointType.CONTINUOUS:
                joint.limit = None
        self._controller.notify_tree_changed()
