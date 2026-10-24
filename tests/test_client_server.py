# =============================================================================
# HYDRA-UMC EDITOR-URDF - tests/test_client_server.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The model-submission client against a small real HTTP server that keeps the contract of HYDRA-UMC-SERVER
# (login, list, submit with 409 on a name collision, download): the token on the calls, the round trip of a model
# with its meshes, the refusals and what the client does with them. Runs without a display.
# =============================================================================
from __future__ import annotations

import base64
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from hydra_editor_urdf.models import Link, MeshGeometry, Robot, Visual
from hydra_editor_urdf.server.client import StudioClient, StudioClientError
from hydra_editor_urdf.urdf.parser import parse_urdf_file

TOKEN = "token-of-the-admin"


class FakeServer:
    """Keeps the submitted models, the calls it got and what a test wants it to do."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str | None, dict | None]] = []  # method, path, Authorization header, body
        self.models: dict[tuple[str, str], dict] = {}
        self.require_sign_in_to_list = False
        self.login_status = 200
        self.login_token: str | None = TOKEN
        self.download_override: dict | None = None


def _start(server: FakeServer) -> tuple[HTTPServer, int]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args) -> None:  # noqa: D401 - silence
            pass

        def _read(self) -> dict | None:
            length = int(self.headers.get("Content-Length") or 0)
            return json.loads(self.rfile.read(length)) if length else None

        def _send(self, status: int, body: object) -> None:
            payload = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _signed_in(self) -> bool:
            return self.headers.get("Authorization") == f"Bearer {TOKEN}"

        def do_POST(self) -> None:  # noqa: N802
            body = self._read()
            server.calls.append(("POST", self.path, self.headers.get("Authorization"), body))
            if self.path == "/api/login":
                if server.login_status != 200:
                    return self._send(server.login_status, {"error": "bad credentials"})
                return self._send(200, {"token": server.login_token} if server.login_token else {})
            if self.path == "/api/models/submit":
                if not self._signed_in():
                    return self._send(401, {"error": "Authentication required"})
                assert body is not None
                key = (body["category"], body["name"])
                if key in server.models and not body.get("overwrite"):
                    return self._send(409, {"error": f"A model named {body['name']} already exists"})
                server.models[key] = body
                return self._send(200, {"success": True, "slug": body["name"]})
            self._send(404, {"error": "no such route"})

        def do_GET(self) -> None:  # noqa: N802
            server.calls.append(("GET", self.path, self.headers.get("Authorization"), None))
            if self.path == "/api/models":
                if server.require_sign_in_to_list and not self._signed_in():
                    return self._send(401, {"error": "Authentication required"})
                return self._send(200, {"models": [{"category": c, "slug": n} for c, n in server.models]})
            parts = self.path.strip("/").split("/")
            if len(parts) == 5 and parts[:2] == ["api", "models"] and parts[4] == "download":
                if server.download_override is not None:
                    return self._send(200, server.download_override)
                model = server.models.get((parts[2], parts[3]))
                if model is None:
                    return self._send(404, {"error": "no such model"})
                return self._send(200, {"urdfFilename": model["urdfFilename"], "urdfXml": model["urdfXml"], "meshFiles": model["meshFiles"]})
            self._send(404, {"error": "no such route"})

    http = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=http.serve_forever, daemon=True).start()
    return http, http.server_address[1]


@pytest.fixture
def served():
    server = FakeServer()
    http, port = _start(server)
    yield server, port
    http.shutdown()
    http.server_close()


def _robot_with_mesh(tmp_path: Path) -> tuple[Robot, object]:
    mesh = tmp_path / "meshes" / "base.stl"
    mesh.parent.mkdir()
    mesh.write_bytes(b"solid x\nendsolid x\n")
    robot = Robot(name="arm")
    link = Link(name="base")
    link.visuals.append(Visual(geometry=MeshGeometry(filename="package://arm/meshes/base.stl")))
    robot.links["base"] = link
    robot.root_link = "base"
    return robot, (lambda name: mesh if name.endswith("base.stl") else None)


def test_login_keeps_the_token_and_presents_it_on_every_later_call(served) -> None:
    server, port = served
    client = StudioClient("127.0.0.1", port)
    client.login("root", "pw")
    assert client.token == TOKEN
    assert client.list_models() == []
    assert [c[2] for c in server.calls] == [None, f"Bearer {TOKEN}"]


def test_a_server_that_asks_for_a_sign_in_on_the_model_list_answers_once_signed_in(served) -> None:
    server, port = served
    server.require_sign_in_to_list = True
    client = StudioClient("127.0.0.1", port)
    with pytest.raises(StudioClientError, match="Authentication required"):
        client.list_models()
    client.login("root", "pw")
    assert client.list_models() == []


def test_a_refused_login_or_one_without_a_token_is_an_error_with_the_reason(served) -> None:
    server, port = served
    server.login_status = 401
    with pytest.raises(StudioClientError, match="bad credentials"):
        StudioClient("127.0.0.1", port).login("root", "wrong")
    server.login_status = 200
    server.login_token = None
    with pytest.raises(StudioClientError, match="no token"):
        StudioClient("127.0.0.1", port).login("root", "pw")


def test_pushing_without_signing_in_never_reaches_the_server(served) -> None:
    server, port = served
    robot = Robot(name="arm")
    robot.links["base"] = Link(name="base")
    with pytest.raises(StudioClientError, match="Not logged in"):
        StudioClient("127.0.0.1", port).push_model(robot, "robots", lambda name: None)
    assert server.calls == []


def test_a_model_goes_to_the_server_with_its_mesh_and_comes_back_whole(served, tmp_path: Path) -> None:
    server, port = served
    robot, resolver = _robot_with_mesh(tmp_path)
    client = StudioClient("127.0.0.1", port)
    client.login("root", "pw")
    assert client.push_model(robot, "robots", resolver) == "arm"
    sent = server.models[("robots", "arm")]
    assert sent["urdfFilename"] == "arm.urdf"
    assert [m["filename"] for m in sent["meshFiles"]] == ["base.stl"]
    assert base64.b64decode(sent["meshFiles"][0]["base64"]) == b"solid x\nendsolid x\n"
    assert client.list_models() == [{"category": "robots", "slug": "arm"}]

    downloaded = client.pull_model("robots", "arm", tmp_path / "pulled")
    assert downloaded == tmp_path / "pulled" / "arm" / "arm.urdf"
    assert (tmp_path / "pulled" / "arm" / "meshes" / "base.stl").read_bytes() == b"solid x\nendsolid x\n"
    assert "arm" in parse_urdf_file(downloaded).name


def test_a_name_collision_is_told_with_the_reason_and_resubmitting_with_overwrite_works(served, tmp_path: Path) -> None:
    server, port = served
    robot, resolver = _robot_with_mesh(tmp_path)
    client = StudioClient("127.0.0.1", port)
    client.login("root", "pw")
    client.push_model(robot, "robots", resolver)
    with pytest.raises(StudioClientError, match="already exists"):
        client.push_model(robot, "robots", resolver)
    assert client.push_model(robot, "robots", resolver, overwrite=True) == "arm"
    posts = [c for c in server.calls if c[1] == "/api/models/submit"]
    assert [c[3]["overwrite"] for c in posts] == [False, False, True]


def test_a_token_that_expired_is_a_clear_error_not_a_crash(served, tmp_path: Path) -> None:
    server, port = served
    robot, resolver = _robot_with_mesh(tmp_path)
    client = StudioClient("127.0.0.1", port)
    client.token = "an-old-token"
    with pytest.raises(StudioClientError, match="Authentication required"):
        client.push_model(robot, "robots", resolver)


def test_a_model_that_does_not_exist_is_a_404_with_its_reason(served, tmp_path: Path) -> None:
    server, port = served
    with pytest.raises(StudioClientError, match="no such model"):
        StudioClient("127.0.0.1", port).pull_model("robots", "ghost", tmp_path)


def test_a_hostile_download_cannot_write_outside_the_model_folder(served, tmp_path: Path) -> None:
    server, port = served
    server.download_override = {
        "urdfFilename": "../../../evil.urdf",
        "urdfXml": '<robot name="r"><link name="base"/></robot>',
        "meshFiles": [{"filename": "../../outside.stl", "base64": base64.b64encode(b"x").decode()}],
    }
    result = StudioClient("127.0.0.1", port).pull_model("robots", "arm", tmp_path / "dest")
    assert result.parent == tmp_path / "dest" / "arm"
    assert sorted(p.name for p in (tmp_path / "dest" / "arm").iterdir()) == ["evil.urdf", "meshes"]
    assert [p.name for p in (tmp_path / "dest" / "arm" / "meshes").iterdir()] == ["outside.stl"]
    assert not (tmp_path / "evil.urdf").exists() and not (tmp_path / "outside.stl").exists()


def test_a_folder_name_that_is_not_one_plain_name_is_refused_before_any_request(served, tmp_path: Path) -> None:
    server, port = served
    client = StudioClient("127.0.0.1", port)
    for slug in ("..", "a/b", "a\\b", "C:evil", ""):
        with pytest.raises(StudioClientError, match="plain folder name"):
            client.pull_model("robots", slug, tmp_path)
    assert server.calls == []


def test_a_server_that_is_not_there_is_an_error_naming_it(tmp_path: Path) -> None:
    with pytest.raises(StudioClientError, match="Couldn't reach http://127.0.0.1:1"):
        StudioClient("127.0.0.1", 1).list_models()
