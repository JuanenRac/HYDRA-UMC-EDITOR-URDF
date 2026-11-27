"""The address of the catalog server and the limits of a repository brought from GitHub."""

import io
import zipfile

import pytest

from hydra_editor_urdf.server.client import StudioClient, StudioClientError
from hydra_editor_urdf.source import github_fetcher as gf


@pytest.mark.parametrize(
    ("host", "url", "clear"),
    [
        ("robot.local", "http://robot.local:3000", True),
        ("127.0.0.1", "http://127.0.0.1:3000", False),
        ("https://robot.local", "https://robot.local:3000", False),
        ("https://robot.local:8443/", "https://robot.local:8443", False),
    ],
)
def test_the_address_may_carry_a_scheme(host, url, clear):
    client = StudioClient(host, 3000)
    assert client.base_url == url and client.sends_secrets_in_the_clear is clear


@pytest.mark.parametrize("host", ["ftp://x", "https://", "https://user@x", "https://x/path", "https://x:port"])
def test_an_unusable_address_is_said_when_it_is_used(host):
    with pytest.raises(StudioClientError):
        StudioClient(host, 3000).list_models()


def test_a_download_past_the_limit_is_cut():
    out = io.BytesIO()
    with pytest.raises(gf.GithubFetchError, match="larger than the limit"):
        gf._copy_bounded(io.BytesIO(b"x" * 10), out, 5, "repo")
    gf._copy_bounded(io.BytesIO(b"x" * 10), out, 0, "repo")  # 0: no limit


def _zip(*members):
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as zf:
        for info, content in members:
            zf.writestr(info, content)
    return zipfile.ZipFile(io.BytesIO(data.getvalue()))


def test_too_many_files_too_many_bytes_and_links_are_refused(monkeypatch):
    monkeypatch.setattr(gf, "load_config", lambda: {"github_max_files": 1})
    with pytest.raises(gf.GithubFetchError, match="github_max_files"):
        gf._check_archive(_zip(("a", "1"), ("b", "2")), "repo")
    monkeypatch.setattr(gf, "load_config", lambda: {"github_max_extracted_mb": 1})
    with pytest.raises(gf.GithubFetchError, match="github_max_extracted_mb"):
        gf._check_archive(_zip(("a", "x" * (2 * 1024 * 1024))), "repo")
    monkeypatch.setattr(gf, "load_config", lambda: {})
    link = zipfile.ZipInfo("repo/link")
    link.external_attr = 0o120777 << 16
    with pytest.raises(gf.GithubFetchError, match="holds a link"):
        gf._check_archive(_zip((link, "target")), "repo")
    gf._check_archive(_zip(("repo/a", "1")), "repo")
