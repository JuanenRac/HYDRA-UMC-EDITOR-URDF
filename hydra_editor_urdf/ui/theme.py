# =============================================================================
# HYDRA-UMC EDITOR-URDF - ui/theme.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Reuses HYDRA-UMC-SUITE's own assets/qss/industrial_dark.qss verbatim
# (copied into this project's own assets/qss/, same relative path) rather
# than designing a new visual theme for a sibling desktop tool in the
# same ecosystem - per [[No reference -> reuse, don't invent]].
# =============================================================================
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication

QSS_PATH = Path(__file__).resolve().parent.parent.parent / "assets" / "qss" / "industrial_dark.qss"


def apply_theme(app: QApplication) -> None:
    try:
        app.setStyleSheet(QSS_PATH.read_text(encoding="utf-8"))
    except OSError:
        pass
