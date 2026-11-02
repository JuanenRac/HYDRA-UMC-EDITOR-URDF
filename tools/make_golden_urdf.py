#!/usr/bin/env python3
# =============================================================================
# HYDRA-UMC EDITOR-URDF - tools/make_golden_urdf.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# Writes the shared "golden" URDF set: a few small robots plus, for each one, the
# position every joint's child frame must have at some joint values. The expected
# numbers come from the plain-math reference below (no numpy, no editor code), so
# every implementation is checked against the same independent answer.
#
# The same files are kept, byte for byte, in the repositories that read or write
# a URDF (the editor, the STL editor and the physics replica). tests/golden/MANIFEST.sha256
# lists them; tools/golden_sync.py --check compares the copies that sit next to
# this checkout.
#
#   py -3 -I tools/make_golden_urdf.py          rewrite tests/golden/
#   py -3 -I tools/make_golden_urdf.py --check  fail when the files differ from the reference
# =============================================================================
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

GOLDEN = Path(__file__).resolve().parent.parent / "tests" / "golden"

Matrix = list[list[float]]


def _identity() -> Matrix:
    return [[1.0 if r == c else 0.0 for c in range(4)] for r in range(4)]


def _mul(a: Matrix, b: Matrix) -> Matrix:
    return [[sum(a[r][k] * b[k][c] for k in range(4)) for c in range(4)] for r in range(4)]


def _translation(x: float, y: float, z: float) -> Matrix:
    m = _identity()
    m[0][3], m[1][3], m[2][3] = x, y, z
    return m


def _rpy(roll: float, pitch: float, yaw: float) -> Matrix:
    """URDF fixed-axis convention: R = Rz(yaw) * Ry(pitch) * Rx(roll)."""
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    m = _identity()
    m[0][0], m[0][1], m[0][2] = cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr
    m[1][0], m[1][1], m[1][2] = sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr
    m[2][0], m[2][1], m[2][2] = -sp, cp * sr, cp * cr
    return m


def _axis_angle(axis: tuple[float, float, float], angle: float) -> Matrix:
    n = math.sqrt(sum(a * a for a in axis))
    x, y, z = (a / n for a in axis)
    c, s = math.cos(angle), math.sin(angle)
    t = 1.0 - c
    m = _identity()
    m[0][0], m[0][1], m[0][2] = t * x * x + c, t * x * y - s * z, t * x * z + s * y
    m[1][0], m[1][1], m[1][2] = t * x * y + s * z, t * y * y + c, t * y * z - s * x
    m[2][0], m[2][1], m[2][2] = t * x * z - s * y, t * y * z + s * x, t * z * z + c
    return m


# Each robot: name -> list of joints in tree order. A joint is
# (name, type, parent_link, child_link, xyz, rpy, axis).
Joint = tuple[str, str, str, str, tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]

ROBOTS: dict[str, list[Joint]] = {
    "rpy_probe_a": [
        ("rot", "fixed", "base", "frame", (0.1, 0.2, 0.3), (0.3, 0.5, 0.7), (0, 0, 1)),
        ("probe_x", "fixed", "frame", "px", (1, 0, 0), (0, 0, 0), (0, 0, 1)),
        ("probe_y", "fixed", "frame", "py", (0, 1, 0), (0, 0, 0), (0, 0, 1)),
        ("probe_z", "fixed", "frame", "pz", (0, 0, 1), (0, 0, 0), (0, 0, 1)),
    ],
    "rpy_probe_b": [
        ("rot", "fixed", "base", "frame", (-0.5, 0.0, 1.25), (-1.2, 0.9, 2.5), (0, 0, 1)),
        ("probe_x", "fixed", "frame", "px", (1, 0, 0), (0, 0, 0), (0, 0, 1)),
        ("probe_y", "fixed", "frame", "py", (0, 1, 0), (0, 0, 0), (0, 0, 1)),
        ("probe_z", "fixed", "frame", "pz", (0, 0, 1), (0, 0, 0), (0, 0, 1)),
    ],
    # pitch close to -90 degrees: the corner where roll and yaw nearly coincide
    "rpy_probe_c": [
        ("rot", "fixed", "base", "frame", (0.0, 0.0, 0.0), (3.0, -1.5, -2.0), (0, 0, 1)),
        ("probe_x", "fixed", "frame", "px", (1, 0, 0), (0, 0, 0), (0, 0, 1)),
        ("probe_y", "fixed", "frame", "py", (0, 1, 0), (0, 0, 0), (0, 0, 1)),
        ("probe_z", "fixed", "frame", "pz", (0, 0, 1), (0, 0, 0), (0, 0, 1)),
    ],
    "arm_3dof": [
        ("base_yaw", "revolute", "base", "turret", (0, 0, 0.1), (0, 0, 0), (0, 0, 1)),
        ("shoulder", "revolute", "turret", "upper", (0.05, 0, 0.2), (0, 0.2, 0.5), (0, 1, 0)),
        ("slide", "prismatic", "upper", "slider", (0.3, 0, 0), (0.1, 0, 0), (1, 0, 0)),
    ],
    "branch_tree": [
        ("spine", "revolute", "base", "trunk", (0, 0, 0.5), (0, 0, 0), (0, 0, 1)),
        ("left_arm", "revolute", "trunk", "left", (0, 0.2, 0.3), (0.4, 0, 0), (1, 0, 0)),
        ("right_arm", "revolute", "trunk", "right", (0, -0.2, 0.3), (-0.4, 0.1, 0), (0, 1, 0)),
        ("left_tip", "fixed", "left", "left_end", (0.25, 0, 0), (0, 0, 0.3), (0, 0, 1)),
    ],
    "continuous_chain": [
        ("wheel", "continuous", "base", "rim", (0.2, 0.1, 0), (1.5707963267948966, 0, 0), (0, 0, 1)),
        ("hub", "fixed", "rim", "hubcap", (0.0, 0.0, 0.05), (0, 0, -0.9), (0, 0, 1)),
        ("tool", "revolute", "hubcap", "pointer", (0.1, 0, 0), (0.2, -0.3, 0.4), (0.6, 0.0, 0.8)),
    ],
}

# Joint values to try for each robot (revolute/continuous radians, prismatic meters).
CASES: dict[str, list[dict[str, float]]] = {
    "rpy_probe_a": [{}],
    "rpy_probe_b": [{}],
    "rpy_probe_c": [{}],
    "arm_3dof": [
        {"base_yaw": 0.0, "shoulder": 0.0, "slide": 0.0},
        {"base_yaw": 0.6, "shoulder": -0.4, "slide": 0.05},
        {"base_yaw": -2.2, "shoulder": 0.9, "slide": 0.12},
    ],
    "branch_tree": [
        {"spine": 0.0, "left_arm": 0.0, "right_arm": 0.0},
        {"spine": 0.8, "left_arm": -0.5, "right_arm": 1.1},
    ],
    "continuous_chain": [
        {"wheel": 0.0, "tool": 0.0},
        {"wheel": 4.0, "tool": -0.7},
    ],
}

LIMITS = {"revolute": (-3.2, 3.2), "prismatic": (0.0, 0.15)}


def urdf_text(name: str) -> str:
    lines = ['<?xml version="1.0"?>', f'<robot name="{name}">']
    links: list[str] = []
    for _, _, parent, child, *_ in ROBOTS[name]:
        for link in (parent, child):
            if link not in links:
                links.append(link)
    for link in links:
        lines.append(f'  <link name="{link}"/>')
    for jname, jtype, parent, child, xyz, rpy, axis in ROBOTS[name]:
        lines.append(f'  <joint name="{jname}" type="{jtype}">')
        lines.append(f'    <parent link="{parent}"/>')
        lines.append(f'    <child link="{child}"/>')
        lines.append(f'    <origin xyz="{xyz[0]:g} {xyz[1]:g} {xyz[2]:g}" rpy="{rpy[0]:.10g} {rpy[1]:.10g} {rpy[2]:.10g}"/>')
        if jtype != "fixed":
            lines.append(f'    <axis xyz="{axis[0]:g} {axis[1]:g} {axis[2]:g}"/>')
        if jtype in LIMITS:
            lo, hi = LIMITS[jtype]
            lines.append(f'    <limit lower="{lo}" upper="{hi}" effort="10" velocity="2"/>')
        lines.append("  </joint>")
    lines.append("</robot>")
    return "\n".join(lines) + "\n"


def reference_positions(name: str, values: dict[str, float]) -> dict[str, list[float]]:
    """Position of each joint's child frame in the base frame, by plain matrix products."""
    frames: dict[str, Matrix] = {}
    root = ROBOTS[name][0][2]
    frames[root] = _identity()
    out: dict[str, list[float]] = {}
    for jname, jtype, parent, child, xyz, rpy, axis in ROBOTS[name]:
        local = _mul(_translation(*xyz), _rpy(*rpy))
        if jtype == "revolute" or jtype == "continuous":
            local = _mul(local, _axis_angle(axis, values.get(jname, 0.0)))
        elif jtype == "prismatic":
            n = math.sqrt(sum(a * a for a in axis))
            d = values.get(jname, 0.0)
            local = _mul(local, _translation(*(a / n * d for a in axis)))
        frames[child] = _mul(frames[parent], local)
        out[jname] = [round(frames[child][r][3], 9) for r in range(3)]
    return out


def build() -> dict[str, str]:
    files: dict[str, str] = {}
    cases: list[dict[str, object]] = []
    for name in ROBOTS:
        files[f"urdf/{name}.urdf"] = urdf_text(name)
        for values in CASES[name]:
            cases.append({"urdf": f"urdf/{name}.urdf", "joints": values, "expected": reference_positions(name, values)})
    files["cases.json"] = json.dumps(
        {
            "about": "Where each joint's child frame sits (meters, base frame) at the given joint values.",
            "tolerance": 1e-6,
            "cases": cases,
        },
        indent=2,
    ) + "\n"
    # rpy -> rotation matrix, used by the code that turns a rotation back into rpy
    rotations = []
    for rpy in [(0.0, 0.0, 0.0), (0.3, 0.5, 0.7), (-1.2, 0.9, 2.5), (3.0, -1.5, -2.0), (0.0, 0.0, 1.5707963267948966), (0.0, 1.5707963267948966, 0.0), (1.5707963267948966, 0.0, 0.0)]:
        m = _rpy(*rpy)
        rotations.append({"rpy": list(rpy), "matrix": [[round(m[r][c], 12) for c in range(3)] for r in range(3)]})
    files["rotations.json"] = json.dumps(
        {"about": "URDF rpy (Rz(yaw) Ry(pitch) Rx(roll)) and the 3x3 rotation matrix it stands for.", "tolerance": 1e-9, "rotations": rotations},
        indent=2,
    ) + "\n"
    return files


def manifest(files: dict[str, str]) -> str:
    return "".join(f"{hashlib.sha256(files[k].encode('utf-8')).hexdigest()}  {k}\n" for k in sorted(files))


def main(argv: list[str]) -> int:
    files = build()
    files_with_manifest = dict(files)
    expected_manifest = manifest(files)
    if "--check" in argv:
        bad = []
        for rel, text in files.items():
            path = GOLDEN / rel
            if not path.is_file() or path.read_bytes() != text.encode("utf-8"):
                bad.append(rel)
        mpath = GOLDEN / "MANIFEST.sha256"
        if not mpath.is_file() or mpath.read_bytes() != expected_manifest.encode("utf-8"):
            bad.append("MANIFEST.sha256")
        if bad:
            print("FAIL: golden files differ from the reference: " + ", ".join(bad))
            return 1
        print("PASS: golden files match the reference")
        return 0
    for rel, text in files_with_manifest.items():
        path = GOLDEN / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))
    (GOLDEN / "MANIFEST.sha256").write_bytes(expected_manifest.encode("utf-8"))
    print(f"wrote {len(files) + 1} files to {GOLDEN}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
