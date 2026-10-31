# =============================================================================
# HYDRA-UMC EDITOR-URDF - tests/qt_support.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# Shared helpers of the tests that need Qt: an offscreen application (skipped when the machine has no Qt platform
# plugin) and a configuration file in a temporary folder, so that no test reads or writes the real one.
# =============================================================================
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from hydra_editor_urdf import i18n

INCOHERENT = """<robot name="r">
  <link name="a"><inertial><mass value="-1"/><inertia ixx="1" iyy="1" izz="9" ixy="0" ixz="0" iyz="0"/></inertial></link>
  <link name="b"/>
  <joint name="j" type="revolute"><parent link="a"/><child link="b"/><axis xyz="0 0 2"/>
    <limit lower="2" upper="1" effort="-1" velocity="0"/></joint>
</robot>"""

COHERENT = """<robot name="r">
  <link name="a"><inertial><mass value="1"/><inertia ixx="1" iyy="1" izz="1" ixy="0" ixz="0" iyz="0"/></inertial></link>
  <link name="b"/>
  <joint name="j" type="revolute"><parent link="a"/><child link="b"/><axis xyz="0 0 1"/>
    <limit lower="-1" upper="1" effort="5" velocity="2"/></joint>
</robot>"""


def qt_app():
    """The offscreen QApplication, or a skip when this machine cannot create one."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError as exc:  # pragma: no cover - depends on the machine
        pytest.skip(f"PySide6 widgets are not available: {exc}")
    app = QApplication.instance() or QApplication([])
    return app


def set_config(monkeypatch, tmp_path: Path, **values: object) -> None:
    """Point the editor at a configuration file in `tmp_path` holding `values` (the language stays what it was)."""
    path = tmp_path / "hydra_editor_urdf_config.json"
    path.write_text(json.dumps(values), encoding="utf-8")
    monkeypatch.setattr(i18n, "CONFIG_FILE_PATH", path)


def write_urdf(tmp_path: Path, text: str, name: str = "robot.urdf") -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def _chain(n: int) -> str:
    links = "".join(
        f'<link name="l{i}"><inertial><mass value="1"/><inertia ixx="1" iyy="1" izz="1" ixy="0" ixz="0" iyz="0"/></inertial></link>'
        for i in range(n + 1)
    )
    joints = "".join(
        f'<joint name="j{i}" type="revolute"><parent link="l{i}"/><child link="l{i + 1}"/><axis xyz="0 0 1"/>'
        f'<limit lower="-1" upper="1" effort="5" velocity="2"/></joint>'
        for i in range(n)
    )
    return f'<robot name="chain{n}">{links}{joints}</robot>'


# Three revolute joints: inside the supported range of degrees of freedom and physically coherent.
FEASIBLE_COHERENT = _chain(3)
# The same chain with one mass of zero: still feasible, one physical warning.
FEASIBLE_ZERO_MASS = FEASIBLE_COHERENT.replace('<mass value="1"/>', '<mass value="0"/>', 1)
