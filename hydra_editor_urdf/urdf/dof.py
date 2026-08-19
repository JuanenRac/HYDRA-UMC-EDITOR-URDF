# =============================================================================
# HYDRA-UMC EDITOR-URDF - urdf/dof.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# DOF counting and feasibility validation against HYDRA-UMC-STUDIO's own
# real, current support - the automated version of the exact judgment
# call this ecosystem's own sessions made by hand for every robot added
# to STUDIO's catalog so far: STUDIO models 3, 4, 5, and 6-DOF serial
# chains (src/store.tsx's own RobotState.joints is a fixed j1..j6 map;
# see that project's own kinematics code for the real, current ceiling)
# - a handful of real, license-clear candidate arms researched during
# that work were 7/8/9-DOF and were discarded for exactly this reason,
# not hypothetically. MIN/MAX_SUPPORTED_DOF below is this app's own single
# source of truth for that number - if STUDIO's own real ceiling changes
# later, update it HERE, not by re-deriving the number from scratch again.
# =============================================================================
from __future__ import annotations

from dataclasses import dataclass, field

from hydra_editor_urdf.models import JointType, Robot

MIN_SUPPORTED_DOF = 3
MAX_SUPPORTED_DOF = 6

# Joint types HYDRA-UMC-STUDIO's own kinematics has no representation for
# at all today, regardless of how many of them a chain has - a single
# FLOATING or PLANAR joint anywhere in the chain makes the whole robot
# infeasible the same way too many/too few revolute/prismatic joints does,
# since STUDIO's own joint model has no concept of either.
UNSUPPORTED_JOINT_TYPES = (JointType.FLOATING, JointType.PLANAR)


@dataclass
class DofReport:
    """Everything ui/panels/dof_panel.py needs to render the feasibility
    verdict in one pass, without re-walking the tree itself."""

    dof_count: int
    movable_joint_names: list[str] = field(default_factory=list)
    unsupported_joint_names: list[str] = field(default_factory=list)  # FLOATING/PLANAR found, by name
    is_feasible: bool = False
    reasons: list[str] = field(default_factory=list)  # human-readable, one entry per problem found - empty iff is_feasible
    # None if the tree has no single root (broken/forked/cyclic parent-
    # child graph) - see models.Robot.root_link_name() for the exact rule.
    root_link_name: str | None = None
    orphan_link_names: list[str] = field(default_factory=list)  # links reachable from no joint at all
    disconnected_link_names: list[str] = field(default_factory=list)  # a real chain of >1 link, but reachable from no root


def _reachable_from(robot: Robot, root: str) -> set[str]:
    reachable = {root}
    frontier = [root]
    by_parent = robot.joints_by_parent()
    while frontier:
        current = frontier.pop()
        for joint in by_parent.get(current, []):
            if joint.child not in reachable:
                reachable.add(joint.child)
                frontier.append(joint.child)
    return reachable


def validate(robot: Robot) -> DofReport:
    movable = robot.movable_joints()
    unsupported = [j.name for j in robot.joints.values() if j.type in UNSUPPORTED_JOINT_TYPES]
    root = robot.root_link_name()

    reasons: list[str] = []

    if root is None:
        child_names = {j.child for j in robot.joints.values()}
        candidate_roots = [name for name in robot.links if name not in child_names]
        if len(candidate_roots) == 0:
            reasons.append("No root link found - every link is some joint's child (the parent/child graph has a cycle, or references a link that doesn't exist).")
        else:
            reasons.append(f"Found {len(candidate_roots)} candidate root links ({', '.join(candidate_roots)}) - a URDF must have exactly one, this looks like more than one disconnected tree.")

    reachable = _reachable_from(robot, root) if root is not None else set()
    disconnected = sorted(set(robot.links) - reachable) if root is not None else []
    # A link with no visual/collision geometry at all AND not referenced
    # by any joint as parent or child is very likely leftover/unused, not
    # a real modeling error - reported separately from "disconnected"
    # (which implies it WAS meant to be part of the chain but the joint
    # linking it in is missing/broken).
    referenced = {j.parent for j in robot.joints.values()} | {j.child for j in robot.joints.values()}
    orphans = sorted(name for name in robot.links if name not in referenced and name != root)

    if disconnected:
        reasons.append(f"{len(disconnected)} link(s) not reachable from the root link by any joint chain: {', '.join(disconnected)}.")

    if unsupported:
        reasons.append(
            f"{len(unsupported)} joint(s) use a type HYDRA-UMC-STUDIO's kinematics doesn't support at all "
            f"(FLOATING/PLANAR): {', '.join(unsupported)}."
        )

    dof_count = len(movable)
    if dof_count < MIN_SUPPORTED_DOF:
        reasons.append(f"{dof_count} DOF is below HYDRA-UMC-STUDIO's supported range ({MIN_SUPPORTED_DOF}-{MAX_SUPPORTED_DOF} DOF).")
    elif dof_count > MAX_SUPPORTED_DOF:
        reasons.append(
            f"{dof_count} DOF exceeds HYDRA-UMC-STUDIO's supported range ({MIN_SUPPORTED_DOF}-{MAX_SUPPORTED_DOF} DOF) - "
            f"this is the same reason several real 7/8/9-DOF candidate arms were discarded from STUDIO's catalog in the past."
        )

    for joint in movable:
        if joint.type != JointType.CONTINUOUS and joint.limit is None:
            reasons.append(f"Joint {joint.name!r} ({joint.type.value}) has no <limit> - required by the URDF spec for anything but a CONTINUOUS joint.")

    return DofReport(
        dof_count=dof_count,
        movable_joint_names=[j.name for j in movable],
        unsupported_joint_names=unsupported,
        is_feasible=not reasons,
        reasons=reasons,
        root_link_name=root,
        orphan_link_names=orphans,
        disconnected_link_names=disconnected,
    )
