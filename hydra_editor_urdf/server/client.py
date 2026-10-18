# =============================================================================
# HYDRA-UMC EDITOR-URDF - server/client.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# Talks to HYDRA-UMC-SERVER's own model-submission contract (server.ts's
# POST /api/models/submit, GET /api/models, GET /api/models/:category/:slug/
# download - see that project's own docs/REMOTE_API.md and server.ts for
# the authoritative contract, this comment can drift from it the same way
# every other client in this ecosystem's own comments admit theirs can).
# NOTE: this contract used to be implemented
# inside HYDRA-UMC-STUDIO's own process - it now lives in the separate
# HYDRA-UMC-SERVER repo (STUDIO is a pure static frontend that talks to
# it over the network). The request/response contract itself (every field
# name below, the 409-on-collision behavior, requireAdmin gating) is
# unchanged by that split - confirmed field-by-field against the real,
# current HYDRA-UMC-SERVER/src/server.ts. This client doesn't hardcode a
# host - the operator points ui/panels/upload_panel.py's own host:port
# fields at wherever that server is actually running.
# stdlib `urllib.request` only, same reasoning as source/github_fetcher.py:
# one more HTTP call doesn't justify a new dependency (httpx/requests) this
# project doesn't otherwise need. Synchronous/blocking - callers (upload_panel.py)
# run these on a background QThread, same pattern source_panel.py already
# uses for the GitHub fetch.
# =============================================================================
from __future__ import annotations

import base64
import binascii
import http.client
import json
import urllib.error
import urllib.request
from pathlib import Path

from hydra_editor_urdf.models import Robot
from hydra_editor_urdf.source.scan import MESH_EXTENSIONS
from hydra_editor_urdf.urdf.writer import robot_to_urdf_string

REQUEST_TIMEOUT_S = 15.0


class StudioClientError(Exception):
    """Always carries a human-readable message - shown directly in
    ui/panels/upload_panel.py."""


class StudioClient:
    """One instance per server the operator has pointed this app at -
    holds the base URL and bearer token (obtained via login()) needed for
    every subsequent call. Mirrors HYDRA-UMC SUITE's own HydraConnection
    in spirit (host/port + token + a handful of REST calls) but far
    smaller, since this app only ever needs the 4 endpoints below, not a
    live bidirectional sync."""

    def __init__(self, host: str, port: int = 3000):
        self.base_url = f"http://{host}:{port}"
        self.token: str | None = None

    def _request(self, method: str, path: str, body: dict | None = None, auth: bool = False) -> dict:
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Content-Type": "application/json"}
        if auth:
            if not self.token:
                raise StudioClientError("Not logged in - call login() first.")
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_S) as resp:
                answer = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            message = f"HTTP {e.code}"
            try:
                payload = json.loads(e.read().decode("utf-8"))
                if isinstance(payload, dict) and isinstance(payload.get("error"), str):
                    message = payload["error"]
            except (ValueError, OSError, http.client.HTTPException):
                pass
            raise StudioClientError(f"{self.base_url}{path}: {message}") from e
        except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException) as e:
            raise StudioClientError(f"Couldn't reach {self.base_url}: {e}") from e
        except ValueError as e:  # not JSON, or not UTF-8: a proxy or captive-portal page, say
            raise StudioClientError(f"{self.base_url}{path}: the answer is not valid JSON") from e
        if not isinstance(answer, dict):
            raise StudioClientError(f"{self.base_url}{path}: the answer is not a JSON object")
        return answer

    def login(self, username: str, password: str) -> None:
        """POST /api/login - only an `admin`-role token can actually use
        push_model()/pull_model() below (HYDRA-UMC-SERVER's own server.ts,
        requireAdmin on POST /api/models/submit), so this app is only
        really usable against an admin account, same as every other
        admin-only feature reachable from STUDIO's own UI (Config > Users,
        Config > Remote Access) - STUDIO's frontend is what the operator
        sees, but the account/token check itself lives in SERVER now."""
        data = self._request("POST", "/api/login", {"username": username, "password": password})
        token = data.get("token")
        if not isinstance(token, str) or not token:
            raise StudioClientError("Login succeeded but the server returned no token.")
        self.token = token

    def list_models(self) -> list[dict]:
        """GET /api/models - every model already submitted, regardless of
        whether THIS client submitted it. No auth needed, matches the
        rest of this ecosystem's own GET-is-open convention."""
        data = self._request("GET", "/api/models")
        models = data.get("models")
        return models if isinstance(models, list) else []

    def push_model(self, robot: Robot, category: str, mesh_resolver, overwrite: bool = False) -> str:
        """POST /api/models/submit - serializes `robot` back to URDF XML
        (urdf/writer.py) and base64-encodes every mesh file its own
        <mesh filename> references (resolved via `mesh_resolver`, the
        same function source/scan.py built when the model was first
        loaded) inline in the JSON body. Returns the server-assigned slug
        on success. Raises StudioClientError with the server's own 409
        message (a name collision) if `overwrite` isn't set - the
        operator decides whether to resubmit with overwrite=True or pick
        a different name, this method never guesses."""
        urdf_xml = robot_to_urdf_string(robot)
        mesh_files: list[dict] = []
        seen_filenames: set[str] = set()
        for link in robot.links.values():
            for visual in link.visuals:
                from hydra_editor_urdf.models import MeshGeometry  # local import - avoids a module-level cycle with models.py's own light footprint
                if not isinstance(visual.geometry, MeshGeometry):
                    continue
                resolved = mesh_resolver(visual.geometry.filename)
                if resolved is None or Path(resolved).suffix.lower() not in MESH_EXTENSIONS:
                    continue  # only mesh files are ever read and uploaded
                out_name = Path(visual.geometry.filename).name
                if out_name in seen_filenames:
                    continue  # same mesh referenced by more than one visual - upload it once
                seen_filenames.add(out_name)
                mesh_bytes = Path(resolved).read_bytes()
                mesh_files.append({"filename": out_name, "base64": base64.b64encode(mesh_bytes).decode("ascii")})

        body = {
            "name": robot.name,
            "category": category,
            "urdfFilename": f"{robot.name}.urdf",
            "urdfXml": urdf_xml,
            "meshFiles": mesh_files,
            "overwrite": overwrite,
        }
        data = self._request("POST", "/api/models/submit", body, auth=True)
        slug = data.get("slug", robot.name)
        return slug if isinstance(slug, str) and slug else robot.name

    def pull_model(self, category: str, slug: str, dest_dir: str | Path) -> Path:
        """GET /api/models/:category/:slug/download - writes the URDF +
        mesh files into a fresh folder under `dest_dir`, returns the URDF
        file's own path (ready to hand straight to
        app.py's own load_urdf_file()) - this is the "extract, edit,
        resend" round-trip half of the owner's own spec."""
        # The slug comes from the server's own model list and becomes a folder
        # name below, so it must be one plain name and nothing else.
        if not slug or slug in (".", "..") or Path(slug).name != slug or "\\" in slug or ":" in slug:
            raise StudioClientError(f"The server sent a model name that is not a plain folder name: {slug!r}")
        data = self._request("GET", f"/api/models/{category}/{slug}/download")
        urdf_xml = data.get("urdfXml", "")
        if not isinstance(urdf_xml, str):
            raise StudioClientError("The server's download answer has no URDF text.")
        # `urdfFilename` and every mesh `filename` come straight from the server's
        # JSON, unlike every other name this app writes to disk (picked in a
        # native dialog, or resolved against a real file by source/scan.py). A
        # malformed or compromised answer such as "../../../startup/evil.dll"
        # would write outside the model folder like an unsanitised zip entry;
        # Path(...).name strips any directory part first, so every write lands
        # inside the folder whatever the server sent.
        raw_urdf_name = data.get("urdfFilename")
        urdf_filename = (Path(raw_urdf_name).name if isinstance(raw_urdf_name, str) else "") or f"{slug}.urdf"
        mesh_files = data.get("meshFiles") or []
        if not isinstance(mesh_files, list):
            raise StudioClientError("The server's download answer has a mesh list that is not a list.")

        # Check every mesh entry before anything is written, so a bad answer
        # does not leave half a model on disk.
        meshes: list[tuple[str, bytes]] = []
        for mf in mesh_files:
            if not isinstance(mf, dict):
                raise StudioClientError("The server's download answer has a mesh entry that is not an object.")
            filename = mf.get("filename")
            b64 = mf.get("base64")
            if not filename or not b64:
                continue
            if not isinstance(filename, str) or not isinstance(b64, str):
                raise StudioClientError("The server's download answer has a mesh entry with a name or data that is not text.")
            safe_name = Path(filename).name
            if not safe_name:
                continue
            try:
                content = base64.b64decode(b64, validate=True)
            except (binascii.Error, ValueError) as e:
                raise StudioClientError(f"The server sent mesh data for {safe_name} that is not valid base64.") from e
            meshes.append((safe_name, content))

        out_dir = Path(dest_dir) / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        urdf_path = out_dir / urdf_filename
        urdf_path.write_text(urdf_xml, encoding="utf-8")

        if meshes:
            mesh_dir = out_dir / "meshes"
            mesh_dir.mkdir(exist_ok=True)
            for safe_name, content in meshes:
                (mesh_dir / safe_name).write_bytes(content)

        return urdf_path
