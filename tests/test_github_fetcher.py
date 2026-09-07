# =============================================================================
# HYDRA-UMC EDITOR-URDF - tests/test_github_fetcher.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Real unit tests for hydra_editor_urdf/source/github_fetcher.py.
# parse_github_url() is pure regex logic, tested directly against every
# real-world form its own docstring lists. resolve_default_branch() and
# fetch_github_repo() touch the real network (urllib) - tested here with
# urllib.request.urlopen mocked at the module boundary, never a real
# network call, per this ecosystem's own established pattern for
# HTTP-calling pure logic.
# =============================================================================
from __future__ import annotations

import io
import json
import urllib.error
import zipfile
from unittest.mock import patch

import pytest

from hydra_editor_urdf.source.github_fetcher import (
    GithubFetchError,
    fetch_github_repo,
    parse_github_url,
    resolve_default_branch,
)


# --- parse_github_url --------------------------------------------------


@pytest.mark.parametrize(
    "url,expected_owner,expected_repo,expected_ref",
    [
        ("https://github.com/ros-industrial/universal_robot", "ros-industrial", "universal_robot", None),
        ("https://github.com/ros-industrial/universal_robot.git", "ros-industrial", "universal_robot", None),
        ("https://github.com/ros-industrial/universal_robot/tree/noetic-devel", "ros-industrial", "universal_robot", "noetic-devel"),
        (
            "https://github.com/ros-industrial/universal_robot/tree/noetic-devel/ur_description",
            "ros-industrial",
            "universal_robot",
            "noetic-devel",
        ),
        ("git@github.com:ROBOTIS-GIT/open_manipulator.git", "ROBOTIS-GIT", "open_manipulator", None),
        ("JuanenRac/HYDRA-UMC-EDITOR-URDF", "JuanenRac", "HYDRA-UMC-EDITOR-URDF", None),
        ("  JuanenRac/HYDRA-UMC-EDITOR-URDF  ", "JuanenRac", "HYDRA-UMC-EDITOR-URDF", None),
        ("https://github.com/owner/repo/", "owner", "repo", None),
    ],
)
def test_parse_github_url_real_world_forms(url, expected_owner, expected_repo, expected_ref):
    owner, repo, ref = parse_github_url(url)
    assert owner == expected_owner
    assert repo == expected_repo
    assert ref == expected_ref


@pytest.mark.parametrize(
    "garbage",
    [
        "",
        "not a url at all",
        "https://gitlab.com/owner/repo",
        "just-one-segment",
    ],
)
def test_parse_github_url_rejects_non_github_input(garbage):
    with pytest.raises(GithubFetchError):
        parse_github_url(garbage)


# --- resolve_default_branch (network mocked) --------------------------------


class _FakeResponse:
    """Stands in for the object urlopen()'s own context manager yields -
    wraps a real BytesIO so both `resp.read()` (resolve_default_branch's
    own whole-body read) and `shutil.copyfileobj(resp, f)` (_download_
    zipball's own chunked read, which calls `.read(length)` in a loop
    until it gets back an empty chunk) work exactly like the real thing."""

    def __init__(self, payload: bytes):
        self._buffer = io.BytesIO(payload)

    def read(self, *args):
        return self._buffer.read(*args)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


def test_resolve_default_branch_returns_the_real_field():
    body = json.dumps({"default_branch": "main"}).encode("utf-8")
    with patch("urllib.request.urlopen", return_value=_FakeResponse(body)):
        assert resolve_default_branch("owner", "repo") == "main"


def test_resolve_default_branch_404_is_a_clear_not_found_error():
    error = urllib.error.HTTPError(url="", code=404, msg="Not Found", hdrs=None, fp=None)
    with patch("urllib.request.urlopen", side_effect=error):
        with pytest.raises(GithubFetchError, match="not found"):
            resolve_default_branch("owner", "repo")


def test_resolve_default_branch_other_http_error_reports_the_status_code():
    error = urllib.error.HTTPError(url="", code=500, msg="Server Error", hdrs=None, fp=None)
    with patch("urllib.request.urlopen", side_effect=error):
        with pytest.raises(GithubFetchError, match="HTTP 500"):
            resolve_default_branch("owner", "repo")


def test_resolve_default_branch_network_error_is_a_clear_error():
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("no route to host")):
        with pytest.raises(GithubFetchError, match="Couldn't reach GitHub"):
            resolve_default_branch("owner", "repo")


def test_resolve_default_branch_missing_field_is_an_error():
    body = json.dumps({"name": "repo"}).encode("utf-8")
    with patch("urllib.request.urlopen", return_value=_FakeResponse(body)):
        with pytest.raises(GithubFetchError, match="no default_branch"):
            resolve_default_branch("owner", "repo")


# --- fetch_github_repo (network + zip extraction) ---------------------------


def _fake_zipball(top_level_name: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr(f"{top_level_name}/README.md", "hello")
        zf.writestr(f"{top_level_name}/model.urdf", "<robot/>")
    return buffer.getvalue()


def test_fetch_github_repo_downloads_and_extracts_with_explicit_ref(tmp_path):
    zip_bytes = _fake_zipball("universal_robot-noetic-devel")
    with patch("urllib.request.urlopen", return_value=_FakeResponse(zip_bytes)):
        result = fetch_github_repo(
            "https://github.com/ros-industrial/universal_robot/tree/noetic-devel", tmp_path
        )
    assert result == tmp_path / "universal_robot-noetic-devel"
    assert (result / "model.urdf").is_file()
    # the scratch zip itself is cleaned up, only the extracted folder remains
    assert list(tmp_path.glob("*.zip")) == []


def test_fetch_github_repo_resolves_default_branch_when_ref_is_omitted(tmp_path):
    branch_response = _FakeResponse(json.dumps({"default_branch": "main"}).encode("utf-8"))
    zip_response = _FakeResponse(_fake_zipball("open_manipulator-main"))
    with patch("urllib.request.urlopen", side_effect=[branch_response, zip_response]):
        result = fetch_github_repo("ROBOTIS-GIT/open_manipulator", tmp_path)
    assert result == tmp_path / "open_manipulator-main"


def test_fetch_github_repo_404_during_download_is_a_clear_error(tmp_path):
    error = urllib.error.HTTPError(url="", code=404, msg="Not Found", hdrs=None, fp=None)
    with patch("urllib.request.urlopen", side_effect=error):
        with pytest.raises(GithubFetchError, match="not found"):
            fetch_github_repo("https://github.com/owner/repo/tree/some-ref", tmp_path)


def test_fetch_github_repo_bad_zip_is_a_clear_error(tmp_path):
    with patch("urllib.request.urlopen", return_value=_FakeResponse(b"not actually a zip file")):
        with pytest.raises(GithubFetchError, match="isn't a valid zip"):
            fetch_github_repo("https://github.com/owner/repo/tree/some-ref", tmp_path)
    # even on failure, the scratch zip must not be left behind
    assert list(tmp_path.glob("*.zip")) == []


def test_fetch_github_repo_empty_archive_is_a_clear_error(tmp_path):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w"):
        pass  # a real, valid, but completely empty zip
    with patch("urllib.request.urlopen", return_value=_FakeResponse(buffer.getvalue())):
        with pytest.raises(GithubFetchError, match="is empty"):
            fetch_github_repo("https://github.com/owner/repo/tree/some-ref", tmp_path)
