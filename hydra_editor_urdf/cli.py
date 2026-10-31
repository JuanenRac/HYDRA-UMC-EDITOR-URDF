# =============================================================================
# HYDRA-UMC EDITOR-URDF - cli.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The command line of the editor: `main.py --cli physical-check FILE.urdf [--json] [--mesh-root DIR]`.

It needs no window and no Qt. It reads the model, runs the physical check (urdf/physical_check.py) and prints one line
per warning, or a JSON list with `--json`. It never writes the model. The exit code is 0 when nothing was found, 1 when
there are warnings and 2 when the file could not be read.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Sequence, TextIO

from hydra_editor_urdf import i18n
from hydra_editor_urdf.source.scan import build_mesh_resolver
from hydra_editor_urdf.urdf.parser import UrdfParseError, parse_urdf_string
from hydra_editor_urdf.urdf.physical_check import PhysicalLimits, PhysicalWarning, check_robot, describe, duplicate_names_in_xml

EXIT_CLEAN = 0
EXIT_WARNINGS = 1
EXIT_ERROR = 2


def _physical_check(args: Sequence[str], out: TextIO, err: TextIO) -> int:
    as_json = False
    mesh_root: str | None = None
    files: list[str] = []
    rest = list(args)
    while rest:
        item = rest.pop(0)
        if item == "--json":
            as_json = True
        elif item == "--mesh-root" and rest:
            mesh_root = rest.pop(0)
        elif item.startswith("--"):
            print(i18n._("PHYS_USAGE"), file=err)
            return EXIT_ERROR
        else:
            files.append(item)
    if len(files) != 1:
        print(i18n._("PHYS_USAGE"), file=err)
        return EXIT_ERROR

    path = Path(files[0])
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(i18n._("PHYS_ERROR", error=exc), file=err)
        return EXIT_ERROR

    warnings: list[PhysicalWarning] = duplicate_names_in_xml(text)
    if not warnings:
        try:
            robot = parse_urdf_string(text)
        except UrdfParseError as exc:
            print(i18n._("PHYS_ERROR", error=exc), file=err)
            return EXIT_ERROR
        root = Path(mesh_root) if mesh_root is not None else path.parent
        resolver = build_mesh_resolver(root, path.parent)
        warnings = check_robot(robot, resolver, PhysicalLimits.from_config(i18n.load_config()))

    if as_json:
        payload = [{**w.as_dict(), "message": describe(w, i18n._)} for w in warnings]
        print(json.dumps(payload, ensure_ascii=False, indent=2), file=out)
    elif warnings:
        for warning in warnings:
            print(describe(warning, i18n._), file=out)
        print(i18n._("PHYS_SUMMARY", count=len(warnings), file=path.name), file=out)
    else:
        print(i18n._("PHYS_NONE"), file=out)
    return EXIT_WARNINGS if warnings else EXIT_CLEAN


def run_cli(argv: Sequence[str], out: TextIO | None = None, err: TextIO | None = None) -> int:
    """Runs the command that follows `--cli` in `argv` (the arguments after the program name)."""
    if out is None:
        # The texts are in the language of the app (Japanese, Chinese, ...): write them as UTF-8 whatever the console code page is.
        for stream in (sys.stdout, sys.stderr):
            reconfigure = getattr(stream, "reconfigure", None)
            if reconfigure is not None:
                reconfigure(encoding="utf-8", errors="replace")
    stdout = out if out is not None else sys.stdout
    stderr = err if err is not None else sys.stderr
    args = list(argv)
    if "--cli" not in args:
        return EXIT_ERROR
    after = args[args.index("--cli") + 1 :]
    if after and after[0] == "physical-check":
        return _physical_check(after[1:], stdout, stderr)
    print(i18n._("PHYS_USAGE"), file=stderr)
    return EXIT_ERROR
