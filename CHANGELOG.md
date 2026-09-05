# Changelog

All notable changes to HYDRA-UMC EDITOR-URDF are documented in this file.

Versioning follows the ecosystem-wide `MAJOR.MINOR.PATCH` scheme with an
"odometer" bump rule applied automatically on every real packaged build (see
`bump_version.py`, invoked from `build_exe.bat`/`build_exe.sh`): `PATCH`
goes up by 1 per build; once `PATCH` would exceed 9 it resets to 0 and
`MINOR` goes up by 1 instead (e.g. `0.0.9` -> `0.1.0`). `MAJOR` is only ever
bumped by hand, as a deliberate decision.

## [Unreleased] - Chinese and Japanese added to the language menu

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
- Doesn't bump `hydra_editor_urdf.__version__` on its own - this
  project's own versioning convention only advances it on a real
  `build_exe.bat`/`build_exe.sh` packaged build.

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
- Added `bump_version.py` (odometer-style PATCH/MINOR bump) and wired it
  into `build_exe.bat`/`build_exe.sh` as a step that runs automatically
  right before every real PyInstaller build.
- The About dialog (Help menu) now shows the running version.
- Added `CHANGELOG.md` (this file).

## Unreleased history (pre-0.0.0, summarized from internal audit notes)

The sections below summarize work completed before version numbering
existed, drawn from the project's internal audit log.

### Project commissioned

Full specification received for a graphical URDF (3D object + kinematics)
creator/editor for HYDRA-UMC-STUDIO's model catalog. Design direction set:
reuse HYDRA-UMC-SUITE's proven pattern (Python + PySide6/Qt6, dockable
Photoshop-style workspace, custom OpenGL viewport) rather than evaluating
a new framework.

### Application built

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

### Documentation and verification

README.md written from scratch (Overview, design-decision rationale,
repository structure, development/build instructions). `python -m
py_compile` and real imports (via HYDRA-UMC-SUITE's venv, same pinned
PySide6/PyOpenGL/numpy-stl versions) confirmed clean across the full
package, including the UI/render/mesh chain.

### Line-by-line audit, round 1

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

### README translated to 5 languages

`README_spa.md`, `README_ita.md`, `README_fra.md`, `README_deu.md` added
as faithful section-by-section translations, matching the convention
already used in URTC-FLASHER/URTC-TESTER. License section expanded to
cover both GPL-3.0 (code) and CC BY-SA 4.0 (documentation).

### Line-by-line audit, round 2

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
