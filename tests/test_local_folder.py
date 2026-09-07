# =============================================================================
# HYDRA-UMC EDITOR-URDF - tests/test_local_folder.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
from __future__ import annotations

import pytest

from hydra_editor_urdf.source.local_folder import LocalFolderError, validate_local_folder


def test_valid_existing_folder_returns_a_path(tmp_path):
    result = validate_local_folder(tmp_path)
    assert result == tmp_path


def test_nonexistent_path_is_an_error(tmp_path):
    with pytest.raises(LocalFolderError, match="doesn't exist"):
        validate_local_folder(tmp_path / "nope")


def test_path_that_is_a_file_not_a_folder_is_an_error(tmp_path):
    file_path = tmp_path / "a_file.txt"
    file_path.write_text("hello")
    with pytest.raises(LocalFolderError, match="isn't a folder"):
        validate_local_folder(file_path)


def test_accepts_a_plain_string_path_too(tmp_path):
    result = validate_local_folder(str(tmp_path))
    assert result == tmp_path
