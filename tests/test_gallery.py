# =============================================================================
# HYDRA-UMC EDITOR-URDF - tests/test_gallery.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Real shape checks on the hand-curated GALLERY list itself - this
# module's own doc comment insists every entry was actually verified to
# exist before being added; these tests just hold the data to the basic
# structural bar that comment promises (real GitHub URL shape, no
# duplicates), not a live network check against GitHub.
# =============================================================================
from __future__ import annotations

from hydra_editor_urdf.gallery import GALLERY


def test_gallery_is_not_empty():
    assert len(GALLERY) > 0


def test_every_entry_has_a_name_description_and_github_url():
    for entry in GALLERY:
        assert entry.name.strip()
        assert entry.description.strip()
        assert entry.github_url.startswith("https://github.com/")


def test_no_duplicate_names():
    names = [entry.name for entry in GALLERY]
    assert len(names) == len(set(names))


def test_no_duplicate_urls():
    urls = [entry.github_url for entry in GALLERY]
    assert len(urls) == len(set(urls))
