# =============================================================================
# HYDRA-UMC-EDITOR-URDF - tests/test_cuts_and_encodings.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""Names outside ASCII through xacro, and GitHub downloads cut in the middle. A small script stands in for xacro and urlopen is replaced."""
from __future__ import annotations

import http.client
import io
import sys
import urllib.request

import pytest

from hydra_editor_urdf.source import github_fetcher
from hydra_editor_urdf.urdf.xacro_expand import expand_xacro


class CutAnswer(io.BytesIO):
    """An answer that stops in the middle of its body."""

    status = 200

    def read(self, *args):
        raise http.client.IncompleteRead(b"{", 100)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_names_outside_ascii_survive_a_xacro_expansion(tmp_path):
    name = "brazo_se\u00f1al_\u30ed\u30dc\u30c3\u30c8_\u201d"
    script = tmp_path / "fake_xacro.py"
    script.write_text('import sys\nsys.stdout.write(open(sys.argv[1], encoding="utf-8").read())\n', encoding="utf-8")
    source = tmp_path / "robot.urdf.xacro"
    source.write_text(f'<robot name="{name}"></robot>', encoding="utf-8")
    assert name in expand_xacro(source, command=[sys.executable, str(script)])


@pytest.mark.parametrize("error", [ConnectionResetError("reset"), http.client.IncompleteRead(b"PK", 100)], ids=lambda e: type(e).__name__)
def test_a_download_cut_in_the_middle_is_a_message_and_leaves_no_half_file(monkeypatch, tmp_path, error):
    class Half(CutAnswer):
        sent = False

        def read(self, *args):
            if not self.sent:
                self.sent = True
                return b"PK\x03\x04half"
            raise error

    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: Half())
    target = tmp_path / "repo.zip"
    with pytest.raises(github_fetcher.GithubFetchError):
        github_fetcher._download_zipball("owner", "repo", "main", target)
    assert not target.exists()


def test_a_cut_answer_about_the_default_branch_is_a_message(monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: CutAnswer())
    with pytest.raises(github_fetcher.GithubFetchError):
        github_fetcher.resolve_default_branch("owner", "repo")
