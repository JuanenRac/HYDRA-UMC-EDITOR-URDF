# =============================================================================
# HYDRA-UMC EDITOR-URDF - tests/test_license_gate.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The license gate of a push: off by default; "warn" lets the push go on and adds the attribution; "block" refuses it.
# =============================================================================
from __future__ import annotations

import json
from pathlib import Path

import pytest

from hydra_editor_urdf.models import Link, MeshGeometry, Robot, Visual
from hydra_editor_urdf.server.client import StudioClient, StudioClientError
from hydra_editor_urdf.urdf.parser import parse_urdf_string
from hydra_editor_urdf.source.licenses import LicenseGate, attribution_comment, check_mesh_licenses, gate_problems

MIT = "Permission is hereby granted, free of charge, to any person obtaining a copy"
NONCOMMERCIAL = "Creative Commons Attribution-NonCommercial 4.0"


def _robot(meshes: list[str]) -> Robot:
    robot = Robot(name="bot")
    for index, mesh in enumerate(meshes):
        robot.links[f"l{index}"] = Link(name=f"l{index}", visuals=[Visual(geometry=MeshGeometry(filename=mesh))])
    return robot


def _resolver(root: Path):
    return lambda name: (root / name) if (root / name).is_file() else None


def _folder(tmp_path: Path, license_text: str | None) -> Path:
    (tmp_path / "meshes").mkdir()
    (tmp_path / "meshes" / "a.stl").write_bytes(b"solid a\nendsolid a\n")
    if license_text is not None:
        (tmp_path / "LICENSE").write_text(license_text, encoding="utf-8")
    return tmp_path


class _Capture(StudioClient):
    def __init__(self) -> None:
        super().__init__("127.0.0.1", 1)
        self.token = "t"
        self.sent: dict | None = None

    def _request(self, method, path, body=None, auth=False):  # type: ignore[override]
        self.sent = body
        return {"slug": "bot"}


def test_the_gate_is_off_unless_the_configuration_asks_for_it() -> None:
    assert LicenseGate.from_config({}).mode == "off"
    assert LicenseGate.from_config({"push_license_gate": "maybe"}).mode == "off"
    assert not LicenseGate.from_config({"push_license_gate": "off"}).active
    assert LicenseGate.from_config({"push_license_gate": "block", "push_license_blocked": ["MIT"]}).blocked_licenses == ("MIT",)


def test_a_mesh_without_a_license_file_and_a_forbidden_license_are_problems(tmp_path: Path) -> None:
    root = _folder(tmp_path, None)
    entries = check_mesh_licenses(_robot(["meshes/a.stl"]), _resolver(root), root)
    assert gate_problems(entries, LicenseGate(mode="block")) and "no LICENSE" in gate_problems(entries, LicenseGate(mode="block"))[0]
    assert gate_problems(entries, LicenseGate(mode="block", require_license_file=False)) == []
    assert gate_problems(entries, LicenseGate(mode="off")) == []


def test_block_refuses_the_push_before_anything_is_sent(tmp_path: Path) -> None:
    root = _folder(tmp_path, NONCOMMERCIAL)
    client = _Capture()
    with pytest.raises(StudioClientError, match="license check"):
        client.push_model(_robot(["meshes/a.stl"]), "arms", _resolver(root), license_gate=LicenseGate(mode="block"), mesh_root=root)
    assert client.sent is None


def test_warn_lets_the_push_go_on_and_the_attribution_travels_in_the_urdf(tmp_path: Path) -> None:
    root = _folder(tmp_path, NONCOMMERCIAL)
    client = _Capture()
    client.push_model(_robot(["meshes/a.stl"]), "arms", _resolver(root), license_gate=LicenseGate(mode="warn"), mesh_root=root)
    xml = client.sent["urdfXml"]  # type: ignore[index]
    assert "Attribution for the meshes of bot" in xml and "LICENSE" in xml
    assert xml.index("<!--") < xml.index("<robot")
    assert parse_urdf_string(xml).name == "bot"  # a comment before the root keeps it a valid URDF


def test_a_licensed_mesh_passes_the_block_gate(tmp_path: Path) -> None:
    root = _folder(tmp_path, MIT)
    client = _Capture()
    assert client.push_model(_robot(["meshes/a.stl"]), "arms", _resolver(root), license_gate=LicenseGate(mode="block"), mesh_root=root) == "bot"


def test_without_the_gate_the_urdf_is_sent_as_before(tmp_path: Path) -> None:
    root = _folder(tmp_path, None)
    client = _Capture()
    client.push_model(_robot(["meshes/a.stl"]), "arms", _resolver(root))
    assert "<!--" not in client.sent["urdfXml"]  # type: ignore[index]
    client.push_model(_robot(["meshes/a.stl"]), "arms", _resolver(root), license_gate=LicenseGate(mode="off"), mesh_root=root)
    assert "<!--" not in client.sent["urdfXml"]  # type: ignore[index]


def test_the_attribution_comment_cannot_close_itself_early() -> None:
    assert "--" not in attribution_comment("a -- b --> c").split("<!--", 1)[1].rsplit("-->", 1)[0]
    json.dumps(attribution_comment("x"))


def test_the_attribution_also_travels_in_its_own_field_and_only_when_the_gate_is_on(tmp_path: Path) -> None:
    root = _folder(tmp_path, NONCOMMERCIAL)
    client = _Capture()
    client.push_model(_robot(["meshes/a.stl"]), "arms", _resolver(root), license_gate=LicenseGate(mode="warn"), mesh_root=root)
    sent = client.sent  # type: ignore[assignment]
    assert "LICENSE" in sent["attribution"] and len(sent["attribution"]) <= 8000
    client.push_model(_robot(["meshes/a.stl"]), "arms", _resolver(root))
    assert "attribution" not in client.sent  # type: ignore[operator]
