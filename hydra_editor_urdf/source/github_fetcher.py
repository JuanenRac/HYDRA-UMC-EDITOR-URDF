# =============================================================================
# HYDRA-UMC EDITOR-URDF - source/github_fetcher.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Pulls a public GitHub repository's source tree down to a local folder
# given just its URL - the "coge de un GitHub concreto" half of the
# owner's own spec. Deliberately does NOT shell out to `git clone`: that
# would make a `git` install a hard runtime dependency of this app on
# both Windows and Linux, for something a plain HTTPS download already
# does - GitHub serves a zipball of any branch/tag/commit at
# codeload.github.com with no authentication needed for a public repo,
# so this uses stdlib `urllib.request` + `zipfile` only, no new
# third-party dependency either.
#
# Only public repos are supported - no token/credential handling exists
# here. A private repo's zipball 404s the same as a nonexistent one from
# this module's own point of view; GithubFetchError's message doesn't
# try to distinguish the two since codeload's own response doesn't
# reliably let it.
# =============================================================================
from __future__ import annotations

import json
import re
import shutil
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

USER_AGENT = "HYDRA-UMC-EDITOR-URDF (github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)"
REQUEST_TIMEOUT_S = 20.0

# Matches the handful of real-world forms a user is likely to paste:
#   https://github.com/owner/repo
#   https://github.com/owner/repo.git
#   https://github.com/owner/repo/tree/some-branch
#   https://github.com/owner/repo/tree/some-branch/sub/dir  (sub/dir ignored - fetches the whole repo, not a subfolder)
#   git@github.com:owner/repo.git
#   owner/repo   (bare shorthand)
_GITHUB_URL_RE = re.compile(
    r"^(?:https?://github\.com/|git@github\.com:)?"
    r"(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+?)"
    r"(?:\.git)?"
    r"(?:/tree/(?P<ref>[A-Za-z0-9_.\-/]+?)(?:/.*)?)?"
    r"/?$"
)


class GithubFetchError(Exception):
    """Always carries a human-readable message - this is what
    ui/panels/source_panel.py shows directly to the operator."""


def parse_github_url(url_or_shorthand: str) -> tuple[str, str, str | None]:
    """Returns (owner, repo, ref) - ref is None if the URL didn't name
    one explicitly (via /tree/<ref>), meaning "use the repo's own default
    branch" (resolved separately, see resolve_default_branch below)."""
    text = url_or_shorthand.strip()
    match = _GITHUB_URL_RE.match(text)
    if not match:
        raise GithubFetchError(
            f"{url_or_shorthand!r} doesn't look like a GitHub repo URL - expected something like "
            "https://github.com/owner/repo or owner/repo."
        )
    return match.group("owner"), match.group("repo"), match.group("ref")


def resolve_default_branch(owner: str, repo: str) -> str:
    """GET https://api.github.com/repos/{owner}/{repo} - unauthenticated
    GitHub API access is rate-limited to 60 requests/hour per source IP,
    which is generous for an app that calls this once per "fetch from
    GitHub" click, not in a loop."""
    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    request = urllib.request.Request(api_url, headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_S) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise GithubFetchError(f"GitHub repo {owner}/{repo} not found (or it's private - this app only fetches public repos).") from e
        raise GithubFetchError(f"GitHub API request failed: HTTP {e.code}") from e
    except (urllib.error.URLError, TimeoutError) as e:
        raise GithubFetchError(f"Couldn't reach GitHub: {e}") from e
    branch = data.get("default_branch")
    if not branch:
        raise GithubFetchError(f"GitHub API response for {owner}/{repo} had no default_branch field.")
    return branch


def _download_zipball(owner: str, repo: str, ref: str, dest_zip: Path) -> None:
    # codeload accepts both branch and tag names under refs/heads and
    # refs/tags respectively - a plain /zip/<ref> without either prefix
    # also works for the common case and is what's used here, since this
    # app has no reliable way to know ahead of time whether `ref` is a
    # branch or a tag (a resolved default branch always is one; anything
    # the operator typed explicitly after /tree/ could be either).
    url = f"https://codeload.github.com/{owner}/{repo}/zip/{ref}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_S) as resp, open(dest_zip, "wb") as f:
            shutil.copyfileobj(resp, f)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise GithubFetchError(f"{owner}/{repo}@{ref} not found - check the repo exists, is public, and the branch/tag name is right.") from e
        raise GithubFetchError(f"Download failed: HTTP {e.code}") from e
    except (urllib.error.URLError, TimeoutError) as e:
        raise GithubFetchError(f"Couldn't reach GitHub: {e}") from e


def fetch_github_repo(url_or_shorthand: str, work_dir: str | Path) -> Path:
    """Downloads and extracts the given repo into a fresh subfolder of
    `work_dir`, returns the path to the extracted repo root (the single
    top-level folder GitHub's own zipball always contains, named
    `{repo}-{ref-with-slashes-replaced-by-dashes}`). `work_dir` itself is
    NOT cleared first - a previous fetch's own extracted folder is left
    alone, so re-fetching the same repo/ref twice just leaves 2 (or
    overwrites one, if the resulting folder name collides) rather than
    silently deleting anything the operator hasn't been told about, per
    [[feedback_no_permanent_delete]] applied to this app's own scratch
    space too even though it's not the operator's real project files."""
    owner, repo, ref = parse_github_url(url_or_shorthand)
    if ref is None:
        ref = resolve_default_branch(owner, repo)

    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    zip_path = work_dir / f"_{owner}_{repo}_{ref.replace('/', '_')}.zip"

    _download_zipball(owner, repo, ref, zip_path)

    try:
        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
            if not names:
                raise GithubFetchError(f"Downloaded archive for {owner}/{repo}@{ref} is empty.")
            top_level = names[0].split("/", 1)[0]
            zf.extractall(work_dir)
    except zipfile.BadZipFile as e:
        raise GithubFetchError(f"Downloaded file for {owner}/{repo}@{ref} isn't a valid zip archive.") from e
    finally:
        zip_path.unlink(missing_ok=True)  # the zip itself is scratch, not the extracted source - safe to remove unconditionally

    extracted_root = work_dir / top_level
    if not extracted_root.is_dir():
        raise GithubFetchError(f"Extracted archive for {owner}/{repo}@{ref} didn't produce the expected folder {top_level!r}.")
    return extracted_root
