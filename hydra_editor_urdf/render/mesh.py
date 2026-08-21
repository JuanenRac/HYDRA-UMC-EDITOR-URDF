# =============================================================================
# HYDRA-UMC EDITOR-URDF - render/mesh.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Mesh loading for whatever a real-world URDF's <mesh filename="..."/>
# points at. STL (via numpy-stl) is first-class and battle-tested - this
# is a near-verbatim port of HYDRA-UMC-SUITE's own render/mesh.py
# load_stl(), per [[No reference -> reuse, don't invent]]. OBJ gets a
# small hand-rolled loader (Wavefront OBJ's triangle/vertex/normal syntax
# is simple enough not to need a dependency) since a real robot
# description repo ships OBJ almost as often as STL. DAE (COLLADA) is
# NOT supported - it's a much larger XML scene-graph format (skeletal
# animation, multiple coordinate systems, embedded materials/textures)
# that would need its own real parser to do honestly rather than a
# best-effort guess at the handful of tags a "simple" DAE happens to use
# - see SONNET/HYDRA-UMC-EDITOR-URDF/mejoras_futuras.txt. load_mesh_file()
# below raises UnsupportedMeshFormat for .dae (and anything else
# unrecognized) with that limitation spelled out, rather than silently
# skipping the link or crashing on a bare KeyError deep in some other
# module.
# =============================================================================
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from stl import mesh as stl_mesh


class UnsupportedMeshFormat(Exception):
    """Raised by load_mesh_file() for any extension this app can't load
    (.dae today, or anything simply not implemented). Always carries a
    human-readable message - see this file's own header for why .dae
    specifically isn't attempted rather than half-supported."""


class MalformedMeshFile(Exception):
    """Raised by load_obj() for a file whose extension IS supported but
    whose content violates the Wavefront OBJ spec in a way this loader
    can detect (today: a literal `0` vertex/normal index in an `f` line -
    OBJ indices are 1-based, so 0 is never valid, positive or negative).
    Caught by render/viewport.py's own _build_visual_mesh() the same way
    as UnsupportedMeshFormat (skip that one visual, don't crash the whole
    rebuild) - kept as its own exception type rather than reusing
    UnsupportedMeshFormat because the failure here is "this specific file
    is broken", not "this app doesn't support this format at all"."""


@dataclass
class Mesh:
    """Flat vertex+normal arrays ready for a GL_TRIANGLES VBO - 3 vertices
    per triangle, no index buffer, same shape HYDRA-UMC-SUITE's own
    render/mesh.py produces."""

    vertices: np.ndarray  # (N, 3) float32
    normals: np.ndarray  # (N, 3) float32, one per vertex (== per-face, repeated 3x for STL; real per-vertex for OBJ when the source file has them)

    @property
    def triangle_count(self) -> int:
        return len(self.vertices) // 3

    def scaled(self, scale: tuple[float, float, float]) -> "Mesh":
        """Returns a new Mesh with `scale` applied to every vertex -
        non-uniform scale needs the normals re-orthogonalized too (a
        plain per-axis multiply on a normal is only correct for uniform
        scale), which is why this isn't just `vertices * scale` inline
        at every call site. Used by the "Modify scale" editing feature
        (models.MeshGeometry.scale) without mutating the cached, disk-
        loaded original - see render/kinematics.py's own mesh cache."""
        s = np.array(scale, dtype=np.float32)
        new_vertices = self.vertices * s
        if scale[0] == scale[1] == scale[2]:
            return Mesh(vertices=new_vertices, normals=self.normals.copy())
        # Non-uniform scale: normals transform by the inverse-transpose of
        # the scale matrix (diagonal here, so inverse-transpose is just
        # elementwise reciprocal), then re-normalize.
        inv_s = 1.0 / np.where(s == 0, 1.0, s)
        new_normals = self.normals * inv_s
        lengths = np.linalg.norm(new_normals, axis=1, keepdims=True)
        lengths[lengths < 1e-12] = 1.0
        new_normals = new_normals / lengths
        return Mesh(vertices=new_vertices, normals=new_normals)


def _guard_mm_vs_m_scale(vertices: np.ndarray) -> np.ndarray:
    """Same defensive mm-vs-m check HYDRA-UMC-STUDIO's own useRealScaleSTL()
    and HYDRA-UMC-SUITE's own render/mesh.py apply - a surprising number of
    real-world exported meshes are authored in millimeters without saying
    so anywhere the file format can record. A single robot link bigger
    than 5 real-world meters in any axis is far more likely to be a
    millimeter-scale mesh than an actual giant robot part."""
    span = vertices.max(axis=0) - vertices.min(axis=0)
    if float(np.max(span)) > 5.0:
        return vertices * 0.001
    return vertices


def load_stl(path: str | Path) -> Mesh:
    raw = stl_mesh.Mesh.from_file(str(path))
    vertices = _guard_mm_vs_m_scale(raw.vectors.reshape(-1, 3).astype(np.float32))

    normals = np.repeat(raw.normals.astype(np.float32), 3, axis=0)
    lengths = np.linalg.norm(normals, axis=1, keepdims=True)
    lengths[lengths < 1e-12] = 1.0
    normals = normals / lengths

    return Mesh(vertices=vertices, normals=normals)


def load_obj(path: str | Path) -> Mesh:
    """Minimal Wavefront OBJ loader - `v`/`vn`/`f` only (no material
    library, no texture coordinates, no quad-to-triangle-fan for anything
    beyond a plain triangle/quad face). Good enough for a robot
    description repo's own visual meshes, which are triangulated exports
    from CAD in the overwhelming majority of cases - a face with more
    than 4 vertices is fan-triangulated from its first vertex, the same
    simple rule most OBJ consumers apply."""
    path = Path(path)  # normalized up front so the MalformedMeshFile messages below can always use path.name, even when called with a bare str
    positions: list[tuple[float, float, float]] = []
    normals_in: list[tuple[float, float, float]] = []
    out_vertices: list[tuple[float, float, float]] = []
    out_normals: list[tuple[float, float, float]] = []

    def emit_triangle(idx_a: tuple[int, int | None], idx_b: tuple[int, int | None], idx_c: tuple[int, int | None]) -> None:
        pa, pb, pc = positions[idx_a[0]], positions[idx_b[0]], positions[idx_c[0]]
        if idx_a[1] is not None and idx_b[1] is not None and idx_c[1] is not None:
            na, nb, nc = normals_in[idx_a[1]], normals_in[idx_b[1]], normals_in[idx_c[1]]
        else:
            # No per-vertex normals in the file - derive one flat face
            # normal from the winding order, same honesty tradeoff
            # render/mesh.py's own STL loader documents for flat shading.
            v1 = np.array(pb) - np.array(pa)
            v2 = np.array(pc) - np.array(pa)
            n = np.cross(v1, v2)
            length = np.linalg.norm(n)
            n = (n / length) if length > 1e-12 else np.array([0.0, 0.0, 1.0])
            na = nb = nc = tuple(n)
        for p, n in ((pa, na), (pb, nb), (pc, nc)):
            out_vertices.append(p)
            out_normals.append(n)

    def parse_face_token(token: str) -> tuple[int, int | None]:
        # "v", "v/vt", "v/vt/vn", or "v//vn" - only v (position) and vn
        # (normal) matter here, vt (texcoord) is parsed and discarded.
        parts = token.split("/")
        v_raw = int(parts[0])
        if v_raw == 0:
            # OBJ indices are 1-based; 0 is never valid (neither the
            # first vertex nor a legal negative/relative offset) - without
            # this check it fell into the "else" branch meant for
            # negative indices and computed len(positions) + 0, an
            # out-of-range index that raised a bare IndexError with no
            # hint that the source .obj itself is malformed.
            raise MalformedMeshFile(f"{path.name}: face token {token!r} uses vertex index 0, which is invalid - OBJ indices are 1-based (no zero index).")
        v_idx = v_raw - 1 if v_raw > 0 else len(positions) + v_raw  # OBJ allows negative (relative) indices
        n_idx = None
        if len(parts) == 3 and parts[2]:
            n_raw = int(parts[2])
            if n_raw == 0:
                raise MalformedMeshFile(f"{path.name}: face token {token!r} uses normal index 0, which is invalid - OBJ indices are 1-based (no zero index).")
            n_idx = n_raw - 1 if n_raw > 0 else len(normals_in) + n_raw
        return v_idx, n_idx

    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            tag = parts[0]
            if tag == "v" and len(parts) >= 4:
                positions.append((float(parts[1]), float(parts[2]), float(parts[3])))
            elif tag == "vn" and len(parts) >= 4:
                normals_in.append((float(parts[1]), float(parts[2]), float(parts[3])))
            elif tag == "f" and len(parts) >= 4:
                face = [parse_face_token(tok) for tok in parts[1:]]
                for i in range(1, len(face) - 1):
                    emit_triangle(face[0], face[i], face[i + 1])

    vertices = _guard_mm_vs_m_scale(np.array(out_vertices, dtype=np.float32))
    normals = np.array(out_normals, dtype=np.float32)
    return Mesh(vertices=vertices, normals=normals)


def make_box_mesh(size: tuple[float, float, float]) -> Mesh:
    """An axis-aligned box centered on its own local origin - stands in
    for a URDF <box size="x y z"/> primitive, ported from HYDRA-UMC-SUITE's
    own render/mesh.py make_box_mesh() (there parameterized as 3 separate
    args; here as the one tuple models.BoxGeometry.size already carries)."""
    x, y, z = size[0] / 2.0, size[1] / 2.0, size[2] / 2.0
    faces = [
        ((0, 0, 1), [(-x, -y, z), (x, -y, z), (x, y, z), (-x, y, z)]),
        ((0, 0, -1), [(x, -y, -z), (-x, -y, -z), (-x, y, -z), (x, y, -z)]),
        ((0, 1, 0), [(-x, y, z), (x, y, z), (x, y, -z), (-x, y, -z)]),
        ((0, -1, 0), [(-x, -y, -z), (x, -y, -z), (x, -y, z), (-x, -y, z)]),
        ((1, 0, 0), [(x, -y, z), (x, -y, -z), (x, y, -z), (x, y, z)]),
        ((-1, 0, 0), [(-x, -y, -z), (-x, -y, z), (-x, y, z), (-x, y, -z)]),
    ]
    verts: list[tuple[float, float, float]] = []
    norms: list[tuple[float, float, float]] = []
    for n, corners in faces:
        c0, c1, c2, c3 = corners
        for v in (c0, c1, c2):
            verts.append(v)
            norms.append(n)
        for v in (c0, c2, c3):
            verts.append(v)
            norms.append(n)
    return Mesh(vertices=np.array(verts, dtype=np.float32), normals=np.array(norms, dtype=np.float32))


def make_cylinder_mesh(radius: float, length: float, segments: int = 24) -> Mesh:
    """A Z-axis cylinder centered on its own local origin, spanning
    [-length/2, +length/2] along Z - matches URDF's own <cylinder
    radius="" length=""/> convention (cylinder axis is the link's local
    Z, unlike HYDRA-UMC-SUITE's Y-axis convention in its own
    make_cylinder_mesh, which follows Three.js instead - this app stays
    in URDF's own frame throughout, see render/kinematics.py's own header)."""
    half_h = length / 2.0
    verts: list[tuple[float, float, float]] = []
    norms: list[tuple[float, float, float]] = []
    angles = [2 * np.pi * i / segments for i in range(segments + 1)]

    for i in range(segments):
        a0, a1 = angles[i], angles[i + 1]
        x0, y0 = radius * np.cos(a0), radius * np.sin(a0)
        x1, y1 = radius * np.cos(a1), radius * np.sin(a1)
        n0 = (np.cos(a0), np.sin(a0), 0.0)
        n1 = (np.cos(a1), np.sin(a1), 0.0)
        top0, top1 = (x0, y0, half_h), (x1, y1, half_h)
        bot0, bot1 = (x0, y0, -half_h), (x1, y1, -half_h)
        for v, n in ((top0, n0), (bot0, n0), (bot1, n1)):
            verts.append(v)
            norms.append(n)
        for v, n in ((top0, n0), (bot1, n1), (top1, n1)):
            verts.append(v)
            norms.append(n)

    for sign, z in ((1.0, half_h), (-1.0, -half_h)):
        center = (0.0, 0.0, z)
        for i in range(segments):
            a0, a1 = angles[i], angles[i + 1]
            p0 = (radius * np.cos(a0), radius * np.sin(a0), z)
            p1 = (radius * np.cos(a1), radius * np.sin(a1), z)
            tri = (center, p1, p0) if sign > 0 else (center, p0, p1)
            for v in tri:
                verts.append(v)
                norms.append((0.0, 0.0, sign))

    return Mesh(vertices=np.array(verts, dtype=np.float32), normals=np.array(norms, dtype=np.float32))


def make_sphere_mesh(radius: float, segments: int = 16, rings: int = 12) -> Mesh:
    """A UV sphere - URDF's <sphere radius=""/> primitive. Per-vertex
    normals are trivially the normalized position for a sphere centered
    on its own origin, no separate normal computation needed."""
    verts: list[tuple[float, float, float]] = []
    norms: list[tuple[float, float, float]] = []

    def point(ring_i: int, seg_i: int) -> tuple[float, float, float]:
        phi = np.pi * ring_i / rings  # 0 (north pole) .. pi (south pole)
        theta = 2 * np.pi * seg_i / segments
        x = radius * np.sin(phi) * np.cos(theta)
        y = radius * np.sin(phi) * np.sin(theta)
        z = radius * np.cos(phi)
        return (x, y, z)

    for ring_i in range(rings):
        for seg_i in range(segments):
            p00 = point(ring_i, seg_i)
            p01 = point(ring_i, seg_i + 1)
            p10 = point(ring_i + 1, seg_i)
            p11 = point(ring_i + 1, seg_i + 1)
            for tri in ((p00, p10, p11), (p00, p11, p01)):
                for v in tri:
                    verts.append(v)
                    length = np.linalg.norm(v)
                    norms.append(tuple(np.array(v) / length) if length > 1e-12 else (0.0, 0.0, 1.0))

    return Mesh(vertices=np.array(verts, dtype=np.float32), normals=np.array(norms, dtype=np.float32))


def load_mesh_file(path: str | Path) -> Mesh:
    """Dispatches on file extension - the one entry point
    render/kinematics.py's mesh cache and source/scan.py both use, so
    adding a new format later means touching this function alone."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".stl":
        return load_stl(path)
    if suffix == ".obj":
        return load_obj(path)
    if suffix == ".dae":
        raise UnsupportedMeshFormat(
            f"{path.name}: COLLADA (.dae) meshes aren't supported yet - convert to .stl or .obj first "
            "(e.g. via Blender's own export, or `assimp export`) and re-point this link's <mesh filename> at that file."
        )
    raise UnsupportedMeshFormat(f"{path.name}: unrecognized mesh format {suffix!r} (supported: .stl, .obj)")
