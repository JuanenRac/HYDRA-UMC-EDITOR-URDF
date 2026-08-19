# =============================================================================
# HYDRA-UMC EDITOR-URDF - models.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# The in-memory URDF data model - what urdf/parser.py builds from XML,
# what every UI panel reads/edits, and what urdf/writer.py serializes back
# out. Deliberately a plain, mutable, in-house dataclass tree rather than
# wrapping an existing Python URDF library (e.g. `urdfpy` or `yourdfpy`):
# this app needs to EDIT the tree interactively (recolor a link, rescale
# a mesh, retype a joint) and re-render every change live, which a
# read-mostly parsing library isn't shaped for - and per the project
# owner's own explicit request ("procura hacer muchos archivos de codigo
# fuente"), owning this model outright keeps it small, inspectable, and
# free of a third-party dependency's own release cadence.
#
# Field names and defaults follow the real URDF XML schema
# (http://wiki.ros.org/urdf/XML) as closely as a Python dataclass allows,
# so parser.py/writer.py stay a thin, obvious XML<->object mapping rather
# than inventing a parallel vocabulary.
# =============================================================================
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class JointType(str, Enum):
    """The 6 joint types the URDF spec defines. This app's own DOF count
    (urdf/dof.py) only ever counts REVOLUTE/CONTINUOUS/PRISMATIC as
    contributing a real degree of freedom - FIXED contributes none,
    FLOATING/PLANAR are accepted for parsing/round-tripping fidelity but
    HYDRA-UMC-STUDIO's own kinematics (server-side + every *Arm.tsx) has
    no support for either today, so a chain that uses one gets flagged
    infeasible the same way a >6-DOF chain does (see urdf/dof.py)."""

    REVOLUTE = "revolute"
    CONTINUOUS = "continuous"
    PRISMATIC = "prismatic"
    FIXED = "fixed"
    FLOATING = "floating"
    PLANAR = "planar"


# Joint types that add a real, controllable degree of freedom.
MOVABLE_JOINT_TYPES = (JointType.REVOLUTE, JointType.CONTINUOUS, JointType.PRISMATIC)


@dataclass
class Origin:
    """<origin xyz="x y z" rpy="r p y"/> - meters and radians, URDF's own
    units. Every optional <origin> in the spec defaults to identity if
    omitted; Origin.identity() below is that default, used instead of
    letting `None` propagate through every consumer as a special case."""

    xyz: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rpy: tuple[float, float, float] = (0.0, 0.0, 0.0)

    @staticmethod
    def identity() -> "Origin":
        return Origin()


@dataclass
class BoxGeometry:
    size: tuple[float, float, float] = (1.0, 1.0, 1.0)


@dataclass
class CylinderGeometry:
    radius: float = 0.5
    length: float = 1.0


@dataclass
class SphereGeometry:
    radius: float = 0.5


@dataclass
class MeshGeometry:
    """`filename` is kept exactly as written in the source URDF (often a
    `package://` URI, sometimes a relative path) - source/scan.py is what
    resolves it to a real file on disk; this dataclass doesn't assume
    either form. `scale` defaults to (1,1,1) per the URDF spec, and is
    the ONE geometry field the "Modify scale" editing feature (per the
    owner's own explicit ask) actually mutates - scaling a mesh's
    triangle data itself would be destructive and lossy on every re-edit,
    scaling the transform is not."""

    filename: str = ""
    scale: tuple[float, float, float] = (1.0, 1.0, 1.0)


Geometry = BoxGeometry | CylinderGeometry | SphereGeometry | MeshGeometry


@dataclass
class Material:
    """<material> - either a bare color (rgba, 0-1 each channel) or a
    named reference to a <material> declared once at <robot> level and
    reused by name across several <visual> elements (the URDF spec allows
    both forms; this app resolves a name-only reference against
    Robot.materials at parse time so every consumer here always sees a
    real rgba, never a name it has to look up itself)."""

    name: str = ""
    rgba: tuple[float, float, float, float] = (0.8, 0.8, 0.8, 1.0)


@dataclass
class Visual:
    name: str = ""
    origin: Origin = field(default_factory=Origin.identity)
    geometry: Geometry = field(default_factory=BoxGeometry)
    material: Material | None = None


@dataclass
class Collision:
    name: str = ""
    origin: Origin = field(default_factory=Origin.identity)
    geometry: Geometry = field(default_factory=BoxGeometry)


@dataclass
class Inertial:
    """Optional per URDF spec - a link with none is legal (common for a
    purely-visual/fixed link) and gets STUDIO's own generic defaults on
    export (see urdf/writer.py) rather than a fabricated mass/inertia
    tensor this app has no real way to compute without the operator
    supplying it."""

    mass: float = 0.0
    origin: Origin = field(default_factory=Origin.identity)
    ixx: float = 0.0
    ixy: float = 0.0
    ixz: float = 0.0
    iyy: float = 0.0
    iyz: float = 0.0
    izz: float = 0.0


@dataclass
class Link:
    name: str
    visuals: list[Visual] = field(default_factory=list)
    collisions: list[Collision] = field(default_factory=list)
    inertial: Inertial | None = None


@dataclass
class JointLimit:
    """Required by the URDF spec for REVOLUTE/PRISMATIC (optional/ignored
    for CONTINUOUS, which is unbounded by definition). `effort`/`velocity`
    are carried through for round-tripping even though this app's own
    live-jog preview (ui/panels/viewport_panel.py) only ever needs
    lower/upper."""

    lower: float = 0.0
    upper: float = 0.0
    effort: float = 0.0
    velocity: float = 0.0


@dataclass
class Joint:
    name: str
    type: JointType
    parent: str  # parent link name
    child: str  # child link name
    origin: Origin = field(default_factory=Origin.identity)
    axis: tuple[float, float, float] = (1.0, 0.0, 0.0)
    limit: JointLimit | None = None

    @property
    def is_movable(self) -> bool:
        return self.type in MOVABLE_JOINT_TYPES


@dataclass
class Robot:
    """The whole parsed/edited tree - one <robot> element's worth. Links
    and joints are kept in insertion order (plain dict, Python 3.7+
    preserves it) so a re-exported URDF reads in roughly the same order
    as the source, which matters for a human diffing the two."""

    name: str = "robot"
    links: dict[str, Link] = field(default_factory=dict)
    joints: dict[str, Joint] = field(default_factory=dict)
    # Top-level <material name="..."> declarations, resolved into every
    # Visual.material that references one by name at parse time - kept
    # here too so writer.py can re-emit the same shared declarations
    # instead of duplicating the rgba inline on every link that uses it.
    materials: dict[str, Material] = field(default_factory=dict)

    def joints_by_parent(self) -> dict[str, list[Joint]]:
        result: dict[str, list[Joint]] = {}
        for joint in self.joints.values():
            result.setdefault(joint.parent, []).append(joint)
        return result

    def root_link_name(self) -> str | None:
        """The one link that is never any joint's `child` - URDF requires
        exactly one (a proper tree, not a forest or a cycle); returns
        None if the model has zero links, or is malformed in a way that
        leaves either zero or more than one candidate (urdf/dof.py's own
        validate() is what surfaces that as a real user-facing error -
        this method just reports what it finds, doesn't judge it)."""
        child_names = {j.child for j in self.joints.values()}
        roots = [name for name in self.links if name not in child_names]
        return roots[0] if len(roots) == 1 else None

    def movable_joints(self) -> list[Joint]:
        return [j for j in self.joints.values() if j.is_movable]
