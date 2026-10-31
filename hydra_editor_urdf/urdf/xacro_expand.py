# =============================================================================
# HYDRA-UMC EDITOR-URDF - urdf/xacro_expand.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Optional expansion of xacro files through the `xacro` tool of the machine.

Nothing here is on by default: the editor only calls it when `xacro_expand` is true in hydra_editor_urdf_config.json,
and only if a `xacro` program (or `ros2 run xacro xacro`) is found. No xacro code is bundled or imitated.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class XacroError(Exception):
    """The xacro tool is missing, failed, timed out or produced nothing."""


def looks_like_xacro(text: str) -> bool:
    head = text.lstrip()[:2000]
    return "xacro" in head and ("xmlns:xacro" in head or "<xacro:" in text)


def find_xacro() -> list[str] | None:
    """The command that runs xacro, or None when this machine has none."""
    direct = shutil.which("xacro")
    if direct:
        return [direct]
    ros2 = shutil.which("ros2")
    if ros2:
        return [ros2, "run", "xacro", "xacro"]
    return None


def expand_xacro(path: str | Path, command: list[str] | None = None, timeout: float = 60.0) -> str:
    """The plain URDF text that xacro makes of the file. The file name is passed as one argument (no shell)."""
    cmd = command if command is not None else find_xacro()
    if not cmd:
        raise XacroError("The xacro tool was not found (neither `xacro` nor `ros2` is on the PATH).")
    path = Path(path)
    try:
        done = subprocess.run([*cmd, str(path)], capture_output=True, text=True, timeout=timeout, check=False, cwd=str(path.parent))
    except subprocess.TimeoutExpired as exc:
        raise XacroError(f"xacro did not finish in {timeout:g} s.") from exc
    except OSError as exc:
        raise XacroError(f"xacro could not be started: {exc}") from exc
    if done.returncode != 0:
        detail = (done.stderr or "").strip().splitlines()
        raise XacroError(f"xacro failed (exit {done.returncode}): {detail[-1] if detail else 'no message'}")
    if "<robot" not in done.stdout:
        raise XacroError("xacro produced no <robot> element.")
    return done.stdout
