# Source map

Every file of the repository with a line on what it does: the annotated tree that the README carried before it was reduced to the first level (the first level, in eight languages, is in the section Repository Structure of the README).

```text
├── main.py                        # Entry point - QApplication, theme, maximized start, F11 fullscreen toggle; --qtquick switches to the deck below
├── qt_editor_urdf.py               # Qt Quick front end - standalone `--qtquick` command deck, bridges the unchanged EditorController to QML
├── run.bat / run.sh                # Convenience wrapper - activates .venv if present, runs main.py, no auto-close
├── requirements.txt                # PySide6, PyOpenGL, numpy-stl, numpy (pinned)
├── requirements-dev.txt            # numpy + pytest only - what tests/ actually needs, no PySide6
├── build_exe.bat / build_exe.sh    # Windows/Linux standalone-executable build scripts (PyInstaller) - bumps the version first
├── build-test.bat / build-test.sh  # Non-versioning build/compile check
├── HYDRA-UMC_EDITOR-URDF.spec      # PyInstaller build spec used by build_exe.bat/.sh
├── bump_version.py                 # Version bump (run only by the explicit `bump` command)
├── bump_manifest_version.py        # Syncs hydra-umc.project.json's version to the native one (--sync)
├── CHANGELOG.md                    # Version history
├── README.md                       # This file
├── README_spa.md / README_ita.md / README_fra.md / README_deu.md / README_zho.md / README_jpn.md / README_por.md  # <- translations
├── LICENSE                         # GPL-3.0-or-later
├── assets/
│   ├── HYDRA_UMC_ICON.svg          # Animated HYDRA-UMC mark used by the toolbar command deck
│   ├── qss/industrial_dark.qss     # Reused verbatim from HYDRA-UMC-SUITE
│   └── qml/EditorDeck.qml          # Qt Quick UI for the `--qtquick` command deck
├── images/
│   └── HYDRA_UMC_BANNER.svg        # Media and diagrams
├── language/                       # english/spanish/italian/french/german/japanese/chinese/portuguese.lng - sits beside the exe, not bundled
├── hydra_editor_urdf/
│   ├── __init__.py                 # __version__ - single source of truth, read by the About dialog and rewritten by bump_version.py
│   ├── app.py                      # EditorController - single owner of "what's loaded", Qt signals every panel listens to
│   ├── models.py                   # In-house URDF object tree (Robot/Link/Joint/Visual/Geometry/Material/...)
│   ├── gallery.py                  # Starter list of real, verified public robot-description repositories
│   ├── inertia_calc.py             # Closed-form moment-of-inertia formulas for the primitive geometries
│   ├── cli.py                      # `--cli physical-check FILE.urdf [--json]` - no window, no Qt; exit 0 clean, 1 warnings, 2 error
│   ├── i18n.py                     # language/*.lng loader, config persistence - ported from HYDRA-UMC-SUITE's own i18n.py
│   ├── urdf/
│   │   ├── parser.py               # URDF XML -> models.py tree (ElementTree, xacro detected and rejected with a clear error)
│   │   ├── writer.py                # models.py tree -> URDF XML string (export + server upload payload)
│   │   ├── save_check.py            # Checks a robot before it is written out, so a model with an impossible or unusable part is refused with a list of what to fix
│   │   ├── physical_check.py       # Physical validation (tree, inertia, limits, axes, meshes, units) with a suggested fix per warning - off by default
│   │   └── dof.py                  # DOF counting, feasibility validation against STUDIO's 3-6 DOF ceiling
│   ├── render/
│   │   ├── mesh.py                 # STL/OBJ loading, box/cylinder/sphere primitive generation, mm-vs-m guard
│   │   ├── kinematics.py           # Generic forward kinematics over an arbitrary imported tree (Z-up, URDF's own convention)
│   │   └── viewport.py             # UrdfGLRenderer (GLSL 3.3 core shader, orbit camera, per-link GPU buffers) + the classic QOpenGLWidget wrapper + OffscreenUrdfRenderer for the `--qtquick` deck
│   ├── source/
│   │   ├── scan.py                 # Finds .urdf/.xacro files, builds the package://-aware mesh filename resolver
│   │   ├── github_fetcher.py       # GitHub zipball download + extraction (urllib + zipfile, no git dependency)
│   │   └── local_folder.py         # Local folder validation - the thin counterpart to github_fetcher.py
│   ├── server/
│   │   └── client.py               # StudioClient - login/list_models/push_model/pull_model against HYDRA-UMC-SERVER's server.ts (STUDIO's own backend before the two repos split)
│   └── ui/
│       ├── main_window.py          # QMainWindow - dockable workspace, menu bar, language switcher, status bar
│       ├── about_dialog.py         # Real About dialog, matching STUDIO's own About.tsx and SUITE's own about_dialog.py
│       ├── theme.py                 # Applies assets/qss/industrial_dark.qss
│       └── panels/
│           ├── source_panel.py     # GitHub URL / local folder input, found-URDF list
│           ├── dof_panel.py        # Feasibility verdict read-out
│           ├── viewport_panel.py   # 3D viewport host, link tree, jog sliders
│           ├── properties_panel.py # Recolor / rescale / retype-and-relimit editors
│           └── upload_panel.py     # Server connect/push/pull
├── docs/
│   ├── ARCHITECTURE.md
│   ├── BUILD_AND_RUN.md
│   ├── INTEGRATION_CONTRACT.md
│   └── PHYSICAL_CHECK.md
├── tests/                          # Real pytest suite (538 tests) - pure logic only, no PySide6 import anywhere here
│   ├── test_urdf_parser.py / test_urdf_writer.py  # URDF XML <-> models.py, including parse -> write -> parse round-trips
│   ├── test_physical_check.py / test_characterization_physical.py  # The physical check: random valid models give no warning, each mutation gives its rule; switch, command line and texts
│   ├── test_dof.py                 # Feasibility validation, DOF boundaries, root/orphan/disconnected/multi-parent detection
│   ├── test_kinematics.py          # Forward kinematics, including the fixed real-cycle-hangs-forever regression
│   ├── test_inertia_calc.py        # Closed-form box/cylinder/sphere tensors against independently-computed textbook values
│   ├── test_models.py              # Robot.root_link_name()/joints_by_parent()/movable_joints()
│   ├── test_scan.py                # find_urdf_files()/build_mesh_resolver(), including the fixed had_scheme regression
│   ├── test_local_folder.py / test_github_fetcher.py  # Source validation; GitHub network calls mocked, never real
│   ├── test_i18n.py                # Config/language file I/O against real temp files, never the operator's real config
│   ├── test_gallery.py             # Structural checks on the hand-curated GALLERY list
│   ├── test_client_server.py       # The client against a local server: a push with its meshes, the refusals and what the client does with them
│   ├── test_dropped_elements.py    # What the file has that the model has no place for is counted and reported
│   ├── test_edge_cases.py          # Files that are not UTF-8 or are binary, malformed text, cycles and broken STL meshes
│   ├── test_input_safety.py        # A mesh path that climbs out of the repository is not resolved; empty or broken STL files are errors, not crashes
│   └── test_save_check.py          # The check before saving (joint limits, masses and the other things it refuses)
├── tools/
│   ├── build_test.py               # Build/compile check without bumping version
│   ├── ci_validate.py              # Manifest/CHANGELOG/docs validation used by CI
│   ├── _doc_policy.py              # Documentation rules shared by the family (a copy of HYDRA-UMC-SDK's, kept in sync)
│   ├── _readme_parity.py           # Check that the eight READMEs share one structure (a copy of HYDRA-UMC-SDK's, kept in sync)
│   └── hydra_project_tool.py       # The same commands in every repository: validate, test, ci, version, status, bump
├── build/                           # PyInstaller's own intermediate work directory (gitignored)
├── dist/                            # Compiled standalone executable (build_exe.bat/.sh output, gitignored)
└── work/                            # Runtime scratch space for fetched GitHub repos and pulled server models (gitignored)
```

Note: an earlier attempt embedded a Qt Quick/QML command deck
(`assets/qml/CommandDeck.qml`, `ui/qtquick_deck.py`) directly inside this
`QMainWindow`'s real `QDockWidget` layout via `QQuickWidget` - that never
composited correctly (solid black, no console error) and was reverted;
the toolbar command deck above is plain `QToolBar`/`QLabel`/`QToolButton`
widgets. The real Qt Quick command deck this app has today
(`qt_editor_urdf.py` / `assets/qml/EditorDeck.qml`, listed above) is a
different, later, standalone `--qtquick` window instead - see
**🎛️ Theme** above and `CHANGELOG.md` for the full story.
