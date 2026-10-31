# =============================================================================
# HYDRA-UMC EDITOR-URDF - tests/test_physical_check.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
#
# The physical check of a model (urdf/physical_check.py), its switch, its command line and its texts. Random models are
# generated from a fixed seed: the valid ones give no warning, and each concrete mutation gives the expected one.
# =============================================================================
from __future__ import annotations

import copy
import io
import json
import math
import random
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from hydra_editor_urdf import i18n
from hydra_editor_urdf.app import EditorController
from hydra_editor_urdf.cli import EXIT_CLEAN, EXIT_ERROR, EXIT_WARNINGS, run_cli
from hydra_editor_urdf.models import (
    BoxGeometry,
    Collision,
    Inertial,
    Joint,
    JointLimit,
    JointType,
    Link,
    MeshGeometry,
    Origin,
    Robot,
    Visual,
)
from hydra_editor_urdf.urdf.parser import parse_urdf_string
from hydra_editor_urdf.urdf.physical_check import (
    RULES,
    PhysicalLimits,
    check_robot,
    duplicate_names_in_xml,
    physical_warning_lines,
)
from hydra_editor_urdf.urdf.writer import robot_to_urdf_string

ROOT = Path(__file__).resolve().parent.parent
LANGUAGES = ("english", "spanish", "german", "french", "italian", "japanese", "chinese", "portuguese")


def _inertial(rng: random.Random) -> Inertial:
    """The tensor of a solid box, turned by a random rotation: always symmetric, positive definite and with principal moments
    that obey the triangle inequalities."""
    mass = rng.uniform(0.1, 20.0)
    a, b, c = (rng.uniform(0.02, 0.5) for _ in range(3))
    diag = np.diag([mass / 12 * (b * b + c * c), mass / 12 * (a * a + c * c), mass / 12 * (a * a + b * b)])
    q, _r = np.linalg.qr(np.array([[rng.gauss(0, 1) for _ in range(3)] for _ in range(3)]))
    t = q @ diag @ q.T
    return Inertial(mass=mass, ixx=float(t[0, 0]), ixy=float(t[0, 1]), ixz=float(t[0, 2]), iyy=float(t[1, 1]), iyz=float(t[1, 2]), izz=float(t[2, 2]))


def random_valid_robot(seed: int) -> Robot:
    rng = random.Random(seed)
    robot = Robot(name=f"r{seed}")
    count = rng.randint(2, 9)
    for i in range(count):
        robot.links[f"l{i}"] = Link(
            name=f"l{i}",
            visuals=[Visual(name=f"v{i}", geometry=BoxGeometry(size=(0.1, 0.2, 0.3)))],
            collisions=[Collision(name=f"c{i}", geometry=BoxGeometry(size=(0.1, 0.2, 0.3)))],
            inertial=_inertial(rng),
        )
    for i in range(1, count):
        kind = rng.choice([JointType.REVOLUTE, JointType.PRISMATIC, JointType.CONTINUOUS, JointType.FIXED])
        axis = np.array([rng.gauss(0, 1) for _ in range(3)])
        axis = axis / np.linalg.norm(axis)
        limit = None
        if kind in (JointType.REVOLUTE, JointType.PRISMATIC):
            limit = JointLimit(rng.uniform(-3.0, 0.0), rng.uniform(0.1, 3.0), rng.uniform(1, 50), rng.uniform(0.1, 5))
        elif kind is JointType.CONTINUOUS:
            limit = JointLimit(0.0, 0.0, rng.uniform(1, 50), rng.uniform(0.1, 5))
        robot.joints[f"j{i}"] = Joint(
            f"j{i}",
            kind,
            f"l{rng.randint(0, i - 1)}",
            f"l{i}",
            Origin(xyz=(rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))),
            (float(axis[0]), float(axis[1]), float(axis[2])),
            limit,
        )
    return robot


def rules_of(robot: Robot, **kwargs) -> set[str]:
    return {w.rule for w in check_robot(robot, **kwargs)}


# --- valid models give no warning ---------------------------------------------------------------------------------------


@pytest.mark.parametrize("seed", range(60))
def test_random_valid_models_give_no_warning(seed: int) -> None:
    assert check_robot(random_valid_robot(seed)) == []


@pytest.mark.parametrize("seed", range(10))
def test_a_valid_model_stays_valid_through_the_writer_and_the_parser(seed: int) -> None:
    again = parse_urdf_string(robot_to_urdf_string(random_valid_robot(seed)))
    assert check_robot(again) == []


def test_the_result_is_deterministic() -> None:
    robot = random_valid_robot(3)
    robot.links["l0"].inertial = Inertial(mass=-1.0, ixx=1, iyy=1, izz=9)
    assert check_robot(robot) == check_robot(copy.deepcopy(robot))


# --- mutations ----------------------------------------------------------------------------------------------------------


def _mutated(seed: int = 1) -> Robot:
    robot = random_valid_robot(seed)
    while not any(j.type is JointType.REVOLUTE for j in robot.joints.values()):
        seed += 1
        robot = random_valid_robot(seed)
    return robot


def _revolute(robot: Robot) -> Joint:
    return next(j for j in robot.joints.values() if j.type is JointType.REVOLUTE)


def _inertial_of(robot: Robot, name: str) -> Inertial:
    inertial = robot.links[name].inertial
    assert inertial is not None
    return inertial


@pytest.mark.parametrize("mass", [0.0, -2.0, float("nan")])
def test_mass_not_above_zero(mass: float) -> None:
    robot = _mutated()
    _inertial_of(robot, "l0").mass = mass
    found = [w for w in check_robot(robot) if w.rule == "mass_not_positive"]
    assert [w.element for w in found] == ["link:l0"]
    assert found[0].limit == "> 0"


def test_a_huge_mass_looks_like_grams() -> None:
    robot = _mutated()
    _inertial_of(robot, "l0").mass = 25000.0
    found = [w for w in check_robot(robot) if w.rule == "units_mass"]
    assert found and found[0].fix == "25"


def test_non_finite_inertia() -> None:
    robot = _mutated()
    _inertial_of(robot, "l1").ixy = float("inf")
    assert "inertia_not_finite" in rules_of(robot)


def test_inertia_not_positive_definite() -> None:
    robot = _mutated()
    robot.links["l0"].inertial = Inertial(mass=1.0, ixx=1.0, iyy=1.0, izz=-0.5)
    found = [w for w in check_robot(robot) if w.rule == "inertia_not_positive_definite"]
    assert len(found) == 1
    shift = float(found[0].fix)  # the suggested shift really does make the tensor positive definite
    assert np.all(np.linalg.eigvalsh(np.diag([1.0 + shift, 1.0 + shift, -0.5 + shift])) > 0)


def test_a_zero_tensor_is_not_positive_definite() -> None:
    robot = _mutated()
    robot.links["l0"].inertial = Inertial(mass=1.0)
    assert "inertia_not_positive_definite" in rules_of(robot)


@pytest.mark.parametrize(
    ("moments", "broken"),
    [((1.0, 1.0, 3.0), True), ((1.0, 1.0, 2.0), False), ((2.0, 3.0, 4.0), False), ((1.0, 2.0, 5.0), True)],
)
def test_triangle_inequality_of_the_principal_moments(moments: tuple[float, float, float], broken: bool) -> None:
    for order in ((0, 1, 2), (2, 0, 1), (1, 2, 0)):  # the rule holds for every permutation
        robot = _mutated()
        ixx, iyy, izz = (moments[i] for i in order)
        robot.links["l0"].inertial = Inertial(mass=1.0, ixx=ixx, iyy=iyy, izz=izz)
        assert ("inertia_triangle" in rules_of(robot)) is broken
    if broken:
        robot = _mutated()
        robot.links["l0"].inertial = Inertial(mass=1.0, ixx=moments[0], iyy=moments[1], izz=moments[2])
        fix = float(next(w for w in check_robot(robot) if w.rule == "inertia_triangle").fix)
        a, b, c = sorted(moments)
        assert (a + fix) + b >= c - 1e-9


def test_inertia_checks_ignore_a_link_without_inertial() -> None:
    robot = _mutated()
    robot.links["l0"].inertial = None
    assert check_robot(robot) == []


def test_limits_inverted() -> None:
    robot = _mutated()
    joint = _revolute(robot)
    joint.limit = JointLimit(2.0, 1.0, 5.0, 1.0)
    found = [w for w in check_robot(robot) if w.rule == "limit_inverted"]
    assert [w.element for w in found] == [f"joint:{joint.name}"]
    assert found[0].fix == "lower 1, upper 2"


def test_velocity_and_effort_must_be_above_zero() -> None:
    robot = _mutated()
    _revolute(robot).limit = JointLimit(-1.0, 1.0, 0.0, -3.0)
    assert {"velocity_not_positive", "effort_not_positive"} <= rules_of(robot)


def test_a_bounded_joint_without_limit() -> None:
    robot = _mutated()
    joint = _revolute(robot)
    joint.limit = None
    assert any(w.rule == "limit_missing" and w.element == f"joint:{joint.name}" for w in check_robot(robot))


def test_continuous_joint_with_limits() -> None:
    robot = _mutated()
    joint = _revolute(robot)
    joint.type = JointType.CONTINUOUS
    joint.limit = JointLimit(-1.0, 1.0, 5.0, 1.0)
    assert "continuous_with_limits" in rules_of(robot)
    joint.limit = JointLimit(0.0, 0.0, 5.0, 1.0)
    assert "continuous_with_limits" not in rules_of(robot)


def test_degrees_in_a_revolute_limit() -> None:
    robot = _mutated()
    _revolute(robot).limit = JointLimit(-180.0, 180.0, 5.0, 1.0)
    found = [w for w in check_robot(robot) if w.rule == "units_angle"]
    assert found and math.isclose(float(found[0].fix), math.radians(180.0), rel_tol=1e-5)


def test_millimetres_in_an_origin_and_in_a_shape() -> None:
    robot = _mutated()
    joint = next(iter(robot.joints.values()))
    joint.origin = Origin(xyz=(500.0, 0.0, 0.0))
    robot.links["l0"].visuals[0].geometry = BoxGeometry(size=(300.0, 10.0, 10.0))
    found = [w for w in check_robot(robot) if w.rule == "units_length"]
    assert {w.element for w in found} == {f"joint:{joint.name}", "link:l0/visual[0]"}


def test_axis_zero_and_not_unit() -> None:
    robot = _mutated()
    joint = _revolute(robot)
    joint.axis = (0.0, 0.0, 0.0)
    assert any(w.rule == "axis_zero" for w in check_robot(robot))
    joint.axis = (0.0, 0.0, 2.0)
    found = [w for w in check_robot(robot) if w.rule == "axis_not_unit"]
    assert found and found[0].fix == "0 0 1"
    joint.axis = (0.0, float("nan"), 1.0)
    assert "axis_zero" in rules_of(robot)


def test_a_fixed_joint_axis_is_not_checked() -> None:
    robot = Robot(name="r", links={"a": Link("a"), "b": Link("b")})
    robot.joints["j"] = Joint("j", JointType.FIXED, "a", "b", axis=(0.0, 0.0, 0.0))
    assert check_robot(robot) == []


# --- the tree -----------------------------------------------------------------------------------------------------------


def test_orphan_link_and_multiple_roots() -> None:
    robot = _mutated()
    robot.links["lonely"] = Link("lonely")
    assert [w.element for w in check_robot(robot) if w.rule == "tree_orphan_link"] == ["link:lonely"]
    assert "tree_multiple_roots" not in rules_of(robot)  # an orphan is reported once, as an orphan

    other = _mutated()
    other.links["x"] = Link("x")
    other.links["y"] = Link("y")
    other.joints["jxy"] = Joint("jxy", JointType.FIXED, "x", "y")
    found = [w for w in check_robot(other) if w.rule == "tree_multiple_roots"]
    assert len(found) == 1 and "2 roots" in found[0].value


def test_cycle_and_no_root() -> None:
    robot = Robot(name="r", links={n: Link(n) for n in "abc"})
    robot.joints["j1"] = Joint("j1", JointType.FIXED, "a", "b")
    robot.joints["j2"] = Joint("j2", JointType.FIXED, "b", "c")
    robot.joints["j3"] = Joint("j3", JointType.FIXED, "c", "a")
    assert {"tree_cycle", "tree_no_root"} <= rules_of(robot)


def test_cycle_beside_a_valid_root_is_unreachable() -> None:
    robot = Robot(name="r", links={n: Link(n) for n in "rabc"})
    robot.joints["j0"] = Joint("j0", JointType.FIXED, "r", "a")
    robot.joints["j1"] = Joint("j1", JointType.FIXED, "b", "c")
    robot.joints["j2"] = Joint("j2", JointType.FIXED, "c", "b")
    found = {w.rule: w for w in check_robot(robot)}
    assert "tree_cycle" in found
    assert found["tree_unreachable_link"].fix == "r"


def test_multiple_parents_and_unknown_link() -> None:
    robot = _mutated()
    robot.joints["extra"] = Joint("extra", JointType.FIXED, "l0", "l1")
    robot.joints["ghost"] = Joint("ghost", JointType.FIXED, "l0", "nowhere")
    assert {"tree_multiple_parents", "tree_unknown_link"} <= rules_of(robot)


def test_duplicate_names_inside_a_link_and_renamed_keys() -> None:
    robot = _mutated()
    robot.links["l0"].visuals = [Visual(name="same"), Visual(name="same")]
    assert any(w.rule == "duplicate_name" and w.element == "link:l0/visual" for w in check_robot(robot))
    robot = _mutated()
    robot.links["l1"].name = "renamed"
    assert any(w.rule == "duplicate_name" and w.element == "link:l1" for w in check_robot(robot))


def test_duplicate_names_in_the_xml_which_the_parser_refuses() -> None:
    text = '<robot name="r"><link name="a"/><link name="a"/><link name="b"/></robot>'
    assert [(w.rule, w.element) for w in duplicate_names_in_xml(text)] == [("duplicate_name", "link:a")]
    assert duplicate_names_in_xml("<robot><link name='a'/><link name='b'/></robot>") == []
    assert duplicate_names_in_xml("not xml") == []
    assert duplicate_names_in_xml("<!DOCTYPE x><robot/>") == []


# --- meshes -------------------------------------------------------------------------------------------------------------


def test_missing_mesh_needs_a_resolver() -> None:
    robot = _mutated()
    robot.links["l0"].visuals = [Visual(geometry=MeshGeometry("missing.stl", (0.001, 0.001, 0.001)))]
    assert check_robot(robot) == []  # no resolver: the files are not looked for
    assert [w.rule for w in check_robot(robot, resolver=lambda _name: None)] == ["mesh_missing"]
    assert check_robot(robot, resolver=lambda _name: Path("x.stl")) == []


@pytest.mark.parametrize(
    "scale", [(0.0, 1.0, 1.0), (-1.0, -1.0, -1.0), (1e-9, 1e-9, 1e-9), (1e6, 1e6, 1e6), (float("nan"), 1.0, 1.0)]
)
def test_mesh_scale_not_reasonable(scale: tuple[float, float, float]) -> None:
    robot = _mutated()
    robot.links["l0"].collisions = [Collision(geometry=MeshGeometry("m.stl", scale))]
    assert "mesh_scale_invalid" in rules_of(robot)


def test_mesh_scale_anisotropic_and_bounds_are_settings() -> None:
    robot = _mutated()
    robot.links["l0"].collisions = [Collision(geometry=MeshGeometry("m.stl", (1.0, 2.0, 1.0)))]
    assert rules_of(robot) == {"mesh_scale_anisotropic"}
    robot.links["l0"].collisions = [Collision(geometry=MeshGeometry("m.stl", (0.001, 0.001, 0.001)))]
    assert rules_of(robot) == set()
    assert rules_of(robot, limits=PhysicalLimits(mesh_scale_min=0.01)) == {"mesh_scale_invalid"}


def test_limits_from_config_ignore_bad_values() -> None:
    defaults = PhysicalLimits()
    assert PhysicalLimits.from_config({}) == defaults
    bad = {"physical_max_length_m": "big", "physical_max_mass_kg": -1, "physical_max_angle_rad": True}
    assert PhysicalLimits.from_config(bad) == defaults
    assert PhysicalLimits.from_config({"physical_max_length_m": 5}).max_length_m == 5.0


# --- the text -----------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_rule_has_a_text_in_every_language(language: str) -> None:
    table = i18n.load_language(language)
    for key in ("PHYS_LINE", "PHYS_NONE", "PHYS_SUMMARY", "PHYS_ERROR", "PHYS_USAGE"):
        assert table.get(key), (language, key)
    for rule in RULES:
        assert table.get("PHYS_R_" + rule), (language, rule)
        assert table.get("PHYS_F_" + rule), (language, rule)


@pytest.mark.parametrize("language", LANGUAGES[1:])
def test_the_texts_are_translated_and_keep_their_placeholders(language: str) -> None:
    english, table = i18n.load_language("english"), i18n.load_language(language)
    for key in [k for k in english if k.startswith("PHYS_")]:
        if key != "PHYS_LINE" and len(english[key]) > 12:
            assert table[key] != english[key], (language, key)
        for placeholder in ("{fix}", "{count}", "{file}", "{error}", "{element}", "{value}", "{limit}", "{what}", "{rule}"):
            assert (placeholder in english[key]) == (placeholder in table[key]), (language, key, placeholder)


def test_portuguese_is_european() -> None:
    table = i18n.load_language("portuguese")
    text = " ".join(v for k, v in table.items() if k.startswith("PHYS_")).lower()
    assert "ficheiro" in text
    assert "arquivo" not in text


def test_a_line_names_rule_element_value_limit_and_suggestion() -> None:
    robot = _mutated()
    robot.links["l0"].inertial = Inertial(mass=-2.0, ixx=1, iyy=1, izz=1)
    english = i18n.load_language("english")

    def translate(key: str, **kwargs: object) -> str:
        return english.get(key, key).format(**kwargs)

    assert physical_warning_lines(robot, translate) == [
        "[mass_not_positive] Mass is not above 0 - link:l0: -2 (limit: > 0). "
        "Suggestion: Set a mass above 0 (for example 0.001 kg) or remove the inertial"
    ]


def test_nothing_is_changed_in_the_robot() -> None:
    robot = random_valid_robot(5)
    robot.links["l0"].inertial = Inertial(mass=-1.0, ixx=1, iyy=1, izz=9)
    before = copy.deepcopy(robot)
    check_robot(robot)
    assert robot == before


# --- the switch ---------------------------------------------------------------------------------------------------------


def _controller(monkeypatch: pytest.MonkeyPatch, config: dict) -> EditorController:
    monkeypatch.setattr("hydra_editor_urdf.i18n.load_config", lambda: config)
    return EditorController()


def test_the_report_has_the_physical_warnings_only_when_the_switch_is_on(monkeypatch: pytest.MonkeyPatch) -> None:
    robot = _mutated()
    robot.links["l0"].inertial = Inertial(mass=0.0, ixx=1, iyy=1, izz=1)
    off = _controller(monkeypatch, {})
    assert off._report(robot).warnings == []
    on = _controller(monkeypatch, {"physical_check": True})
    report = on._report(robot)
    assert any("mass_not_positive" in w for w in report.warnings)
    assert report.is_feasible == off._report(robot).is_feasible  # a warning never changes feasibility
    assert off._report(robot).reasons == report.reasons


def test_a_non_boolean_switch_is_off(monkeypatch: pytest.MonkeyPatch) -> None:
    robot = _mutated()
    robot.links["l0"].inertial = Inertial(mass=0.0, ixx=1, iyy=1, izz=1)
    assert _controller(monkeypatch, {"physical_check": "true"})._report(robot).warnings == []


def test_the_switch_is_off_without_a_setting(monkeypatch: pytest.MonkeyPatch) -> None:
    assert EditorController._switch("physical_check") is False
    monkeypatch.setattr("hydra_editor_urdf.i18n.load_config", lambda: {})
    assert EditorController._switch("physical_check") is False


def test_physical_warning_lines_work_on_demand_without_the_switch(monkeypatch: pytest.MonkeyPatch) -> None:
    robot = _mutated()
    robot.links["l0"].inertial = Inertial(mass=0.0, ixx=1, iyy=1, izz=1)
    controller = _controller(monkeypatch, {})
    assert controller.physical_warning_lines() == []  # no robot loaded
    controller.robot = robot
    assert controller.physical_warning_lines()


# --- the command line ---------------------------------------------------------------------------------------------------

GOOD = """<robot name="r">
  <link name="a"><inertial><mass value="1"/><inertia ixx="1" iyy="1" izz="1" ixy="0" ixz="0" iyz="0"/></inertial></link>
  <link name="b"/>
  <joint name="j" type="revolute"><parent link="a"/><child link="b"/><axis xyz="0 0 1"/>
    <limit lower="-1" upper="1" effort="5" velocity="2"/></joint>
</robot>"""
BAD = GOOD.replace('<mass value="1"/>', '<mass value="0"/>')


def _run(*args: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    code = run_cli(["main.py", "--cli", *args], out, err)
    return code, out.getvalue(), err.getvalue()


def test_cli_clean_model(tmp_path: Path) -> None:
    path = tmp_path / "good.urdf"
    path.write_text(GOOD, encoding="utf-8")
    code, out, _err = _run("physical-check", str(path))
    assert code == EXIT_CLEAN
    assert out.strip() == i18n._("PHYS_NONE")
    code, out, _err = _run("physical-check", str(path), "--json")
    assert code == EXIT_CLEAN and json.loads(out) == []


def test_cli_warnings_text_and_json(tmp_path: Path) -> None:
    path = tmp_path / "bad.urdf"
    path.write_text(BAD, encoding="utf-8")
    code, out, _err = _run("physical-check", str(path))
    assert code == EXIT_WARNINGS
    assert "[mass_not_positive]" in out and "link:a" in out
    code, out, _err = _run("physical-check", str(path), "--json")
    data = json.loads(out)
    assert code == EXIT_WARNINGS
    assert data[0]["rule"] == "mass_not_positive"
    assert set(data[0]) == {"rule", "element", "value", "limit", "fix", "message"}
    assert path.read_text(encoding="utf-8") == BAD  # never written


def test_cli_duplicate_names_are_reported_not_a_parse_error(tmp_path: Path) -> None:
    path = tmp_path / "dup.urdf"
    path.write_text('<robot name="r"><link name="a"/><link name="a"/></robot>', encoding="utf-8")
    code, out, _err = _run("physical-check", str(path), "--json")
    assert code == EXIT_WARNINGS
    assert json.loads(out)[0]["rule"] == "duplicate_name"


def test_cli_errors(tmp_path: Path) -> None:
    assert _run("physical-check", str(tmp_path / "missing.urdf"))[0] == EXIT_ERROR
    broken = tmp_path / "broken.urdf"
    broken.write_text("<robot", encoding="utf-8")
    assert _run("physical-check", str(broken))[0] == EXIT_ERROR
    assert _run("physical-check")[0] == EXIT_ERROR
    assert _run("physical-check", "a.urdf", "b.urdf")[0] == EXIT_ERROR
    assert _run("physical-check", "a.urdf", "--nope")[0] == EXIT_ERROR
    assert _run("unknown")[0] == EXIT_ERROR
    assert _run()[0] == EXIT_ERROR


def test_cli_finds_the_meshes_beside_the_model(tmp_path: Path) -> None:
    text = GOOD.replace('<link name="b"/>', '<link name="b"><visual><geometry><mesh filename="m/part.stl"/></geometry></visual></link>')
    path = tmp_path / "m.urdf"
    path.write_text(text, encoding="utf-8")
    code, out, _err = _run("physical-check", str(path), "--json")
    assert code == EXIT_WARNINGS and json.loads(out)[0]["rule"] == "mesh_missing"
    (tmp_path / "m").mkdir()
    (tmp_path / "m" / "part.stl").write_bytes(b"solid x\nendsolid x\n")
    assert _run("physical-check", str(path))[0] == EXIT_CLEAN
    assert _run("physical-check", str(path), "--mesh-root", str(tmp_path))[0] == EXIT_CLEAN


def test_main_py_answers_the_cli_without_qt(tmp_path: Path) -> None:
    path = tmp_path / "bad.urdf"
    path.write_text(BAD, encoding="utf-8")
    probe = "\n".join(
        [
            "import sys, runpy",
            "sys.argv = ['main.py', '--cli', 'physical-check', sys.argv[1]]",
            "try:",
            "    runpy.run_path('main.py', run_name='__main__')",
            "except SystemExit as e:",
            "    print('QT' if any(m.startswith('PySide6') for m in sys.modules) else 'NOQT', e.code)",
        ]
    )
    env_path = str(ROOT)
    result = subprocess.run(
        [sys.executable, "-c", probe, str(path)],
        cwd=ROOT,
        env={**__import__("os").environ, "PYTHONPATH": env_path},
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.stdout is not None and result.stdout.strip().endswith("NOQT 1"), result.stdout + result.stderr
