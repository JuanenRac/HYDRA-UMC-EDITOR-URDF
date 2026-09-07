# =============================================================================
# HYDRA-UMC EDITOR-URDF - source/local_folder.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# The "already have it in a local folder" half of the owner's own spec -
# deliberately thin, since source/scan.py already does the real work
# (finding URDF files, resolving mesh references) identically for both
# this path and the GitHub-fetched one (source/github_fetcher.py just
# hands scan.py a downloaded folder instead of one the operator already
# had) - this module exists only to validate the folder the operator
# picked and give app.py one consistent entry point regardless of which
# of the 2 source types is in use.
# =============================================================================
from __future__ import annotations

from pathlib import Path


class LocalFolderError(Exception):
    """Always carries a human-readable message - shown directly in
    ui/panels/source_panel.py."""


def validate_local_folder(path: str | Path) -> Path:
    folder = Path(path)
    if not folder.exists():
        raise LocalFolderError(f"{folder} doesn't exist.")
    if not folder.is_dir():
        raise LocalFolderError(f"{folder} isn't a folder.")
    return folder
