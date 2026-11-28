# =============================================================================
# HYDRA-UMC EDITOR-URDF - tests/test_urdf_invalid_corpus.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The questionable URDF files both readers of limits are tested on (`tests/urdf_invalid/`): this checkout holds the master that
`tools/golden_sync.py` copies to HYDRA-UMC-PHYSICS-REPLICA and HYDRA-UMC-HIL-BRIDGE, which assert the same fingerprint."""
from __future__ import annotations

import json
from pathlib import Path

CORPUS = Path(__file__).parent / "urdf_invalid"
# FNV-1a 64 of the names and bytes of the set, the same number as in the two Rust repositories: change a case in all three.
FINGERPRINT = 0x379293C2746A6DD7


def _fingerprint(folder: Path) -> int:
    digest = 0xCBF29CE484222325
    for path in sorted(folder.iterdir(), key=lambda p: p.name):
        for byte in path.name.encode("utf-8") + path.read_bytes():
            digest = ((digest ^ byte) * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return digest


def test_the_master_is_the_agreed_set() -> None:
    assert _fingerprint(CORPUS) == FINGERPRINT, sorted(p.name for p in CORPUS.iterdir())


def test_every_case_of_the_table_has_its_file_and_says_what_both_readers_do() -> None:
    cases = json.loads((CORPUS / "expect.json").read_text(encoding="utf-8"))["cases"]
    named = {case["file"] for case in cases}
    assert named == {p.name for p in CORPUS.glob("*.urdf")}
    assert all("replica" in case and "bridge" in case and case["why"] for case in cases)
