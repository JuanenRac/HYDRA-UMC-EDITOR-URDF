# Changelog

All notable changes to this project are documented here.

## [Unreleased]

## [0.1.8] - A physical check of the model with 25 rules, a command line for it and a panel of its own, all off by default

- **A physical check of the model, off by default:** with `physical_check` true in `hydra_editor_urdf_config.json`, the DOF screen lists, as warnings that never change feasibility or what is saved, what is not physically coherent: more than one root, a cycle, a link no joint uses or no joint reaches, a link with two parents, a joint that names a missing link, duplicate names; a mass that is not above 0, an inertia tensor that is not finite, not positive definite or whose principal moments break the triangle inequality (Ixx + Iyy >= Izz and the permutations); a limit with lower above upper, effort or velocity not above 0, no limit on a revolute or prismatic joint, lower and upper on a continuous one; an axis that is zero or not of length 1; a mesh that does not exist or whose scale is not positive, reasonable and equal on the three axes; lengths, angles and masses that look like millimetres, degrees or grams. Each warning gives the rule, the element, the value, the limit and a suggested correction, which is never applied. The bounds of the unit and scale rules are `physical_max_length_m`, `physical_max_angle_rad`, `physical_max_mass_kg`, `physical_mesh_scale_min` and `physical_mesh_scale_max` in the same file. Texts in the eight languages; see `docs/PHYSICAL_CHECK.md`.
- **A command line:** `main.py --cli physical-check FILE.urdf [--json] [--mesh-root DIR]` runs the same check without a window or Qt, prints one line per warning (or a JSON list), never writes the model, and exits with 0 (nothing found), 1 (warnings) or 2 (the file could not be read). A file with duplicate names, which the reader refuses, is reported as a warning of the check.
- **A panel of its own for the physical check, shown only with the switch on:** with `physical_check` true, both interfaces (the classic dockable window and the `--qtquick` deck) get a "Physical validation" panel, tabbed with the DOF screen, that lists every warning with its severity (error, warning or hint, decided by the rule), rule, element, value, limit and suggested correction. It can be filtered by severity, by rule and by a text in the element name, sorted by severity, rule or element, shows a counter (shown of total, and how many of each severity), has a "Check again" button (it reads the model and the settings again) and copies or exports the rows shown as JSON. It is read-only: the suggestion is text and there is no button that applies it. With the switch off (the default) the panel, its dock, its menu entry, its navigation button and the QML tab do not exist, and the DOF screen and the rest of the window are exactly as before. Texts in the eight languages (European Portuguese); see `docs/PHYSICAL_CHECK.md`.
- 31 new tests (569 in all), among them the first that open the classic window, the panel and the QML deck offscreen.

## [0.1.7] - Xacro expansion, a self-collision warning, a report of the mesh licenses and a Y-up export, all off by default

- **A xacro file can be expanded with the `xacro` tool of the machine, off by default:** with `xacro_expand` set to true in `hydra_editor_urdf_config.json` and a `xacro` program (or `ros2 run xacro xacro`) on the PATH, opening a xacro file runs that tool (no shell, a time limit of `xacro_timeout_seconds`, 60 by default) and reads the plain URDF it prints; a tool that is missing, fails, times out or prints no `<robot>` is reported as a load failure. With the switch off, a xacro file is refused with the same explanation as before. Nothing of xacro is bundled.
- **Links that may collide are listed as warnings, off by default:** with `self_collision_check` true, the DOF screen lists the pairs of links (not joined by a joint) whose boxes overlap in the home pose or while one joint at a time is jogged over its whole range (`self_collision_steps`, 9 by default; `self_collision_tolerance_m`, 0.001 by default). Each link is boxed with an axis-aligned box that contains its collision geometry (its visual geometry when it has none), so a near miss can be reported but an overlap is not missed. A warning never changes whether the robot is feasible or what is saved.
- **The license files beside the meshes are reported, off by default:** with `license_check` true, the folders from each mesh up to the opened folder are searched for LICENSE, COPYING, NOTICE and ATTRIBUTION files; meshes without any, and licenses that carry conditions (the Creative Commons non-commercial and share-alike ones, the GPL and LGPL), are listed as warnings, and an ATTRIBUTION text can be built from what was found (`EditorController.attribution_text`). This reports what is there; it does not decide what a license allows.
- **The model can be exported for a Y-up scene:** the Export window has a box, off by default and off again for every robot that is loaded, that writes the model with a new root link that turns the world a quarter turn about X, so a point (x, y, z) is (x, z, -y) as in a Three.js scene; `y_up_scale` in the configuration file (1 by default) scales every length. The robot in memory and the saved check are not changed. Texts in the eight languages.
- 21 new tests (399 in all).

## [0.1.6] - The unit of a mesh declared by its model, write-back of the elements the model has no field for and the universal README

- **The unit of a mesh is declared by its model:** a `metadata.json` in the folder of the meshes (or up to three folders above) with `"unit": "mm"` or `"m"` decides the scale. Only when no unit is declared is the size of the mesh used to guess it, as before, and the span above which a mesh is taken for millimeters is `mesh_millimeter_span` in `hydra_editor_urdf_config.json` (5 by default; 0 turns the guess off). A mesh that its URDF already scales (`<mesh scale=...>` other than 1 1 1) is no longer guessed a second time, so a model with `scale="0.001 0.001 0.001"` is not made 1000 times smaller again.

- **The elements the model has no field for can be written back:** the reader now keeps, as text, the `<transmission>`, `<gazebo>` and other children of `<robot>` and the `<dynamics>`, `<safety_controller>`, `<calibration>` and `<mimic>` (with its multiplier and offset) of each joint, and `robot_to_urdf_string(robot, keep_unsupported=True)` writes them back, leaving out those that name a joint or link that was deleted. The default is unchanged (they are left out, and the screen that lists them still says so). The Export button now opens a window that says how many such elements the source file has and has a switch, off by default and off again for every robot that is loaded, to write them back; it is in the eight languages.
- **README in the universal layout:** the README and its seven translations follow the layout that the four families share (22 sections in a fixed order), with an architecture picture and a repository-structure picture drawn from `docs/architecture.json` and `docs/structure.json`; the CI validator checks both pictures and the file tree.

- **The layout of the README is checked in the CI:** the validator runs `tools/universal_readme_check.py` and lists, as a warning, what differs from the universal layout of the README.

## [0.1.5] - A joint that follows another (`<mimic>`) is not a degree of freedom and a joint whose range is one point is a warning

### Firmware and protocol

- **A joint whose range is one point is a warning.** A REVOLUTE or PRISMATIC joint with `lower` equal to `upper` is a valid URDF that can never move; the DOF screen now lists it after the reasons (`DofReport.warnings`, never counted against feasibility) instead of saying nothing, in the eight languages.

### Programs and windows

- **The elements the editor does not keep are reported when the file is read.** The DOF screen lists, as warnings, every `<transmission>`, `<gazebo>`, `<dynamics>`, `<safety_controller>`, `<mimic>`, texture and other element that the model has no place for and that saving or sending the model therefore leaves out (`Robot.dropped_elements`, by element and count), instead of losing them silently. Passing them through to the written file is not done.
- **The sliders start where the viewport is posed, and a continuous joint can be jogged.** A continuous joint whose `<limit>` carries only effort and velocity got a slider a millionth of a radian wide; it now offers a full turn each way (`kinematics.jog_range`, shared by the classic and the QML interface), and every slider starts at `default_joint_values`.

### Tests, builds and checks

- New tests for the client against a local server that keeps the contract (token on every call, name collision and overwrite, a round trip with its meshes, an expired token, a hostile download), for the warning and for the mesh cache (355 in all).
- **A joint axis is a direction everywhere, not only at export**: the parser reads a non-unit `<axis>` as the unit vector it points along (as URDF readers do), so the preview, the kinematics and the writer agree; an explicit zero-length axis on a revolute, continuous, prismatic or planar joint is refused with the joint named (it used to be accepted and turn the joint into the identity in the preview, and was only caught when saving), and on a fixed or floating joint, which does not use it, it is ignored. The writer writes the axis as a direction (a scaled x axis is the default and is omitted); an axis with no direction in memory is written as it is for the save check to refuse. 6 new tests (336 in all).
- Building no longer changes the version; raising it is the explicit `bump` command (`python tools/hydra_project_tool.py bump`). The build scripts only report the version they built, and CI fails if a build script runs a bump.
- The build and run scripts use the Python of the `.venv` directly instead of an activate script, and create the venv with the `py` launcher when there is one; CI fails if a script activates a venv.
- Added `tools/hydra_project_tool.py`: the same `validate`, `test`, `version`, `status` and `bump` commands in every repository. The checks run with `HYDRA_UMC_CI=1` and fail if the version changes; only `bump` changes it.

### Other changes

- **A joint that follows another (`<mimic>`) is not a degree of freedom.** It used to be counted as one, so a 5-DOF arm with a mimic joint looked like a feasible 6-DOF one; it is reported as a follower and still needs its own `<limit>`.
- **Meshes are read from disk once.** The viewport read every mesh of the robot again at each rebuild (a scale or type edit). Loaded meshes are kept by path, modification time and size, up to 256 MiB, with read-only arrays so the shared original cannot be changed by mistake; a mesh that could not be read is never kept.
- **The model client sends its token on every call once signed in,** also on the model list, which a server that asks for a sign-in on the host information (`HYDRA_UMC_INFO_AUTH=required`) refuses otherwise.
- The banner follows the animated style of the ecosystem banners, with the name, the kind and the technologies of the project.

## [0.1.4] - Hostile files and server answers are reported, not raised

- **URDF files:** a URDF that is not valid UTF-8 (a Latin-1 comment is enough) raised an unhandled `UnicodeDecodeError` while loading; it is now a readable parse error naming the file.
- **Meshes:** an STL whose header promises billions of triangles, or whose ASCII facet is malformed, raised an `AssertionError` that escaped the mesh loader; both are now a malformed-mesh message and the link is skipped. A binary STL cut short is reported instead of being shown with pieces missing.
- **Model server:** a login, list, push or download answer that is not a JSON object (a proxy page, `null`, a list), a token or slug that is not text, a download with a mesh list or mesh data that is not valid, or a GitHub answer that is not JSON, is now a readable error. A downloaded model whose name is not a plain folder name (`..`, a path) is refused instead of being written outside the chosen folder, and a bad download no longer leaves a half-written model behind.
- 116 new tests (330 in all, 54 % of `render/mesh.py` and 99 % of `server/client.py` covered): URDF and mesh parsing of broken input, the model-server client against a local server, the controller's signals and export backups.

## [0.1.3]

- Build version synchronized with `hydra-umc.project.json` and the repository-native version source.
- The licence is written as GPL-3.0-or-later in every header and in the package metadata.

## [0.1.2] - Mesh paths stay inside the repository, safer push and export

- **Mesh paths can no longer leave the repository:** a `<mesh filename>` with `..` segments, an absolute path or a `file://` URI used to resolve to any readable file on the operator's computer, and "Push" would read it and upload it to the server. The resolver now only returns `.stl`, `.obj` or `.dae` files inside the opened folder, the URDF folder or a folder added with "Locate Missing Meshes", and the upload skips anything else.
- **Pushing runs the same checks as exporting:** a non-finite limit, inertia or scale typed in the editor could reach the server. "Push" now refuses a robot that fails the pre-save check, a non-finite joint limit makes the robot infeasible, and the visual deck turns a decimal comma into a point and ignores values that are not numbers.
- **No more pre-filled credentials in the visual deck:** the user and password fields no longer start as `admin` / `admin`; they show a placeholder like the classic panel.
- **A cyclic joint chain no longer crashes the link tree** (classic and visual deck).
- **Broken meshes are skipped instead of stopping the viewer:** empty or truncated STL files, OBJ files without faces, faces that point at missing vertices and non-finite vertices are reported as "mesh could not be loaded".
- **Safer export:** the file is written to a temporary file and replaced atomically, and the `.bak` copy keeps the first original instead of being overwritten by the next export.
- **XML hardening:** a URDF that declares a DOCTYPE or entities is refused whatever expat version is installed.
- **Cleanups:** the radians unit key is renamed (`UNIT_RADIANS`), unused imports are removed, the new "not a valid number" message exists in all 8 languages, and the README (all languages) documents the mesh confinement, the millimetre guard and the tags that are not kept on export (214 tests).

## [0.1.1] - Deterministic mesh choice; the interface speaks Portuguese

- **Mesh references that match several files:** when a `<mesh filename>` basename is found in more than one place, the file whose path shares the most trailing components with the reference now wins, a reference that names a folder that did not resolve no longer picks the file lying beside the URDF, and ties are broken by path. It used to take whichever file the directory walk listed first, so the same project loaded a different mesh on another file system (`test_scan.py` failed on one of them).
- **Portuguese interface:** `language/portuguese.lng` (103 keys, the same placeholders as English) and a `Português` entry in the language menu. A README_por.md joins the other seven.
- 3 new tests (202 in all): the closest path wins whatever the walk order, ties go by path, and a folder reference that missed does not pick the file beside the URDF.

## [0.1.0] - CI test fix

- The pre-save export tests that need the editor controller now skip when PySide6 is not installed, so the plain Python test job stays green.

## [0.0.9] - Export refuses an unsound robot

- `urdf/save_check.py`: before anything is written, export checks every joint limit (finite,
  lower below upper, non-negative effort and velocity, present for revolute and prismatic
  joints), that a movable joint's axis is a real direction, that geometry has positive
  dimensions and non-zero mesh scale, and (when a mesh folder is given) that each mesh file
  exists. A failing robot raises `UrdfSaveError` listing every problem, nothing is written and
  the existing file is left alone. The UI already shows the message. Nine new tests.

## [0.0.8] - A graphical fallback when package:// mesh resolution can't find a file

- **Locate Missing Meshes... dialog:** `source/scan.py`'s heuristic
  `package://` resolution (relative path, then basename search under
  the fetched/opened folder) already handles the common case, but had
  no fallback when a referenced mesh genuinely isn't anywhere under the
  original folder - e.g. the URDF references a sibling ROS package that
  lives in a separate checkout. The viewport now shows a "Locate Missing
  Meshes..." button whenever a mesh actually fails to resolve; picking a
  folder there rebuilds the resolver with that folder as an extra
  basename-search root (`build_mesh_resolver`'s new `extra_roots`
  parameter) and retries every geometry, including ones that previously
  failed, without needing to re-open the URDF. New `VIEWPORT_LOCATE_MESHES_
  BUTTON`/`VIEWPORT_LOCATE_MESHES_DIALOG_TITLE` keys across all 7
  languages.

## [0.0.7] - insecure defaults, an invisible ghost link, non-finite geometry, and denied capabilities

- the Upload panel's username/password fields were pre-filled
  with the literal text `"admin"`/`"admin"` - a real credential, not a
  placeholder, suggesting it as legitimate to actually connect with.
  Both now start empty with neutral placeholder text (added to all 7
  languages).
- a joint whose own `<parent>`/`<child>` names a link with no
  matching `<link>` element at all used to get a "viable" DOF verdict -
  `root_link_name()`/`_reachable_from()` only ever walk names already in
  `robot.links`, so a fictitious name was silently accepted into the
  "reachable" set instead of being flagged. `validate()` now checks every
  joint's parent/child against the real link set first.
- the parser's `float(...)` calls happily accepted `"nan"`/
  `"inf"`/`"-inf"` (valid per Python's own `float()`) for any numeric URDF
  field - origin xyz/rpy, geometry dimensions, inertia, joint limits -
  baking non-finite, physically meaningless values into a model that
  then parsed "successfully". A new shared `_parse_float()`/`_parse_floats()`
  now reject any non-finite result (and any non-numeric text, with a
  clearer message) with the same `UrdfParseError` every other malformed
  input in this parser already raises. Also added: an inverted joint
  `<limit>` (lower > upper) is now flagged as invalid.
- **Docs:** `INTEGRATION_CONTRACT.md` claimed "no network endpoint,
  remote loading contract... is provided", and `ARCHITECTURE.md` claimed
  the editor "does not... upload a URDF" - both false: `source/
  github_fetcher.py` (real, read-only GitHub zipball fetch) and `server/
  client.py`'s `StudioClient` (real authenticated push/pull to
  HYDRA-UMC-SERVER) both exist and are exercised from the Upload panel.
  Reworded both documents to describe the real boundary (explicit-action
  network paths, no hardware/motion authority ever) instead of denying
  capabilities that exist. `BUILD_AND_RUN.md` also gained a mention of the
  real, working standalone `--qtquick` mode next to its existing account
  of the abandoned embedded-widget attempt, which previously left a
  reader unaware the standalone mode exists at all.
- 185 tests passing (8 new regressions), up from 177.

## [0.0.6] - Honesty check section in every README

Added a "Honesty check" paragraph right after the intro badges in
`README.md` and all 6 translated READMEs, naming the real, tested
pure-logic modules (`urdf/parser.py`, `urdf/writer.py`, `urdf/dof.py`,
`render/kinematics.py`, `inertia_calc.py`, `source/scan.py`,
`source/github_fetcher.py`, `source/local_folder.py`, `models.py`,
`gallery.py`, `i18n.py`) and the real test count (177 passing). States
plainly that the Qt/OpenGL layer (`render/viewport.py`, `render/mesh.py`,
every `ui/*` panel, `server/client.py`'s `StudioClient`) has no
automated test coverage at all and is only verified by hand, and that
`test_github_fetcher.py` mocks every network call. Documents the real,
current state of what's implemented vs. planned; no behavior changed.

## [0.0.5] - removed private-document references

- 
  removed the 2 remaining references to an internal
  planning file with no public equivalent (`app.py`'s crash-safety `.bak`
  comment, `urdf/dof.py`'s negative-mass-link comment) - the reasoning
  each one supported is now stated in place instead of pointing at a
  document outside this repository.

## [0.0.4] - Real automated test suite

- Found on code review: this app's own
  pure logic (`urdf/parser.py`/`urdf/writer.py`, `urdf/dof.py`,
  `render/kinematics.py`, `inertia_calc.py`, `models.py`,
  `source/scan.py`/`source/local_folder.py`/`source/github_fetcher.py`,
  `i18n.py`, `gallery.py`) had zero automated test coverage.
- **`tests/`** (new) - 177 real tests across 11 test modules, none of
  which import PySide6/PyOpenGL: URDF parse/export (including
  parse -> write -> parse round-trips for every geometry/material/
  inertial/limit combination), DOF feasibility (every boundary and
  structural failure mode: no/multiple root links, disconnected
  sub-graphs, multi-parent links, negative mass), forward kinematics
  (including explicit regressions for the real-cycle-hangs-forever bug
  and the diamond-reconvergence determinism already fixed in an earlier review), closed-form inertia tensors checked against independently
  computed textbook values, the mesh-reference resolver (including an
  explicit regression for the `had_scheme` gating bug already fixed in
  an earlier review), `parse_github_url()`'s every real-world URL form,
  `resolve_default_branch()`/`fetch_github_repo()` with GitHub's network
  calls mocked (never real), and `i18n.py`'s config/language file I/O
  against real temp files (never the operator's own real config).
- **`requirements-dev.txt`** (new) - `numpy` + `pytest` only, NOT the
  full `requirements.txt`: every test file above is pure logic with no
  Qt import anywhere in its own dependency chain, so CI installs a short
  list instead of the full GUI dependency set and the suite runs with no
  display or Qt platform plugin needed.
- **`.github/workflows/ci.yml`** - new step, `python -m pip install -r
  requirements-dev.txt` then `python -m pytest tests/ -q`, gated on
  `requirements-dev.txt` existing (this ecosystem's own established
  pattern for a pure-Python project's real test suite).
- Verified for real: `python -m pytest tests/ -q` - 177/177 passing.

- **Fixed real overlapping-text layout bugs in the `--qtquick` deck.**
  Found from a direct user report of wide elements sitting on top of
  other controls, hiding their functions. Root cause, confirmed with a
  real on-screen check (not a theory): a `RowLayout` doesn't reserve
  real height for a wrapped `Text` sibling sharing its row with another
  control - the row sizes itself off that Text's un-wrapped single-line
  height, and the wrapped second line spills down over whatever comes
  next. Hit twice in the Upload panel: the "Models already on this
  server" label spilled over the Refresh button/models list below it,
  and a `CheckBox` with its own custom `contentItem`/`indicator` (itself
  a real, already-documented gotcha - it misplaces the indicator box)
  made the same mistake with its own wrapped label. Both replaced with
  a plain `CheckBox` plus a separate label `Text` on its own full-width
  row - the proven pattern HYDRA-UMC-SUITE's own short-label checkboxes
  already use, extended here to survive a genuinely long, wrapping
  label too. Separately, the 3D Viewport panel's own "unavailable"
  message used `anchors.centerIn` plus an arithmetic
  `width: parent.width * 0.8` that froze at `0.8px` wide (confirmed by
  walking the real live QML object tree, not guessed) and never
  re-evaluated afterward, wrapping the message one word per line in a
  sliver a few pixels wide - switched to `anchors.fill` + margins,
  which doesn't have that failure mode.
- **New: real Qt Quick "command deck" (`python main.py --qtquick`), the
  same standalone-shell pattern HYDRA-UMC-OS-REBUILDER/HYDRA-UMC-UPDATER/
  URTC-TESTER/URTC-FLASHER/HYDRA-UMC-SUITE already use.** The bullet just
  below this one documents this app's OWN earlier, different attempt -
  embedding a `QQuickWidget` inside the classic `QToolBar`, which painted
  solid black and was reverted. This is not that: a genuinely standalone
  QML `ApplicationWindow` (`qt_editor_urdf.py` + `assets/qml/
  EditorDeck.qml`), never embedded in the classic `QMainWindow`, so the
  compositing bug that sank the embed attempt doesn't apply here at all.
  Faithfully reproduces the classic dockable workspace's own real spatial
  arrangement (Source+DOF tabbed left, Viewport+Properties side by side,
  Upload docked across the bottom - see `ui/main_window.py`'s own
  `_build_panels()`) and every one of its 5 panels' own real features:
  GitHub/gallery/local-folder loading with found-URDF picking, live DOF
  validation, an orbit/pan/zoom 3D preview with a clickable link tree and
  per-joint jog sliders, color/scale/joint-limit/mass-and-inertia editing,
  and the STUDIO server connect/push/pull round-trip - reusing
  `EditorController`, the background fetch/server-call threads, and every
  real i18n key unchanged, not a second implementation of any of it.
  `render/viewport.py`'s own `UrdfViewport(QOpenGLWidget)` was split into
  a context-agnostic `UrdfGLRenderer` plus a thin `UrdfViewport` wrapper
  (identical real behavior) and a new `OffscreenUrdfRenderer` - a genuine
  separate `QOpenGLContext`/`QOffscreenSurface`/FBO, deliberately not Qt
  Quick's own `QQuickFramebufferObject` - so the deck's 3D preview reuses
  the exact same real rendering code the classic viewport already uses,
  fed into QML through a `QQuickImageProvider`, the same real split
  HYDRA-UMC-SUITE's own `RobotGLRenderer`/`OffscreenRobotRenderer` already
  proved (including that class's own real reentrancy-counter fix for a
  nested make/done-current segfault, reused here rather than
  re-discovered). Verified end-to-end with real PySide6 instantiation (no
  display needed for the logic/render path): loading a real test URDF
  through the bridge produced the correct DOF verdict, link tree, joint
  ranges, and a real rendered frame (saved to a PNG and visually confirmed
  correct, including a visible joint rotation after a jog); color/scale/
  joint/inertia edits and URDF export all round-tripped correctly. The
  classic `QMainWindow` app was re-instantiated after the same refactor to
  confirm zero regressions. Adds no new user-facing strings beyond 3 short
  deck-only chrome labels (tagline, Export button, empty-viewport message),
  translated in all 7 language files alongside the existing 82 keys this
  deck otherwise reuses unchanged.
- **Fixed: command deck rendered as a blank black bar; real About dialog
  added.** Real per-project screenshots (not just code reading) confirmed
  the Qt Quick/QML command deck described in the bullets below painted
  solid black with zero content visible, no console error - a
  `QQuickWidget` embedded in a `QToolBar` inside this `QMainWindow`'s real
  `QDockWidget` layout never got a correctly composited native surface,
  the exact same bug HYDRA-UMC-SUITE's own deck had. Reverted the deck to
  plain `QToolBar`/`QLabel`/`QToolButton` widgets - verified via a fresh
  screenshot: logo, title, navigation buttons and the model/status chips
  all render correctly now. Separately, the single-line `QMessageBox`
  About dialog is now a real `AboutDialog` matching
  HYDRA-UMC-STUDIO's own `About.tsx` (animated logo, colored HYDRA-UM-C
  wordmark, tagline, description, Version/Author/Email/License rows) -
  see `ui/about_dialog.py`. The now-orphaned `qtquick_deck.py`/
  `CommandDeck.qml` were moved out of the repo rather than deleted.
- The embedded Qt Quick deck now shows live validated DOF, link and joint
  counts alongside the HYDRA-UMC-STUDIO feasibility verdict. It receives the
  same model and tree-change signals used by the established dock panels, so
  a property edit cannot leave the deck displaying stale validation data.
- The Qt Quick command deck now reads its navigation and Export labels from
  the established editor language files, rather than maintaining a second,
  English-only label list in QML.
- The Qt Quick command deck now keeps Export disabled until a real URDF model
  has been loaded, matching the actual availability of the established export
  action instead of showing an avoidable no-model dialog.
- The dock workspace now has a real QML/Qt Quick command deck, embedded through
  QQuickWidget on the same renderer used by HYDRA-UMC-UPDATER and
  HYDRA-UMC-SUITE. Its Source, DOF, Viewport, Properties and Upload actions
  raise the existing live docks; Export and About forward to the existing
  actions. No URDF parser, editor, OpenGL viewport or server-upload path was
  duplicated.
- The deck reports real controller status and the name of each loaded robot.
  The bundled HYDRA-UMC SVG is rendered by Qt Quick as the visual identity;
  native window icons remain platform-static.
- PyInstaller build scripts include the Qt Quick/QML runtime needed by the
  embedded deck.

- New `language/chinese.lng` (简体中文) and `language/japanese.lng` (日本語) -
  full translation of all 82 keys, matching the coverage of the existing
  english/spanish/italian/french/german files. Added to `i18n.py`'s own
  `AVAILABLE_LANGUAGES` list, which the Language menu builds from
  dynamically - no other UI code needed changing. Verified two ways: a
  real `load_language()` call for both new files confirmed all 82 keys
  present with zero gaps against `english.lng`, and a real offscreen Qt
  `MainWindow()` instantiation confirmed both new entries render correctly
  in the actual Language menu alongside the other 5.
- New `README_zho.md` / `README_jpn.md` documentation translations, plus
  the 5 existing README files' language selectors updated to link them.

## [0.0.3]

- **Fixed a real, silent drift in `assets/qss/industrial_dark.qss`.** `ui/theme.py`'s own header comment claims this file "reuses HYDRA-UMC-SUITE's own... verbatim", but real user feedback ("no tiene ese toque visual que tiene updater y os_rebuilder") plus a direct screenshot comparison found it had quietly diverged to an older, flatter palette (`#0b0e13`/`#11151c`/teal `#1e94a8`) missing the entire command-deck gradient/border-glow treatment SUITE's own copy has picked up since. Re-synced from SUITE's current file, keeping the one real selector SUITE no longer needs but this app still does (`QToolButton#commandDeckNav` - SUITE's own nav moved into a new left sidebar; this app's command deck still uses real nav buttons for Source/DOF Validation/3D Viewport/Properties/Export URDF), styled identically to `#commandDeckAbout`. Verified with a real before/after screenshot of the running app, not just a code diff.

## [0.0.2] - Gallery of verified robot description repositories

- New `gallery.py` - a short, hand-checked starter list of real, public,
  currently-active robot-description GitHub repos (ROS-Industrial's
  `universal_robot`, ROBOTIS' `open_manipulator`) - each verified to
  actually exist and contain real URDF/xacro content before being added,
  not assumed from memory. `SourcePanel` gets a new "Gallery" dropdown
  above the existing GitHub URL field - picking an entry only fills the
  URL and shows its description, it never fetches on its own; the
  operator still presses Fetch themselves, same as typing the URL by
  hand.
- Verified with real PySide6 widget instantiation (offscreen platform):
  dropdown item count matches the gallery data, selecting an entry fills
  the exact URL/description, resetting to the placeholder clears the
  description, and no network call fires just from selecting an entry.

## [0.0.1] - Automatic center-of-mass and inertia estimation

- New `inertia_calc.py` - real closed-form uniform-density inertia tensor
  formulas for Box/Cylinder/Sphere, plus a bounding-box approximation for
  Mesh geometry (this app has no per-triangle mesh integrator, and says
  so explicitly rather than presenting the mesh result as exact).
- `PropertiesPanel` gets a new "Mass & inertia" group: "Auto-calculate"
  fills mass/Ixx/Iyy/Izz from the selected link's own geometry (an
  operator-entered mass always wins over a density-based guess; with no
  mass entered yet it assumes a generic aluminum density, 2700 kg/m3,
  and says so in a note), "Apply" commits it to `Link.inertial` - same
  calculate-then-apply pattern the Scale/Joint groups already use.
- Verified end-to-end with real PySide6 widget instantiation (`QT_QPA_
  PLATFORM=offscreen`, no display needed): a Box(0.2, 0.3, 0.1) link with
  mass=5kg auto-calculated to the exact textbook Ixx/Iyy/Izz values,
  Apply wrote the correct `Inertial` onto the real model object, and the
  unresolvable-mesh path was confirmed to show a note instead of
  crashing. All 8 new translation keys resolve with real, correctly
  UTF-8-encoded text in all 5 languages (verified `'á' in string`, not
  just that a value exists). Version bumped via the real `bump_version.py`
  (0.0.0 -> 0.0.1); the full PyInstaller `.exe` packaging step itself was
  not re-run for this change (it repackages, it doesn't re-verify this
  logic - the widget-level test above is the real regression check here).

## [0.0.0]

Version numbering introduced for this project - it had no version number
at all before this point.

- Added `__version__` to `hydra_editor_urdf/__init__.py`, starting at
  `0.0.0`.
- Added `bump_version.py` (PATCH/MINOR bump) and wired it
  into `build_exe.bat`/`build_exe.sh` as a step that runs automatically
  right before every real PyInstaller build.
- The About dialog (Help menu) now shows the running version.
- Added `CHANGELOG.md` (this file).

## Earlier history

### Earlier history (before version numbering)

The sections below summarize work completed before version numbering
existed, drawn from the project's history.

Full specification received for a graphical URDF (3D object + kinematics)
creator/editor for HYDRA-UMC-STUDIO's model catalog. Design direction set:
reuse HYDRA-UMC-SUITE's proven pattern (Python + PySide6/Qt6, dockable
Photoshop-style workspace, custom OpenGL viewport) rather than evaluating
a new framework.

Full application implemented: `EditorController` (single owner of "what
URDF is loaded and where it came from"), a mutable dataclass model tree
for editing URDF interactively, honest unsupported-format errors for
xacro and `.dae`/COLLADA (no silent partial support), DOF validation
(3-6 DOF, matching what HYDRA-UMC-STUDIO's kinematics support), generic
forward kinematics for arbitrary imported URDFs (Rodrigues' rotation
formula, not a fixed robot registry), a real OpenGL 3.3 core-profile
viewport, mesh path resolution that handles `package://` URIs without a
live ROS workspace, git-free GitHub zipball fetching, and a client for
HYDRA-UMC-STUDIO's model submit/list/download API. Five-panel dockable UI
(Source/DOF/Viewport/Properties/Upload) with 5-language i18n. `tests/`
exists but was empty at this point.

README.md written from scratch (Overview, design-decision rationale,
repository structure, development/build instructions). `python -m
py_compile` and real imports (via HYDRA-UMC-SUITE's venv, same pinned
PySide6/PyOpenGL/numpy-stl versions) confirmed clean across the full
package, including the UI/render/mesh chain.

Every one of the 26 `.py` modules reviewed line by line, with real
end-to-end pipeline testing (a synthetic 6-DOF robot referencing real STL
meshes from HYDRA-UMC-STUDIO's catalog) and a field-by-field cross-check
of `server/client.py` against the real `HYDRA-UMC-STUDIO/server.ts`.

4 real bugs found and fixed:
1. `source/scan.py` mesh resolver applied its package-name-stripping step
   unconditionally, letting it resolve to an unrelated file outside the
   search root for a plain relative path with no `package://` scheme.
2. `source_panel.py`/`upload_panel.py` QThread instances could be
   overwritten mid-flight by an auto-triggered refresh, leaving Qt running
   a thread with no live Python reference - fixed by tracking live threads
   in a set until their `finished` signal fires.
3. `render/viewport.py` never freed GPU VAO/VBO buffers on rebuild - a
   real GPU memory leak on every live edit - fixed with explicit
   `glDeleteVertexArrays`/`glDeleteBuffers` before discarding old buffers.
4. `properties_panel.py` left a stale `<limit>` on a joint retyped away
   from revolute/prismatic, producing invalid exported URDF - fixed by
   clearing `joint.limit` on retype (except for `continuous`, where a
   `<limit>` is valid per spec).

`README_spa.md`, `README_ita.md`, `README_fra.md`, `README_deu.md` added
as faithful section-by-section translations, matching the convention
already used in URTC-FLASHER/URTC-TESTER. License section expanded to
cover both GPL-3.0 (code) and CC BY-SA 4.0 (documentation).

Remaining open items from the previous audit's "reasonable doubts"
resolved as 2 additional real bugs, each reproduced before and after the
fix:
1. `urdf/dof.py` `validate()` never detected a link declared as `<child>`
   of more than one `<joint>` (invalid per URDF spec) - fixed by adding
   `multi_parent_link_names` detection and a corresponding reason string.
2. `render/mesh.py` `load_obj()` mishandled a literal `0` vertex/normal
   index in a Wavefront `f` line (invalid per spec, 1-based), raising an
   unclear `IndexError` - fixed with an explicit check that raises a new
   `MalformedMeshFile` with a clear message instead.

No commits were made during any of this work - the owner makes their own
commits.
