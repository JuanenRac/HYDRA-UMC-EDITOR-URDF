# =============================================================================
# HYDRA-UMC EDITOR-URDF - tests/test_scan.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
#
# Real unit tests for hydra_editor_urdf/source/scan.py against a real
# temp-directory file tree (tmp_path) - including an explicit regression
# test for the had_scheme gating bug already fixed in a prior audit pass
# (build_mesh_resolver's own "BUG (found in audit)" comment).
# =============================================================================
from __future__ import annotations

from hydra_editor_urdf.source.scan import build_mesh_resolver, find_urdf_files


def test_find_urdf_files_finds_urdf_and_xacro_recursively(tmp_path):
    (tmp_path / "robot.urdf").write_text("<robot/>")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "arm.xacro").write_text("<robot/>")
    (sub / "notes.txt").write_text("not a urdf")

    found = find_urdf_files(tmp_path)
    names = sorted(p.name for p in found)
    assert names == ["arm.xacro", "robot.urdf"]


def test_find_urdf_files_on_missing_directory_returns_empty_list(tmp_path):
    assert find_urdf_files(tmp_path / "does-not-exist") == []


def test_find_urdf_files_on_empty_directory_returns_empty_list(tmp_path):
    assert find_urdf_files(tmp_path) == []


def test_resolve_relative_to_urdf_dir(tmp_path):
    urdf_dir = tmp_path / "urdf"
    urdf_dir.mkdir()
    meshes_dir = tmp_path / "meshes"
    meshes_dir.mkdir()
    mesh_file = meshes_dir / "link1.stl"
    mesh_file.write_bytes(b"stl-data")

    resolve = build_mesh_resolver(root=tmp_path, urdf_file_dir=urdf_dir)
    result = resolve("../meshes/link1.stl")
    assert result == mesh_file.resolve()


def test_resolve_absolute_path_that_exists(tmp_path):
    mesh_file = tmp_path / "link1.stl"
    mesh_file.write_bytes(b"stl-data")
    resolve = build_mesh_resolver(root=tmp_path, urdf_file_dir=tmp_path)
    result = resolve(str(mesh_file))
    assert result == mesh_file


def test_resolve_package_uri_by_stripping_scheme_and_package_name(tmp_path):
    urdf_dir = tmp_path / "urdf"
    urdf_dir.mkdir()
    meshes_dir = tmp_path / "meshes"
    meshes_dir.mkdir()
    mesh_file = meshes_dir / "link1.stl"
    mesh_file.write_bytes(b"stl-data")

    resolve = build_mesh_resolver(root=tmp_path, urdf_file_dir=urdf_dir)
    result = resolve("package://some_pkg/meshes/link1.stl")
    assert result == mesh_file.resolve()


def test_resolve_falls_back_to_basename_search_anywhere_under_root(tmp_path):
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)
    mesh_file = deep / "gripper.obj"
    mesh_file.write_bytes(b"obj-data")

    resolve = build_mesh_resolver(root=tmp_path, urdf_file_dir=tmp_path / "urdf")
    result = resolve("package://unrelated_pkg/totally/different/path/gripper.obj")
    assert result == mesh_file


def test_resolve_falls_back_to_extra_roots_when_root_has_no_match(tmp_path):
    # The graphical "Locate Missing Meshes..." dialog (app.py's own
    # add_mesh_search_folder()) rebuilds the resolver with an
    # operator-picked extra folder once the automatic root search above
    # comes up empty - e.g. the referenced ROS package lives in a
    # separate checkout the original fetch/open never saw.
    root = tmp_path / "fetched_repo"
    root.mkdir()
    sibling_pkg = tmp_path / "sibling_pkg"
    (sibling_pkg / "meshes").mkdir(parents=True)
    mesh_file = sibling_pkg / "meshes" / "gripper.stl"
    mesh_file.write_bytes(b"stl-data")

    resolve = build_mesh_resolver(root=root, urdf_file_dir=root, extra_roots=[sibling_pkg])
    result = resolve("package://sibling_pkg/meshes/gripper.stl")
    assert result == mesh_file


def test_resolve_prefers_root_over_extra_roots_when_both_match(tmp_path):
    root = tmp_path / "fetched_repo"
    root.mkdir()
    root_mesh = root / "gripper.stl"
    root_mesh.write_bytes(b"root-data")
    extra_root = tmp_path / "extra"
    extra_root.mkdir()
    (extra_root / "gripper.stl").write_bytes(b"extra-data")

    resolve = build_mesh_resolver(root=root, urdf_file_dir=root, extra_roots=[extra_root])
    result = resolve("package://some_pkg/gripper.stl")
    assert result == root_mesh


def test_resolve_returns_none_when_extra_roots_also_have_no_match(tmp_path):
    root = tmp_path / "fetched_repo"
    root.mkdir()
    extra_root = tmp_path / "extra"
    extra_root.mkdir()

    resolve = build_mesh_resolver(root=root, urdf_file_dir=root, extra_roots=[extra_root])
    assert resolve("package://some_pkg/nonexistent.stl") is None


def test_resolve_returns_none_for_empty_filename(tmp_path):
    resolve = build_mesh_resolver(root=tmp_path, urdf_file_dir=tmp_path)
    assert resolve("") is None


def test_resolve_returns_none_when_nothing_matches(tmp_path):
    resolve = build_mesh_resolver(root=tmp_path, urdf_file_dir=tmp_path)
    assert resolve("nonexistent.stl") is None


def test_bare_relative_path_that_is_broken_does_not_pick_up_an_unrelated_same_named_file_regression_for_prior_audit_fix(tmp_path):
    # BUG (found in audit) regression: a bare relative path with no
    # package:// scheme (e.g. a moved/broken "sub/mesh.stl" reference)
    # must NOT probe urdf_file_dir/<basename> directly - only a real
    # package:// URI is allowed to drop its leading path segment. Before
    # the fix, an unrelated file of the same basename sitting directly in
    # urdf_file_dir would be silently returned instead of falling through
    # to the honest basename-wide search (or None).
    urdf_dir = tmp_path / "urdf"
    urdf_dir.mkdir()
    # An UNRELATED file that happens to share a basename with the broken
    # reference, sitting directly in urdf_file_dir - must NOT be picked.
    wrong_file = urdf_dir / "mesh.stl"
    wrong_file.write_bytes(b"wrong file - must not be matched")
    # The REAL file lives elsewhere, findable only via the honest
    # basename-wide fallback search.
    real_dir = tmp_path / "actual_meshes"
    real_dir.mkdir()
    real_file = real_dir / "mesh.stl"
    real_file.write_bytes(b"the real mesh")

    resolve = build_mesh_resolver(root=tmp_path, urdf_file_dir=urdf_dir)
    # "sub/mesh.stl" has no "://" - had_scheme is False - so the
    # package-name-stripping probe (which would have hit urdf_dir/mesh.stl,
    # i.e. wrong_file) must be skipped entirely.
    result = resolve("sub/mesh.stl")
    assert result == real_file


def test_multiple_files_sharing_a_basename_returns_the_first_index_entry(tmp_path):
    dir_a = tmp_path / "a"
    dir_a.mkdir()
    dir_b = tmp_path / "b"
    dir_b.mkdir()
    (dir_a / "dup.stl").write_bytes(b"1")
    (dir_b / "dup.stl").write_bytes(b"2")

    resolve = build_mesh_resolver(root=tmp_path, urdf_file_dir=tmp_path / "urdf")
    result = resolve("package://pkg/meshes/dup.stl")
    assert result is not None
    assert result.name == "dup.stl"


def test_resolver_index_is_case_insensitive_on_basename(tmp_path):
    meshes_dir = tmp_path / "meshes"
    meshes_dir.mkdir()
    (meshes_dir / "Link1.STL").write_bytes(b"data")

    resolve = build_mesh_resolver(root=tmp_path, urdf_file_dir=tmp_path / "urdf")
    result = resolve("package://pkg/link1.stl")
    assert result is not None
    assert result.name == "Link1.STL"
