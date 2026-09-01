# =============================================================================
# HYDRA-UMC EDITOR-URDF - Qt Quick command-deck bridge
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""A QML command surface that forwards into the existing dock workspace."""
from __future__ import annotations

from PySide6.QtCore import QObject, Property, Signal, Slot


class UrdfDeckBridge(QObject):
    """Live QML state only; editing and URDF I/O remain in existing panels."""

    changed = Signal()
    navigateRequested = Signal(str)
    exportRequested = Signal()
    aboutRequested = Signal()

    def __init__(self, version: str, logo_source: str) -> None:
        super().__init__()
        self._version = version
        self._logo_source = logo_source
        self._status = "READY"
        self._model = "NO URDF LOADED"
        self._can_export = False

    @Property(str, constant=True)
    def version(self) -> str:
        return self._version

    @Property(str, constant=True)
    def logoSource(self) -> str:
        return self._logo_source

    @Property(str, notify=changed)
    def status(self) -> str:
        return self._status

    @Property(str, notify=changed)
    def modelName(self) -> str:
        return self._model

    @Property(bool, notify=changed)
    def canExport(self) -> bool:
        return self._can_export

    def set_status(self, status: str) -> None:
        if status != self._status:
            self._status = status
            self.changed.emit()

    def set_model(self, model: str) -> None:
        can_export = bool(model)
        if model != self._model or can_export != self._can_export:
            self._model = model
            self._can_export = can_export
            self.changed.emit()

    @Slot(str)
    def navigate(self, destination: str) -> None:
        self.navigateRequested.emit(destination)

    @Slot()
    def exportUrdf(self) -> None:
        self.exportRequested.emit()

    @Slot()
    def showAbout(self) -> None:
        self.aboutRequested.emit()
