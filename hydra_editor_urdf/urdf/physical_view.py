# =============================================================================
# HYDRA-UMC EDITOR-URDF - urdf/physical_view.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""What the "Physical validation" panel shows, without Qt: the rows, their severity, the filters, the order and the JSON.

Both interfaces (the classic dock and the Qt Quick deck) use this module, so they show the same rows in the same order and
export the same JSON. It is read-only: a row carries the suggestion of the rule as text and nothing here changes a robot.

The severity is a property of the rule (the physical check itself has none):

  error    the model cannot be simulated or is not a valid tree or body (no root, a cycle, a mass of zero, a tensor no solid
           has, inverted limits, a zero axis, a name used twice, a mesh scale that is not positive)
  warning  it can be loaded but is probably wrong (a missing limit, a mesh that is not found, a link out of reach)
  hint     a guess from the size of a number (millimetres, degrees, grams) or a stretched mesh
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable, Iterable, Sequence

from hydra_editor_urdf.urdf.physical_check import RULES, PhysicalWarning

SEVERITIES = ("error", "warning", "hint")

SEVERITY_OF_RULE: dict[str, str] = {
    "tree_no_root": "error",
    "tree_multiple_roots": "error",
    "tree_cycle": "error",
    "tree_orphan_link": "warning",
    "tree_unreachable_link": "warning",
    "tree_multiple_parents": "error",
    "tree_unknown_link": "error",
    "duplicate_name": "error",
    "mass_not_positive": "error",
    "inertia_not_finite": "error",
    "inertia_not_positive_definite": "error",
    "inertia_triangle": "error",
    "limit_missing": "warning",
    "limit_inverted": "error",
    "velocity_not_positive": "warning",
    "effort_not_positive": "warning",
    "continuous_with_limits": "warning",
    "axis_zero": "error",
    "axis_not_unit": "warning",
    "mesh_missing": "warning",
    "mesh_scale_invalid": "error",
    "mesh_scale_anisotropic": "hint",
    "units_length": "hint",
    "units_angle": "hint",
    "units_mass": "hint",
}

SORT_KEYS = ("severity", "rule", "element")

Translate = Callable[..., str]


def severity_of(rule: str) -> str:
    """The severity of a rule. A rule this module does not know is shown as a warning (never hidden)."""
    return SEVERITY_OF_RULE.get(rule, "warning")


@dataclass(frozen=True)
class PhysicalRow:
    """One row of the panel: the finding of the check and its texts in the language of the editor."""

    severity: str
    rule: str
    element: str
    value: str
    limit: str
    what: str
    suggestion: str
    fix: str

    def as_dict(self) -> dict[str, str]:
        return {
            "severity": self.severity,
            "rule": self.rule,
            "element": self.element,
            "value": self.value,
            "limit": self.limit,
            "message": self.what,
            "suggestion": self.suggestion,
            "fix": self.fix,
        }


def build_rows(warnings: Iterable[PhysicalWarning], translate: Translate) -> list[PhysicalRow]:
    """The rows of `warnings`, in the order of the check (by rule, then element, then value)."""
    return [
        PhysicalRow(
            severity=severity_of(w.rule),
            rule=w.rule,
            element=w.element,
            value=w.value,
            limit=w.limit,
            what=translate("PHYS_R_" + w.rule),
            suggestion=translate("PHYS_F_" + w.rule, fix=w.fix, value=w.value, limit=w.limit),
            fix=w.fix,
        )
        for w in warnings
    ]


def filter_rows(rows: Sequence[PhysicalRow], severity: str = "", rule: str = "", element: str = "") -> list[PhysicalRow]:
    """The rows that match every filter that is set. `severity` and `rule` are exact (empty = any); `element` matches when
    the text appears in the element name, ignoring case and surrounding blanks."""
    needle = element.strip().lower()
    return [
        row
        for row in rows
        if (not severity or row.severity == severity)
        and (not rule or row.rule == rule)
        and (not needle or needle in row.element.lower())
    ]


def sort_rows(rows: Sequence[PhysicalRow], key: str = "severity", descending: bool = False) -> list[PhysicalRow]:
    """The rows sorted by `severity` (errors first), `rule` (the order of the check) or `element`; a tie is broken by the
    order of the check, so the result is deterministic. An unknown key leaves the order of the check."""
    if key not in SORT_KEYS:
        return list(rows)
    position = {id(row): index for index, row in enumerate(rows)}
    rule_rank = {rule: index for index, rule in enumerate(RULES)}

    def sort_key(row: PhysicalRow) -> tuple:
        if key == "severity":
            primary: object = SEVERITIES.index(row.severity) if row.severity in SEVERITIES else len(SEVERITIES)
        elif key == "rule":
            primary = rule_rank.get(row.rule, len(rule_rank))
        else:
            primary = row.element.lower()
        return (primary, position[id(row)])

    return sorted(rows, key=sort_key, reverse=descending)


def counts_by_severity(rows: Iterable[PhysicalRow]) -> dict[str, int]:
    counts = {name: 0 for name in SEVERITIES}
    for row in rows:
        counts[row.severity] = counts.get(row.severity, 0) + 1
    return counts


def rules_present(rows: Iterable[PhysicalRow]) -> list[str]:
    """The rules that have at least one row, in the order of the check (for the rule filter)."""
    found = {row.rule for row in rows}
    return [rule for rule in RULES if rule in found] + sorted(found - set(RULES))


def rows_to_json(rows: Sequence[PhysicalRow]) -> str:
    """The rows as a JSON list of objects (`severity`, `rule`, `element`, `value`, `limit`, `message`, `suggestion`, `fix`),
    the same keys on every call so that two exports of the same model are the same text."""
    return json.dumps([row.as_dict() for row in rows], ensure_ascii=False, indent=2)
