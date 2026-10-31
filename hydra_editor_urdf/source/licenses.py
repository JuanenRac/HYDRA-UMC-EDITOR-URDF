# =============================================================================
# HYDRA-UMC EDITOR-URDF - source/licenses.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Which license and attribution files sit with the meshes of a model.

For every mesh the URDF uses, the folders from the mesh up to the folder that was opened are searched for LICENSE,
COPYING, NOTICE and ATTRIBUTION files. What is found is only reported (and can be written as an ATTRIBUTION text);
this does not decide whether a license allows a use.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from hydra_editor_urdf.models import MeshGeometry, Robot

LICENSE_STEMS = ("license", "licence", "copying", "notice", "attribution", "copyright")

_PATTERNS = (
    ("Apache-2.0", r"apache license.{0,40}version 2"),
    ("GPL-3.0", r"gnu general public license.{0,60}version 3"),
    ("GPL-2.0", r"gnu general public license.{0,60}version 2"),
    ("LGPL", r"gnu (lesser|library) general public license"),
    ("MIT", r"permission is hereby granted, free of charge"),
    ("BSD", r"redistribution and use in source and binary forms"),
    ("CC0-1.0", r"cc0|creative commons zero"),
    ("CC-BY-SA", r"attribution-sharealike"),
    ("CC-BY-NC", r"attribution-noncommercial"),
    ("CC-BY", r"creative commons attribution"),
)
_CONDITIONED = ("CC-BY-NC", "CC-BY-SA", "GPL-2.0", "GPL-3.0", "LGPL")


@dataclass
class MeshLicense:
    mesh: str  # the file name as the URDF writes it
    path: Path
    files: list[Path] = field(default_factory=list)
    licenses: list[str] = field(default_factory=list)


def guess_license(path: Path) -> str | None:
    """A short name for the license in a file, from well-known sentences of the first 8 KiB, or None."""
    try:
        text = path.read_bytes()[:8192].decode("utf-8", errors="replace").lower()
    except OSError:
        return None
    text = re.sub(r"\s+", " ", text)
    for name, pattern in _PATTERNS:
        if re.search(pattern, text):
            return name
    return None


def find_license_files(start: str | Path, root: str | Path) -> list[Path]:
    """The license-like files in `start` (a folder or a file) and in each folder above it up to `root`, nearest first."""
    root = Path(root).resolve()
    here = Path(start).resolve()
    if here.is_file():
        here = here.parent
    found: list[Path] = []
    while True:
        try:
            for entry in sorted(here.iterdir()):
                if entry.is_file() and entry.stem.lower() in LICENSE_STEMS:
                    found.append(entry)
        except OSError:
            pass
        if here == root or root not in here.parents:
            break
        here = here.parent
    return found


def mesh_filenames(robot: Robot) -> list[str]:
    names: list[str] = []
    for link in robot.links.values():
        for shape in [*link.visuals, *link.collisions]:
            if isinstance(shape.geometry, MeshGeometry) and shape.geometry.filename and shape.geometry.filename not in names:
                names.append(shape.geometry.filename)
    return names


def check_mesh_licenses(robot: Robot, resolver: Callable[[str], "Path | None"], root: str | Path) -> list[MeshLicense]:
    """One entry per mesh the resolver can find; a mesh it cannot find is left out (a missing mesh is reported elsewhere)."""
    entries: list[MeshLicense] = []
    for name in mesh_filenames(robot):
        path = resolver(name)
        if path is None:
            continue
        files = find_license_files(path, root)
        licenses = sorted({guess for f in files if (guess := guess_license(f))})
        entries.append(MeshLicense(mesh=name, path=Path(path), files=files, licenses=licenses))
    return entries


def license_warnings(entries: list[MeshLicense]) -> list[str]:
    lines = []
    missing = [e.mesh for e in entries if not e.files]
    if missing:
        shown = ", ".join(repr(m) for m in missing[:5]) + (f" and {len(missing) - 5} more" if len(missing) > 5 else "")
        lines.append(
            f"{len(missing)} mesh(es) have no LICENSE, COPYING, NOTICE or ATTRIBUTION file in their folders: {shown}. "
            "Check the license before sending them."
        )
    restricted = sorted({lic for e in entries for lic in e.licenses if lic in _CONDITIONED})
    if restricted:
        lines.append("The meshes carry licenses with conditions that need a look before sharing: " + ", ".join(restricted) + ".")
    return lines


def attribution_text(robot_name: str, entries: list[MeshLicense], root: str | Path) -> str:
    """A plain-text ATTRIBUTION listing, per license file, the meshes that sit under it."""
    root = Path(root).resolve()
    by_file: dict[Path, list[str]] = {}
    for entry in entries:
        for f in entry.files[:1]:  # the nearest file governs the mesh
            by_file.setdefault(f, []).append(entry.mesh)
    lines = [f"Attribution for the meshes of {robot_name}", ""]
    for f, meshes in sorted(by_file.items()):
        try:
            shown = f.relative_to(root).as_posix()
        except ValueError:
            shown = f.name
        guess = guess_license(f)
        lines.append(shown + (f" ({guess})" if guess else ""))
        lines.extend(f"  - {m}" for m in sorted(meshes))
        lines.append("")
    unlicensed = [e.mesh for e in entries if not e.files]
    if unlicensed:
        lines.append("No license file found for:")
        lines.extend(f"  - {m}" for m in sorted(unlicensed))
        lines.append("")
    return "\n".join(lines)
