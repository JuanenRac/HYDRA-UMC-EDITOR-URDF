#!/usr/bin/env python3
# =============================================================================
# HYDRA-UMC EDITOR-URDF - tools/golden_sync.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# Keeps the shared golden URDF set (tests/golden/) and the corpus of questionable
# URDF files (tests/urdf_invalid/) identical in the repositories that check them.
# This checkout holds the masters; the others sit next to it.
#
#   py -3 -I tools/golden_sync.py --check   list the copies that differ (exit 1 if any)
#   py -3 -I tools/golden_sync.py --apply   copy the master over them
# =============================================================================
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
MASTER = HERE / "tests" / "golden"
COPIES = {
    "HYDRA-UMC-EDITOR-STL": Path("tests") / "golden",
    "HYDRA-UMC-PHYSICS-REPLICA": Path("tests") / "golden",
}
# The two readers of joint limits (the replica and the bridge) are tested on the same questionable files.
INVALID_MASTER = HERE / "tests" / "urdf_invalid"
INVALID_COPIES = {
    "HYDRA-UMC-PHYSICS-REPLICA": Path("tests") / "urdf_invalid",
    "HYDRA-UMC-HIL-BRIDGE": Path("src") / "urdf_invalid",
}


def _files(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes().replace(b"\r\n", b"\n") for p in sorted(root.rglob("*")) if p.is_file()}


def main(argv: list[str]) -> int:
    apply = "--apply" in argv
    differing = 0
    sets = [(repo, rel, _files(MASTER)) for repo, rel in COPIES.items()]
    sets += [(repo, rel, _files(INVALID_MASTER)) for repo, rel in INVALID_COPIES.items()]
    for repo, rel, master in sets:
        target = HERE.parent / repo / rel
        if not (HERE.parent / repo).is_dir():
            print(f"skip: {repo} is not next to this checkout")
            continue
        have = _files(target) if target.is_dir() else {}
        if have == master:
            print(f"same: {repo}/{rel.as_posix()}")
            continue
        differing += 1
        if apply:
            for name, data in master.items():
                out = target / name
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(data)
            for name in set(have) - set(master):
                (target / name).unlink()
            print(f"copied: {repo}/{rel.as_posix()}")
        else:
            print(f"differs: {repo}/{rel.as_posix()} ({len(set(have) ^ set(master))} files missing or extra, others by content)")
    if apply:
        return 0
    return 1 if differing else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
