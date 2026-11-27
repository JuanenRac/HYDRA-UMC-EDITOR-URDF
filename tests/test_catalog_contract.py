# =============================================================================
# HYDRA-UMC-EDITOR-URDF - tests/test_catalog_contract.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""What this editor sends to the model catalog of the server, against the contract it shares with HYDRA-UMC-EDITOR-STL
(`tests/golden/catalog_submit.json`, a byte copy of `conformance/fixtures/v1/catalog-submit.json` of HYDRA-UMC-SDK)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from hydra_editor_urdf.server.client import StudioClient
from hydra_editor_urdf.urdf.parser import parse_urdf_file

CONTRACT_FILE = Path(__file__).parent / "golden" / "catalog_submit.json"
# The same number in the other editor: the contract changes in the SDK first, then in both copies.
CONTRACT_SHA256 = "86442c8b44d37b068d73f728602938d0700e5d5e702f6d1ced5711b4f2507cb1"
CONTRACT = json.loads(CONTRACT_FILE.read_text(encoding="utf-8"))


def _recording(client) -> list[tuple[str, str, dict | None, bool]]:
    """Replaces the HTTP call of the client: it answers with the examples of the contract and keeps what was asked."""
    asked: list[tuple[str, str, dict | None, bool]] = []
    answers = {spec["path"]: spec["response"] for spec in (CONTRACT["login"], CONTRACT["submit"])}

    def request(method: str, path: str, body: dict | None = None, auth: bool = False) -> dict:
        asked.append((method, path, body, auth))
        return answers.get(path, CONTRACT["download"]["response"])

    client._request = request
    return asked


def _same_shape(sent: dict, required: dict, optional: dict) -> None:
    assert set(required) <= set(sent) <= set(required) | set(optional), sorted(sent)
    for key, value in sent.items():
        assert type(value) is type({**required, **optional}[key]), key


def test_the_contract_is_the_agreed_copy() -> None:
    assert hashlib.sha256(CONTRACT_FILE.read_bytes()).hexdigest() == CONTRACT_SHA256


def test_login_submit_and_download_follow_the_contract(tmp_path: Path) -> None:
    (tmp_path / "base.stl").write_bytes(b"solid base")
    source = tmp_path / "arm.urdf"
    source.write_text('<robot name="arm"><link name="base"><visual><geometry><mesh filename="base.stl"/></geometry></visual></link></robot>', encoding="utf-8")
    robot = parse_urdf_file(source)
    client = StudioClient("127.0.0.1")
    asked = _recording(client)
    login, submit, download = CONTRACT["login"], CONTRACT["submit"], CONTRACT["download"]
    client.login(login["request"]["username"], login["request"]["password"])
    assert client.push_model(robot, "robots", lambda name: tmp_path / name) == submit["response"]["slug"]
    pulled = client.pull_model("robots", "arm", tmp_path / "out")
    (method, path, body, auth), (method2, path2, body2, auth2), (method3, path3, _, auth3) = asked
    assert (method, path, auth) == (login["method"], login["path"], False)
    assert body == login["request"]
    assert (method2, path2, auth2) == (submit["method"], submit["path"], True)
    assert body2 is not None
    _same_shape(body2, submit["required"], submit["optional"])
    assert all(set(entry) == {"filename", "base64"} for entry in body2["meshFiles"])
    assert (method3, path3, auth3) == (download["method"], download["path"].format(category="robots", slug="arm"), False)
    assert pulled.read_text(encoding="utf-8") == download["response"]["urdfXml"]
    assert (pulled.parent / "meshes" / "base.stl").read_bytes()
