# =============================================================================
# HYDRA-UMC EDITOR-URDF - tests/test_edge_cases.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# Hostile files and hostile server answers: URDFs that are not UTF-8, meshes
# whose header lies, a model server that answers with something that is not a
# model, and the controller's behaviour on each of them. Runs without a display.
# =============================================================================
from __future__ import annotations

import base64
import json
import struct
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from hydra_editor_urdf.models import BoxGeometry, Link, MeshGeometry, Robot, Visual
from hydra_editor_urdf.render.mesh import MalformedMeshFile, load_mesh_file
from hydra_editor_urdf.server.client import StudioClient, StudioClientError
from hydra_editor_urdf.urdf.parser import UrdfParseError, parse_urdf_file, parse_urdf_string

BAD_UTF8 = b"\xff\xfe\x00\xc3\x28 not utf-8"
ROBOT = '<robot name="r"><link name="base"/></robot>'


# ------------------------------------------------------------------ URDF files


def test_a_urdf_file_that_is_not_utf8_is_a_parse_error(tmp_path: Path) -> None:
    path = tmp_path / "latin1.urdf"
    path.write_bytes('<robot name="r"><!-- caf\xe9 --><link name="base"/></robot>'.encode("latin-1"))
    with pytest.raises(UrdfParseError, match="UTF-8"):
        parse_urdf_file(path)


def test_a_binary_file_is_a_parse_error(tmp_path: Path) -> None:
    path = tmp_path / "junk.urdf"
    path.write_bytes(BAD_UTF8)
    with pytest.raises(UrdfParseError):
        parse_urdf_file(path)


def test_a_missing_or_directory_path_is_a_parse_error(tmp_path: Path) -> None:
    with pytest.raises(UrdfParseError):
        parse_urdf_file(tmp_path / "nope.urdf")
    with pytest.raises(UrdfParseError):
        parse_urdf_file(tmp_path)


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   ",
        "not xml",
        "<robot",
        "<robot></robot>",
        "<other><link name='a'/></other>",
        '<robot><link/></robot>',
        '<robot><link name="a"/><link name="a"/></robot>',
        '<robot><link name="a"/><joint name="j" type="warp"><parent link="a"/><child link="a"/></joint></robot>',
        '<robot><link name="a"/><joint name="j" type="fixed"><parent link="a"/></joint></robot>',
        '<robot><link name="a"/><joint type="fixed"><parent link="a"/><child link="a"/></joint></robot>',
        '<robot><link name="a"><visual><geometry><box size="1 2"/></geometry></visual></link></robot>',
        '<robot><link name="a"><visual><geometry><box size="1 2 nan"/></geometry></visual></link></robot>',
        '<robot><link name="a"><visual><geometry><sphere radius="inf"/></geometry></visual></link></robot>',
        '<robot><link name="a"><inertial><mass value="x"/></inertial></link></robot>',
        '<robot><link name="a"/><joint name="j" type="revolute"><parent link="a"/><child link="a"/><limit lower="-inf"/></joint></robot>',
        '<?xml version="1.0"?><!DOCTYPE robot [<!ENTITY x "y">]><robot><link name="a"/></robot>',
        '<robot><link name="a"/>&xxe;</robot>',
        '<!doctype robot><robot><link name="a"/></robot>',
    ],
)
def test_malformed_urdf_text_is_always_a_parse_error(text: str) -> None:
    with pytest.raises(UrdfParseError):
        parse_urdf_string(text)


def test_a_urdf_with_a_cycle_still_parses_and_terminates() -> None:
    from hydra_editor_urdf.render.kinematics import compute_link_world_transforms

    robot = parse_urdf_string(
        '<robot name="r"><link name="a"/><link name="b"/><link name="c"/>'
        '<joint name="j1" type="fixed"><parent link="a"/><child link="b"/></joint>'
        '<joint name="j2" type="fixed"><parent link="b"/><child link="c"/></joint>'
        '<joint name="j3" type="fixed"><parent link="c"/><child link="b"/></joint></robot>'
    )
    assert set(compute_link_world_transforms(robot, {})) == {"a", "b", "c"}


# ------------------------------------------------------------------ mesh files


def _binary_stl(triangle_count_in_header: int, triangles: int) -> bytes:
    body = b"".join(struct.pack("<12fH", 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0) for _ in range(triangles))
    return b"\0" * 80 + struct.pack("<I", triangle_count_in_header) + body


@pytest.mark.parametrize(
    "content",
    [
        # the header promises four billion triangles
        b"\0" * 80 + struct.pack("<I", 4_000_000_000) + b"\0" * 50,
        # a facet with a vertex missing
        b"solid x\nfacet normal 0 0 1\nouter loop\nvertex 0 0 0\nvertex 1 0 0\nendloop\nendfacet\nendsolid x\n",
        # a coordinate that is not a number
        b"solid x\nfacet normal 0 0 1\nouter loop\nvertex a b c\nvertex 1 0 0\nvertex 0 1 0\nendloop\nendfacet\nendsolid x\n",
        b"solid x\nendsolid x\n",
        b"",
        b"x",
        b"\0" * 80,
    ],
)
def test_a_broken_stl_is_reported_as_a_malformed_mesh(tmp_path: Path, content: bytes) -> None:
    path = tmp_path / "broken.stl"
    path.write_bytes(content)
    with pytest.raises(MalformedMeshFile):
        load_mesh_file(path)


def test_a_binary_stl_cut_short_is_a_malformed_mesh(tmp_path: Path) -> None:
    path = tmp_path / "cut.stl"
    path.write_bytes(_binary_stl(triangle_count_in_header=5, triangles=2))
    with pytest.raises(MalformedMeshFile, match="cut short"):
        load_mesh_file(path)


def test_a_complete_binary_stl_loads(tmp_path: Path) -> None:
    path = tmp_path / "ok.stl"
    path.write_bytes(_binary_stl(triangle_count_in_header=3, triangles=3))
    assert load_mesh_file(path).triangle_count == 3


def test_a_binary_stl_with_trailing_bytes_loads(tmp_path: Path) -> None:
    path = tmp_path / "padded.stl"
    path.write_bytes(_binary_stl(triangle_count_in_header=2, triangles=2) + b"\0" * 16)
    assert load_mesh_file(path).triangle_count == 2


def test_a_binary_stl_whose_header_starts_with_solid_loads(tmp_path: Path) -> None:
    path = tmp_path / "solid_header.stl"
    path.write_bytes(b"solid exported by a tool".ljust(80, b"\0") + _binary_stl(1, 1)[80:])
    assert load_mesh_file(path).triangle_count == 1


@pytest.mark.parametrize(
    "body",
    [
        "v nan 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n",
        "v 1e999 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n",
        "v a b c\nv 1 0 0\nv 0 1 0\nf 1 2 3\n",
        "v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 six\n",
        "v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 4\n",
        "v 0 0 0\nv 1 0 0\nv 0 1 0\nf 0 1 2\n",
        "v 0 0 0\nv 1 0 0\nv 0 1 0\nf -9 1 2\n",
        "",
    ],
)
def test_hostile_obj_files_are_malformed_meshes(tmp_path: Path, body: str) -> None:
    path = tmp_path / "m.obj"
    path.write_text(body, encoding="utf-8")
    with pytest.raises(MalformedMeshFile):
        load_mesh_file(path)


def test_an_obj_that_is_not_utf8_still_loads_its_geometry(tmp_path: Path) -> None:
    path = tmp_path / "m.obj"
    path.write_bytes(b"# caf\xe9\nv 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n")
    assert load_mesh_file(path).triangle_count == 1


# ---------------------------------------------------------------- model server


class _Handler(BaseHTTPRequestHandler):
    routes: dict[tuple[str, str], tuple[int, bytes]] = {}
    seen: list[tuple[str, str, bytes]] = []

    def log_message(self, format, *args) -> None:  # noqa: A002 - base class signature
        pass

    def _answer(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        self.seen.append((self.command, self.path, body))
        status, payload = self.routes.get((self.command, self.path), (404, b'{"error":"nope"}'))
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    do_GET = do_POST = _answer


@pytest.fixture
def server():
    routes: dict[tuple[str, str], tuple[int, bytes]] = {}
    seen: list[tuple[str, str, bytes]] = []
    handler = type("Handler", (_Handler,), {"routes": routes, "seen": seen})
    httpd = HTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield httpd.server_address[1], routes, seen
    httpd.shutdown()
    httpd.server_close()
    thread.join(timeout=2)


@pytest.mark.parametrize(
    "status,body",
    [
        (200, b"<html>captive portal</html>"),
        (200, b""),
        (200, b"[]"),
        (200, b"null"),
        (200, b'"token"'),
        (200, BAD_UTF8),
        (401, b"[]"),
        (500, b'"text"'),
        (500, b"null"),
        (502, b"<html>bad gateway</html>"),
        (500, BAD_UTF8),
    ],
)
def test_login_with_a_broken_answer_is_a_readable_error(server, status: int, body: bytes) -> None:
    port, routes, _ = server
    routes[("POST", "/api/login")] = (status, body)
    client = StudioClient("127.0.0.1", port)
    with pytest.raises(StudioClientError):
        client.login("admin", "pw")
    assert client.token is None


@pytest.mark.parametrize("token", [None, "", 0, 5, ["a"], {"a": 1}, False])
def test_login_needs_a_text_token(server, token) -> None:
    port, routes, _ = server
    routes[("POST", "/api/login")] = (200, json.dumps({"token": token}).encode())
    client = StudioClient("127.0.0.1", port)
    with pytest.raises(StudioClientError):
        client.login("admin", "pw")
    assert client.token is None


def test_the_error_text_of_the_server_is_passed_on(server) -> None:
    port, routes, _ = server
    routes[("POST", "/api/login")] = (401, b'{"error":"Invalid credentials"}')
    with pytest.raises(StudioClientError, match="Invalid credentials"):
        StudioClient("127.0.0.1", port).login("admin", "bad")


def test_the_token_is_sent_as_a_bearer_and_only_after_login(server) -> None:
    port, routes, seen = server
    client = StudioClient("127.0.0.1", port)
    with pytest.raises(StudioClientError, match="Not logged in"):
        client.push_model(Robot(name="r"), "arms", lambda name: None)
    assert seen == []


@pytest.mark.parametrize("answer", [b"{}", b'{"models": 5}', b'{"models": {"a": 1}}', b'{"models": null}'])
def test_list_models_without_a_list_gives_an_empty_list(server, answer: bytes) -> None:
    port, routes, _ = server
    routes[("GET", "/api/models")] = (200, answer)
    assert StudioClient("127.0.0.1", port).list_models() == []


@pytest.mark.parametrize("answer", [b"[]", b"null", b"<html>", b""])
def test_list_models_with_an_answer_that_is_not_an_object_is_an_error(server, answer: bytes) -> None:
    port, routes, _ = server
    routes[("GET", "/api/models")] = (200, answer)
    with pytest.raises(StudioClientError):
        StudioClient("127.0.0.1", port).list_models()


def test_list_models_returns_what_the_server_lists(server) -> None:
    port, routes, _ = server
    routes[("GET", "/api/models")] = (200, b'{"models":[{"slug":"a"}]}')
    assert StudioClient("127.0.0.1", port).list_models() == [{"slug": "a"}]


def test_an_unreachable_server_is_a_readable_error() -> None:
    with pytest.raises(StudioClientError, match="Couldn't reach"):
        StudioClient("127.0.0.1", 1).list_models()


def _robot_with_meshes(tmp_path: Path) -> tuple[Robot, dict[str, Path]]:
    (tmp_path / "a.stl").write_bytes(b"AAAA")
    (tmp_path / "notes.txt").write_text("secret", encoding="utf-8")
    robot = Robot(name="arm")
    link = Link(name="base")
    link.visuals.append(Visual(geometry=MeshGeometry(filename="package://pkg/meshes/a.stl")))
    link.visuals.append(Visual(geometry=MeshGeometry(filename="again/a.stl")))  # same name, uploaded once
    link.visuals.append(Visual(geometry=MeshGeometry(filename="notes.txt")))  # not a mesh
    link.visuals.append(Visual(geometry=MeshGeometry(filename="missing.stl")))  # not found
    link.visuals.append(Visual(geometry=BoxGeometry(size=(1, 1, 1))))
    robot.links["base"] = link
    files = {
        "package://pkg/meshes/a.stl": tmp_path / "a.stl",
        "again/a.stl": tmp_path / "a.stl",
        "notes.txt": tmp_path / "notes.txt",
    }
    return robot, files


def test_push_uploads_only_real_mesh_files_once_each(server, tmp_path: Path) -> None:
    port, routes, seen = server
    routes[("POST", "/api/login")] = (200, b'{"token":"abc"}')
    routes[("POST", "/api/models/submit")] = (200, b'{"slug":"arm-1"}')
    robot, files = _robot_with_meshes(tmp_path)
    client = StudioClient("127.0.0.1", port)
    client.login("admin", "pw")
    slug = client.push_model(robot, "arms", lambda name: files.get(name), overwrite=True)
    assert slug == "arm-1"
    method, path, body = seen[-1]
    payload = json.loads(body)
    assert [m["filename"] for m in payload["meshFiles"]] == ["a.stl"]
    assert base64.b64decode(payload["meshFiles"][0]["base64"]) == b"AAAA"
    assert payload["overwrite"] is True and payload["category"] == "arms" and payload["name"] == "arm"


@pytest.mark.parametrize("answer", [b"[]", b"null", b"<html>"])
def test_push_with_an_answer_that_is_not_an_object_is_an_error(server, tmp_path: Path, answer: bytes) -> None:
    port, routes, _ = server
    routes[("POST", "/api/login")] = (200, b'{"token":"abc"}')
    routes[("POST", "/api/models/submit")] = (200, answer)
    robot, files = _robot_with_meshes(tmp_path)
    client = StudioClient("127.0.0.1", port)
    client.login("admin", "pw")
    with pytest.raises(StudioClientError):
        client.push_model(robot, "arms", lambda name: files.get(name))


def _download(routes, category: str, slug: str, payload: object) -> None:
    routes[("GET", f"/api/models/{category}/{slug}/download")] = (200, json.dumps(payload).encode())


def test_pull_writes_the_urdf_and_meshes_inside_the_chosen_folder(server, tmp_path: Path) -> None:
    port, routes, _ = server
    _download(routes, "arms", "arm-1", {
        "urdfXml": ROBOT,
        "urdfFilename": "arm.urdf",
        "meshFiles": [{"filename": "a.stl", "base64": base64.b64encode(b"AAAA").decode()}],
    })
    urdf = StudioClient("127.0.0.1", port).pull_model("arms", "arm-1", tmp_path / "out")
    assert urdf == tmp_path / "out" / "arm-1" / "arm.urdf"
    assert urdf.read_text(encoding="utf-8") == ROBOT
    assert (tmp_path / "out" / "arm-1" / "meshes" / "a.stl").read_bytes() == b"AAAA"


def test_pull_keeps_hostile_file_names_inside_the_folder(server, tmp_path: Path) -> None:
    port, routes, _ = server
    _download(routes, "arms", "arm-1", {
        "urdfXml": ROBOT,
        "urdfFilename": "../../escaped.urdf",
        "meshFiles": [
            {"filename": "../../../escaped.stl", "base64": base64.b64encode(b"x").decode()},
            {"filename": "C:\\Windows\\escaped2.stl", "base64": base64.b64encode(b"x").decode()},
            {"filename": "/etc/escaped3.stl", "base64": base64.b64encode(b"x").decode()},
        ],
    })
    out = tmp_path / "out"
    StudioClient("127.0.0.1", port).pull_model("arms", "arm-1", out)
    written = {p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*") if p.is_file()}
    assert all(name.startswith("out/arm-1/") for name in written), written


@pytest.mark.parametrize("slug", ["..", "../..", "../../elsewhere", ".", "a/../../b", "/abs", "C:\\abs"])
def test_pull_refuses_a_slug_that_leads_out_of_the_folder(server, tmp_path: Path, slug: str) -> None:
    port, routes, _ = server
    _download(routes, "arms", slug, {"urdfXml": ROBOT, "urdfFilename": "arm.urdf"})
    out = tmp_path / "out"
    with pytest.raises(StudioClientError):
        StudioClient("127.0.0.1", port).pull_model("arms", slug, out)
    assert [p for p in tmp_path.rglob("*") if p.is_file()] == []


@pytest.mark.parametrize(
    "payload",
    [
        [],
        None,
        {"urdfXml": 5},
        {"urdfXml": None, "urdfFilename": "a.urdf"},
        {"urdfXml": ROBOT, "meshFiles": 5},
        {"urdfXml": ROBOT, "meshFiles": ["not an object"]},
        {"urdfXml": ROBOT, "meshFiles": [{"filename": "a.stl", "base64": "!!! not base64 !!!"}]},
        {"urdfXml": ROBOT, "meshFiles": [{"filename": 5, "base64": "QQ=="}]},
    ],
)
def test_pull_with_a_broken_answer_is_a_readable_error(server, tmp_path: Path, payload) -> None:
    port, routes, _ = server
    _download(routes, "arms", "arm-1", payload)
    with pytest.raises(StudioClientError):
        StudioClient("127.0.0.1", port).pull_model("arms", "arm-1", tmp_path / "out")


def test_pull_skips_mesh_entries_without_a_name_or_data(server, tmp_path: Path) -> None:
    port, routes, _ = server
    _download(routes, "arms", "arm-1", {
        "urdfXml": ROBOT,
        "meshFiles": [{"filename": "", "base64": "QQ=="}, {"filename": "a.stl"}, {"filename": "b.stl", "base64": ""}],
    })
    urdf = StudioClient("127.0.0.1", port).pull_model("arms", "arm-1", tmp_path / "out")
    assert urdf.name == "arm-1.urdf" and urdf.is_file()
    assert not (tmp_path / "out" / "arm-1" / "meshes").exists()


# ----------------------------------------------------------------- controller


@pytest.fixture
def controller():
    from hydra_editor_urdf.app import EditorController

    return EditorController()


def _listen(controller):
    events: dict[str, list] = {"failed": [], "loaded": [], "tree": [], "candidates": []}
    controller.load_failed.connect(events["failed"].append)
    controller.robot_loaded.connect(lambda robot, report: events["loaded"].append((robot, report)))
    controller.tree_changed.connect(lambda: events["tree"].append(1))
    controller.urdf_candidates_found.connect(lambda files, root: events["candidates"].append(files))
    return events


def test_a_urdf_that_is_not_utf8_is_reported_not_raised(controller, tmp_path: Path) -> None:
    events = _listen(controller)
    path = tmp_path / "latin1.urdf"
    path.write_bytes('<robot name="r"><!-- caf\xe9 --><link name="base"/></robot>'.encode("latin-1"))
    controller.load_urdf_file(path)
    assert len(events["failed"]) == 1 and "latin1.urdf" in events["failed"][0]
    assert controller.robot is None


def test_a_folder_without_urdf_files_is_reported(controller, tmp_path: Path) -> None:
    events = _listen(controller)
    (tmp_path / "readme.txt").write_text("x", encoding="utf-8")
    controller.load_from_local_folder(str(tmp_path))
    assert "No .urdf or .xacro files" in events["failed"][0]


def test_a_missing_local_folder_is_reported(controller, tmp_path: Path) -> None:
    events = _listen(controller)
    controller.load_from_local_folder(str(tmp_path / "gone"))
    controller.load_from_local_folder(str(tmp_path / "file.txt"))
    assert len(events["failed"]) == 2


def test_the_largest_urdf_of_a_folder_is_loaded_and_all_are_offered(controller, tmp_path: Path) -> None:
    events = _listen(controller)
    (tmp_path / "small.urdf").write_text(ROBOT, encoding="utf-8")
    (tmp_path / "big.urdf").write_text('<robot name="big"><link name="a"/><link name="b"/>' + " " * 200 + "</robot>", encoding="utf-8")
    controller.load_from_local_folder(str(tmp_path))
    assert controller.robot is not None and controller.robot.name == "big"
    assert {p.name for p in events["candidates"][0]} == {"small.urdf", "big.urdf"}
    assert len(events["loaded"]) == 1


def test_a_second_load_forgets_the_extra_mesh_folders_of_the_first(controller, tmp_path: Path) -> None:
    first = tmp_path / "first.urdf"
    first.write_text(ROBOT, encoding="utf-8")
    controller.load_urdf_file(first)
    controller.add_mesh_search_folder(tmp_path / "extra")
    assert controller._extra_mesh_roots == [tmp_path / "extra"]
    controller.add_mesh_search_folder(tmp_path / "extra")
    assert controller._extra_mesh_roots == [tmp_path / "extra"]
    controller.load_urdf_file(first)
    assert controller._extra_mesh_roots == []


def test_adding_a_mesh_folder_before_anything_is_loaded_does_nothing(controller, tmp_path: Path) -> None:
    events = _listen(controller)
    controller.add_mesh_search_folder(tmp_path)
    assert events["tree"] == []


def test_export_without_a_robot_is_refused(controller, tmp_path: Path) -> None:
    assert controller.export_urdf_string() is None
    with pytest.raises(ValueError):
        controller.export_urdf_file(tmp_path / "out.urdf")


def test_export_refuses_a_robot_that_would_not_pass_the_save_check(controller, tmp_path: Path) -> None:
    from hydra_editor_urdf.urdf.save_check import UrdfSaveError

    source = tmp_path / "in.urdf"
    source.write_text(
        '<robot name="r"><link name="a"/><link name="b"/>'
        '<joint name="j" type="revolute"><parent link="a"/><child link="b"/>'
        '<limit lower="1" upper="0" effort="1" velocity="1"/></joint></robot>',
        encoding="utf-8",
    )
    controller.load_urdf_file(source)
    target = tmp_path / "out.urdf"
    with pytest.raises(UrdfSaveError):
        controller.export_urdf_file(target)
    assert not target.exists()


def test_export_keeps_the_first_backup_of_an_existing_file(controller, tmp_path: Path) -> None:
    source = tmp_path / "robot.urdf"
    original = '<robot name="orig"><link name="base"/></robot>'
    source.write_text(original, encoding="utf-8")
    controller.load_urdf_file(source)
    controller.robot.name = "edited-once"
    controller.export_urdf_file(source)
    controller.robot.name = "edited-twice"
    controller.export_urdf_file(source)
    assert (tmp_path / "robot.urdf.bak").read_text(encoding="utf-8") == original
    assert "edited-twice" in source.read_text(encoding="utf-8")
    assert not (tmp_path / "robot.urdf.tmp").exists()


def test_selection_and_joint_values_are_announced(controller) -> None:
    selected: list = []
    values: list = []
    controller.selected_link_changed.connect(selected.append)
    controller.joint_values_changed.connect(values.append)
    controller.set_selected_link("base")
    controller.set_selected_link(None)
    controller.set_joint_value("j1", 0.5)
    controller.set_joint_value("j2", -1.0)
    assert selected == ["base", None]
    assert values == [{"j1": 0.5}, {"j1": 0.5, "j2": -1.0}]
    values[0]["j1"] = 99.0  # a listener cannot change the controller's own state
    assert controller.joint_values["j1"] == 0.5


def test_notify_tree_changed_revalidates(controller, tmp_path: Path) -> None:
    events = _listen(controller)
    controller.notify_tree_changed()  # nothing loaded: nothing to announce
    assert events["tree"] == []
    path = tmp_path / "r.urdf"
    path.write_text(ROBOT, encoding="utf-8")
    controller.load_urdf_file(path)
    controller.notify_tree_changed()
    assert events["tree"] == [1]


# ----------------------------------------------------------------------- GitHub


class _FakeResponse:
    def __init__(self, payload: bytes) -> None:
        import io

        self._buffer = io.BytesIO(payload)

    def read(self, *args):
        return self._buffer.read(*args)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


@pytest.mark.parametrize("payload", [b"<html>rate limited</html>", b"", b"[]", b"null", b'{"default_branch": 5}', b'{"default_branch": ""}', BAD_UTF8])
def test_a_broken_github_answer_is_a_readable_error(payload: bytes) -> None:
    from unittest.mock import patch

    from hydra_editor_urdf.source.github_fetcher import GithubFetchError, resolve_default_branch

    with patch("urllib.request.urlopen", return_value=_FakeResponse(payload)):
        with pytest.raises(GithubFetchError):
            resolve_default_branch("owner", "repo")


# ------------------------------------------------------------------- primitives


def test_primitive_meshes_have_matching_unit_normals() -> None:
    import numpy as np

    from hydra_editor_urdf.render.mesh import make_box_mesh, make_cylinder_mesh, make_sphere_mesh

    box = make_box_mesh((2.0, 4.0, 6.0))
    assert box.triangle_count == 12
    assert box.vertices.min(axis=0).tolist() == [-1.0, -2.0, -3.0]
    assert box.vertices.max(axis=0).tolist() == [1.0, 2.0, 3.0]
    cylinder = make_cylinder_mesh(1.0, 2.0, segments=8)
    assert cylinder.triangle_count == 8 * 2 + 8 * 2
    assert cylinder.vertices[:, 2].min() == pytest.approx(-1.0)
    sphere = make_sphere_mesh(2.0, segments=8, rings=6)
    assert np.allclose(np.linalg.norm(sphere.vertices, axis=1), 2.0, atol=1e-5)
    for mesh in (box, cylinder, sphere):
        assert len(mesh.normals) == len(mesh.vertices)
        assert np.allclose(np.linalg.norm(mesh.normals, axis=1), 1.0, atol=1e-5)


def test_scaling_a_mesh_keeps_its_normals_valid() -> None:
    import numpy as np

    from hydra_editor_urdf.render.mesh import make_box_mesh

    box = make_box_mesh((1.0, 1.0, 1.0))
    uniform = box.scaled((2.0, 2.0, 2.0))
    assert uniform.vertices.max() == pytest.approx(1.0)
    assert np.array_equal(uniform.normals, box.normals)
    stretched = box.scaled((1.0, 4.0, 0.0))  # a zero axis must not divide by zero
    assert np.isfinite(stretched.normals).all()
    assert np.allclose(np.linalg.norm(stretched.normals, axis=1), 1.0, atol=1e-5)
    assert box.vertices.max() == pytest.approx(0.5)  # the original is not changed


def test_unsupported_mesh_formats_are_named() -> None:
    from hydra_editor_urdf.render.mesh import UnsupportedMeshFormat

    with pytest.raises(UnsupportedMeshFormat, match="COLLADA"):
        load_mesh_file("robot.dae")
    with pytest.raises(UnsupportedMeshFormat, match="unrecognized"):
        load_mesh_file("robot.ply")


# ------------------------------------------------------------- the cache of loaded meshes


def _write_ascii_stl(path: Path, triangles: int) -> None:
    lines = ["solid t"]
    for i in range(triangles):
        lines += ["facet normal 0 0 1", " outer loop", f"  vertex {i} 0 0", f"  vertex {i + 1} 0 0", f"  vertex {i} 1 0", " endloop", "endfacet"]
    lines.append("endsolid t")
    path.write_text("\n".join(lines) + "\n")


def test_a_mesh_is_read_from_disk_once_until_the_file_changes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from hydra_editor_urdf.render import mesh as mesh_module

    mesh_module.clear_mesh_cache()
    path = tmp_path / "a.stl"
    _write_ascii_stl(path, 2)
    reads: list[str] = []
    real = mesh_module._read_mesh_file
    monkeypatch.setattr(mesh_module, "_read_mesh_file", lambda p, *args: reads.append(str(p)) or real(p, *args))
    first = mesh_module.load_mesh_file(path)
    second = mesh_module.load_mesh_file(path)
    assert first is second and first.triangle_count == 2
    assert len(reads) == 1
    _write_ascii_stl(path, 3)  # another size on disk
    third = mesh_module.load_mesh_file(path)
    assert third.triangle_count == 3 and len(reads) == 2


def test_the_shared_mesh_cannot_be_changed_in_place_and_scaling_gives_a_new_one(tmp_path: Path) -> None:
    from hydra_editor_urdf.render import mesh as mesh_module

    mesh_module.clear_mesh_cache()
    path = tmp_path / "a.stl"
    _write_ascii_stl(path, 1)
    mesh = mesh_module.load_mesh_file(path)
    with pytest.raises(ValueError):
        mesh.vertices[0, 0] = 99.0
    scaled = mesh.scaled((2.0, 2.0, 2.0))
    assert scaled is not mesh and scaled.vertices[1, 0] == mesh.vertices[1, 0] * 2
    assert mesh_module.load_mesh_file(path).vertices[1, 0] == mesh.vertices[1, 0]


def test_a_mesh_that_cannot_be_read_is_not_kept_and_is_reported_every_time(tmp_path: Path) -> None:
    from hydra_editor_urdf.render import mesh as mesh_module

    mesh_module.clear_mesh_cache()
    path = tmp_path / "bad.stl"
    path.write_bytes(b"not a mesh at all")
    for _ in range(2):
        with pytest.raises(MalformedMeshFile):
            mesh_module.load_mesh_file(path)
    assert len(mesh_module._mesh_cache) == 0
    with pytest.raises(OSError):
        mesh_module.load_mesh_file(tmp_path / "missing.stl")


def test_the_cache_keeps_to_its_budget_and_drops_the_oldest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from hydra_editor_urdf.render import mesh as mesh_module

    mesh_module.clear_mesh_cache()
    paths = []
    for i in range(4):
        path = tmp_path / f"m{i}.stl"
        _write_ascii_stl(path, 10)
        paths.append(path)
    one = mesh_module._mesh_bytes(mesh_module.load_mesh_file(paths[0]))
    mesh_module.clear_mesh_cache()
    monkeypatch.setattr(mesh_module, "MESH_CACHE_BYTES", one * 2 + 1)
    for path in paths:
        mesh_module.load_mesh_file(path)
    assert len(mesh_module._mesh_cache) == 2
    assert mesh_module._mesh_cache_bytes <= one * 2 + 1
    kept = {key[0] for key in mesh_module._mesh_cache}
    assert kept == {str(paths[2].resolve()), str(paths[3].resolve())}
