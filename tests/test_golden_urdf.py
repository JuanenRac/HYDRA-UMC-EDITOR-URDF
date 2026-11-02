# =============================================================================
# HYDRA-UMC EDITOR-URDF - tests/test_golden_urdf.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The shared golden URDF set (tests/golden/): the same files are checked here, in
# the STL editor and in the physics replica, so all of them read origin, rpy and
# axis the same way. The expected numbers come from tools/make_golden_urdf.py.
# =============================================================================
from __future__ import annotations

import hashlib
import json
import math
import runpy
from pathlib import Path

import numpy as np
import pytest

from hydra_editor_urdf.render.kinematics import compute_link_world_transforms, rpy_to_matrix
from hydra_editor_urdf.urdf.parser import parse_urdf_file, parse_urdf_string
from hydra_editor_urdf.urdf.writer import robot_to_urdf_string

GOLDEN = Path(__file__).resolve().parent / "golden"
CASES = json.loads((GOLDEN / "cases.json").read_text(encoding="utf-8"))
ROTATIONS = json.loads((GOLDEN / "rotations.json").read_text(encoding="utf-8"))


def _joint_positions(robot, values):
    world = compute_link_world_transforms(robot, values)
    return {name: world[joint.child][:3, 3] for name, joint in robot.joints.items()}


def _case_id(case):
    return f"{Path(case['urdf']).stem}-{len(case['joints'])}"


@pytest.mark.parametrize("case", CASES["cases"], ids=_case_id)
def test_forward_kinematics_matches_the_golden_positions(case):
    robot = parse_urdf_file(GOLDEN / case["urdf"])
    positions = _joint_positions(robot, case["joints"])
    for joint, expected in case["expected"].items():
        assert np.allclose(positions[joint], expected, atol=CASES["tolerance"]), (joint, positions[joint], expected)


@pytest.mark.parametrize("case", CASES["cases"], ids=_case_id)
def test_writing_and_reading_back_keeps_the_golden_positions(case):
    robot = parse_urdf_file(GOLDEN / case["urdf"])
    again = parse_urdf_string(robot_to_urdf_string(robot))
    positions = _joint_positions(again, case["joints"])
    for joint, expected in case["expected"].items():
        assert np.allclose(positions[joint], expected, atol=CASES["tolerance"]), joint


@pytest.mark.parametrize("entry", ROTATIONS["rotations"], ids=lambda e: "-".join(f"{v:.2f}" for v in e["rpy"]))
def test_rpy_matrix_matches_the_golden_rotation(entry):
    assert np.allclose(rpy_to_matrix(tuple(entry["rpy"])), entry["matrix"], atol=ROTATIONS["tolerance"])


def _normalised_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def test_the_manifest_lists_every_golden_file_with_its_hash():
    listed = {}
    for line in (GOLDEN / "MANIFEST.sha256").read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        listed[name] = digest
    on_disk = {p.relative_to(GOLDEN).as_posix() for p in GOLDEN.rglob("*") if p.is_file() and p.name != "MANIFEST.sha256"}
    assert set(listed) == on_disk
    for name, digest in listed.items():
        assert _normalised_digest(GOLDEN / name) == digest, name


def test_the_files_are_what_the_reference_generator_writes():
    generator = runpy.run_path(str(Path(__file__).resolve().parent.parent / "tools" / "make_golden_urdf.py"))
    for name, text in generator["build"]().items():
        assert (GOLDEN / name).read_bytes().replace(b"\r\n", b"\n") == text.encode("utf-8"), name


def test_every_golden_robot_has_at_least_one_case():
    used = {Path(c["urdf"]).name for c in CASES["cases"]}
    assert used == {p.name for p in (GOLDEN / "urdf").glob("*.urdf")}
    assert math.isclose(CASES["tolerance"], 1e-6)
