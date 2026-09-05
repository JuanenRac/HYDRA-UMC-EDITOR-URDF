<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-EDITOR-URDF banner" width="100%">
</p>
# 🦾 HYDRA-UMC EDITOR-URDF

<p align="center">
  🇺🇸 <b>English</b> |
  <a href="README_spa.md">🇪🇸 Español</a> |
  <a href="README_fra.md">🇫🇷 Français</a> |
  <a href="README_ita.md">🇮🇹 Italiano</a> |
  <a href="README_deu.md">🇩🇪 Deutsch</a> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <a href="README_jpn.md">🇯🇵 日本語</a>
</p>


<p align="left">
  <img src="https://img.shields.io/badge/License-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Language-Python%203.11-3776AB.svg" alt="Python">
  <img src="https://img.shields.io/badge/Framework-PySide6-41CD52.svg" alt="PySide6">
  <img src="https://img.shields.io/badge/Format-URDF-red.svg" alt="URDF">
</p>


### 🖌️ Graphical URDF Creator/Editor for the HYDRA-UMC-STUDIO Model Catalog

**Current version:** 0.0.2 (`MAJOR.MINOR.PATCH` - see the **Production Build** section below for how this number moves)

---

## 🎯 Overview

**HYDRA-UMC EDITOR-URDF** is the desktop tool that turns "porting a new robot into [HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)'s model catalog" from a manual, per-robot investigation into a repeatable, graphical workflow. Every real robot model in STUDIO's catalog got there the same way in the past: find a description repo on GitHub, figure out how its mesh references resolve, count the degrees of freedom in its kinematic chain, check whether STUDIO can actually drive that many, and hand-place the result into `public/models/`. This app automates that entire pass - pull the source files from a GitHub URL or an already-downloaded local folder, resolve every `<mesh filename="...">` reference (`package://` URIs included) against the real files on disk, validate the chain's DOF count against what STUDIO's kinematics supports today, edit color/scale/joint limits/joint type with a live 3D preview, and push the finished result straight to a running STUDIO server.

Built with **Python** and **PySide6/Qt6**, using the same architectural patterns already validated in this ecosystem's other desktop tool, [HYDRA-UMC SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE): a Photoshop/Fusion-360-style dockable workspace (`QDockWidget`), a hand-written OpenGL 3D viewport (`QOpenGLWidget` + GLSL 3.3 core-profile shaders, no `glBegin`/`glEnd` legacy path), and one central controller object that owns state and every UI panel listens to via Qt signals. Reusing that pattern here - rather than exploring a new UI/render stack for a sibling tool in the same ecosystem - is a deliberate choice, not an oversight.

**Honesty note, matching the rest of this ecosystem's own documentation convention:** this app does not expand [xacro](http://wiki.ros.org/xacro) macros, and does not load COLLADA (`.dae`) meshes. Both are named, explicit limitations (a clear error message, not a silent misparse or a missing link in the viewport) rather than a half-implemented attempt - see the **URDF Parsing** and **Mesh Loading** sections below for why real support for either would take significant additional work.

---

## 📥 Source Loading - GitHub or Local Folder

Two ways to point the app at a robot's source files, both landing in the same import path:

- **From a GitHub URL** - accepts a full `https://github.com/owner/repo` URL (with or without `/tree/<branch>`), an SSH-style `git@github.com:owner/repo.git`, or the bare `owner/repo` shorthand. Deliberately does **not** shell out to `git clone`, which would make a `git` install a hard runtime dependency on both Windows and Linux for something a plain HTTPS download already does: GitHub serves a zipball of any branch/tag/commit from `codeload.github.com` with no authentication needed for a public repo, so this uses the standard library's own `urllib.request` + `zipfile` and nothing else. Only public repos are supported - there's no token/credential handling, and a private repo's zipball 404s the same as a nonexistent one.
- **From a local folder** - for a repo already downloaded by hand, or a working copy the operator is actively editing outside this app.
- **From the Gallery** - a small "Gallery" dropdown above the GitHub URL field (`hydra_editor_urdf/gallery.py`) lists a short, hand-checked starter set of real, currently-active robot-description repos (ROS-Industrial's `universal_robot`, ROBOTIS' `open_manipulator`). Picking an entry only fills the URL field and shows its description - it never fetches on its own, the operator still presses Fetch, same as typing a URL by hand. A deliberately short, hand-picked list rather than an auto-scraped one: a gallery entry pointing at a dead or malicious repo would be worse than no gallery at all.

Either way, the app then recursively finds every `*.urdf`/`*.xacro` file under the chosen folder, lists all of them (a real robot description repo often ships more than one - a bare arm plus a "with gripper" variant is a common pairing), and auto-picks the largest by file size as a reasonable default for "the main one" - switching to a different candidate afterward is one double-click in the Source panel, not a re-fetch.

**Mesh reference resolution** is the actual unglamorous work every past manual robot-porting session in this ecosystem did by hand: a URDF's `<mesh filename="package://some_pkg/meshes/link1.stl"/>` is essentially never a directly-openable path once the file is sitting in a plain downloaded folder instead of a live ROS workspace, where `package://` resolves through the ROS package index. The resolver tries, in order: (1) the reference as a path relative to the URDF's own folder, (2) the same reference with a leading `package://`-style package-name segment stripped, (3) as an absolute path if it happens to already be one, and (4) by bare basename anywhere under the source folder - which is what actually handles a real `package://` URI, since the scheme and package name are meaningless outside a live ROS workspace but the mesh's own filename is still findable.

---

## ✅ DOF Feasibility Validation

The automated version of the same judgment call this ecosystem's own past sessions made by hand for every robot added to STUDIO's catalog: **STUDIO's own kinematics supports 3, 4, 5, and 6-DOF serial chains today** (its `RobotState.joints` is a fixed `j1..j6` map) - a handful of real, license-clear candidate arms researched in the past turned out to be 7, 8, or 9-DOF and were discarded for exactly this reason, not hypothetically. On every import (and after every live edit that could change the count - retyping a joint, for instance), the app walks the actual parent/child joint graph and reports:

- **DOF count** - only `revolute`/`continuous`/`prismatic` joints count as a real, controllable degree of freedom; `fixed` contributes none.
- **Unsupported joint types** - a single `floating` or `planar` joint anywhere in the chain makes the whole robot infeasible regardless of DOF count, since STUDIO's joint model has no representation for either.
- **Tree integrity** - exactly one root link is required (a proper tree, not a forest or a cycle); any link not reachable from that root by a joint chain is flagged as disconnected, and any link referenced by no joint at all as an orphan.
- **Missing `<limit>`** - required by the URDF spec for anything but a `continuous` joint; flagged per-joint if absent.

The verdict and every reason behind it render live in the DOF panel, and the Upload panel refuses to push an infeasible robot to a server.

---

## 🎨 Live Editing with a Real 3D Preview

The Properties panel edits whichever link is selected in the Viewport panel's link tree, and every edit mutates the loaded model in place and re-validates/re-renders through one signal (`EditorController.notify_tree_changed`) - no panel has to know how the viewport or the DOF report reacts to its own edit:

- **Recolor** - a link's visual material, picked through a standard color dialog. A material shared by name across several links (a real URDF's top-level `<material name="...">` declaration referenced by more than one `<visual>`) recolors every link sharing it together, matching what that shared-material syntax actually means in the spec.
- **Rescale** - per-axis (X/Y/Z) scale factor on a mesh geometry's own `<mesh scale="...">` transform, not a destructive rewrite of the mesh's triangle data itself - the same edit re-applied later starts from the original, unmodified mesh every time.
- **Retype and re-limit a joint** - change a joint's type (any of the 6 the URDF spec defines) and its lower/upper limit, with the DOF panel's verdict updating immediately since a retype can change the DOF count or introduce an unsupported type.
- **Mass & inertia** - "Auto-calculate" fills mass/Ixx/Iyy/Izz from the selected link's own geometry using `inertia_calc.py`'s closed-form uniform-density formulas (Box/Cylinder/Sphere exact, Mesh a bounding-box approximation - said so explicitly, since there's no per-triangle mesh integrator here); an operator-entered mass always wins over the density-based guess, and with no mass entered yet it assumes a generic aluminum density (2700 kg/m³) and notes that it did. "Apply" commits the fields to `Link.inertial` - the same calculate-then-apply two-step pattern as Scale/Joint above, so a computed value can be eyeballed or hand-tweaked before it's written to the model.

The **Viewport panel** hosts the actual OpenGL 3D view plus a jog slider per movable joint, so the operator can preview the URDF moving through its own real range before ever touching STUDIO. Forward kinematics (`render/kinematics.py`) is generic over whatever tree was just imported - unlike HYDRA-UMC SUITE's own kinematics module, which drives a fixed registry of a few dozen known, hand-verified robot models, this app has to pose an arbitrary, previously-unseen URDF, so it composes each joint's real `<origin>`/`<axis>` (Rodrigues' rotation formula for an arbitrary revolute axis, not just the cardinal-direction shortcut a fixed registry could rely on) walking the actual parent/child graph.

**Z-up, not Y-up** - the one deliberate divergence from HYDRA-UMC SUITE's own viewport convention: URDF itself is a Z-up format (gravity is `-Z`, every `<origin>`/`<axis>` in a source file is authored assuming it), and this app's job is to show and edit a URDF faithfully in its own convention, not re-orient it into whatever a downstream viewer (STUDIO's Three.js scene, SUITE's own OpenGL scene) happens to prefer.

---

## 🗂️ Mesh Loading

`.stl` (via `numpy-stl`) and `.obj` (a small hand-rolled Wavefront loader - `v`/`vn`/`f` only, n-gon faces fan-triangulated) are both first-class. **COLLADA (`.dae`) is not supported** - it's a much larger XML scene-graph format (skeletal animation, multiple coordinate systems, embedded materials/textures) that would need a real parser to handle honestly rather than a best-effort guess at whichever tags a "simple" `.dae` happens to use; a link that references one gets a clear, named error instead of silently missing from the viewport or crashing the whole import. Every loaded mesh also gets the same defensive millimeter-vs-meter guard HYDRA-UMC STUDIO's own `useRealScaleSTL()` and HYDRA-UMC SUITE's own mesh loader apply: a link larger than 5 real-world meters in any axis is far more likely to be a millimeter-scale export with no unit metadata than an actual giant robot part, and gets rescaled by 0.001 automatically.

---

## 📜 URDF Parsing and Export

Plain XML via the standard library's own `xml.etree.ElementTree` - no `lxml` dependency needed for a format this simple. The in-memory model (`hydra_editor_urdf/models.py`) is a deliberately plain, mutable, in-house dataclass tree rather than a wrapper around an existing Python URDF library such as `urdfpy` or `yourdfpy`: this app needs to *edit* the tree interactively and re-render every change live, which a read-mostly parsing library isn't shaped for, and owning the model outright keeps it small, inspectable, and free of a third-party dependency's own release cadence. Field names and defaults follow the real [URDF XML schema](http://wiki.ros.org/urdf/XML) closely, so the parser/writer pair stays a thin, obvious XML↔object mapping.

**xacro is not expanded.** [xacro](http://wiki.ros.org/xacro) is a Python/XML macro preprocessor with its own ROS package and dependency chain, and a real xacro file is only reliably resolvable inside the same ROS package environment it was authored against (macro arguments, `$(find pkg)`-style includes, etc.) - something this app has no way to reproduce honestly. A file that uses `<xacro:...>` tags or declares the xacro namespace gets a clear error explaining the limitation and pointing at the ROS `xacro` command-line tool to preprocess it first, rather than a silent misparse.

Export (`urdf/writer.py`) re-serializes the current in-memory tree from scratch rather than patching the original source XML text, so every live edit - regardless of which panel made it - is reflected exactly once, through one code path, in both the "Export URDF" menu action and the payload sent to a STUDIO server.

---

## 🖥️ Dockable Workspace

Real `QDockWidget` panels - drag to float, drag back to dock, merge into tabs, split the workspace - the same mechanism and reasoning HYDRA-UMC SUITE's own main window already applies: Qt's own docking system already does exactly what a Photoshop/Fusion-360-style workspace needs, and a hand-rolled one would only reinvent it with more bugs. Five panels, arranged with a sensible default layout that's fully rearrangeable afterward:

- **Source** - GitHub URL / local folder input, found-`.urdf` list.
- **DOF** - the feasibility verdict and every reason behind it.
- **Viewport** - the live 3D view, link tree, and jog sliders.
- **Properties** - recolor / rescale / retype-and-relimit for the selected link.
- **Upload** - connect to a STUDIO server, push, or pull.

---

## ☁️ Server Round-Trip

Talks to HYDRA-UMC-SERVER's own model-submission contract (`POST /api/models/submit`, `GET /api/models`, `GET /api/models/:category/:slug/download` in that project's own `server.ts`, gated behind its own **Config > Models > "Accept model submissions"** toggle) using the standard library's own `urllib.request` - one more HTTP call didn't justify pulling in `httpx`/`requests` for a project that only ever needs 4 endpoints, not a persistent live connection. Every call runs on a background `QThread` so a slow or unreachable server never freezes the UI. This contract used to live inside HYDRA-UMC-STUDIO's own process before that project split into a pure frontend (STUDIO) plus a separate headless backend (HYDRA-UMC-SERVER, see **Related Projects** below) - this app doesn't hardcode either name, the operator just points the **Upload** panel's host/port fields at wherever the real backend is running.

- **Login** - `POST /api/login`; only an `admin`-role token can actually reach `POST /api/models/submit` server-side, so this app is only really usable against an admin account, same as every other admin-only STUDIO feature.
- **Push** - serializes the current robot back to URDF XML and base64-encodes every mesh file its visuals reference (resolved through the same mesh resolver built at import time) inline in the request body, tagged with the operator-picked category (mirroring STUDIO's own Config > UI > Module Visibility categories: Robot 3-6DOF, CNC, Pick & Place, Laser, Vacuum Table, XY Table, Heated Bed, ATC Tools - a URDF has no field of its own that says which of these it is). A name collision comes back as the server's own 409 response; the operator decides whether to resubmit with **Overwrite** checked or rename, this app never guesses.
- **Pull** - downloads an already-submitted model's URDF + meshes back down into a local working folder and loads it straight into the editor - the "extract, edit, resend" round-trip half of this app's own purpose, letting an existing catalog entry be touched up without starting from its original source repo again.

---

## 🌐 Multi-Language UI

Full interface translation across **English, Spanish, Italian, French, German, Chinese (simplified), and Japanese** (`language/*.lng`), using the exact same plain `KEY=Value` file mechanism as every other Python tool in this ecosystem (URTC Flasher, URTC Tester, HYDRA-UMC SUITE) - not reinvented here, since the mechanism itself carries no project-specific logic. A language switch takes effect after an app restart rather than retranslating every already-built widget live, matching that same convention. `language/` sits **next to** the executable rather than bundled inside it via PyInstaller's `--add-data`, so a translator can edit or add a `.lng` file without a rebuild.

---

## 🎛️ Theme

The dock workspace's top toolbar is a real `QToolBar`/`QLabel`/`QToolButton`
command deck, not a separate Qt Quick/QML UI - an earlier version embedded
through QQuickWidget (same renderer as HYDRA-UMC-UPDATER and HYDRA-UMC-SUITE)
rendered as a solid black bar with no console error once placed inside this
`QMainWindow`'s real `QDockWidget` layout, so it was reverted to plain
widgets; see `CHANGELOG.md` for the full story. Its Source, DOF, Viewport,
Properties and Upload buttons only raise the existing docks; Export and About
forward to the existing actions, and Export stays disabled until a model is
actually loaded. After a URDF load (and after every live property edit), its
status chip shows the loaded model's name, DOF count, and current feasibility
verdict. It does not replace the OpenGL viewport, editor, parser or
server-upload implementation.

Reuses HYDRA-UMC SUITE's own `assets/qss/industrial_dark.qss` verbatim (same relative path, same file) rather than designing a new visual theme for a sibling desktop tool in the same ecosystem.

### Visual command deck (`--qtquick`)

That embed attempt is a different, separate thing from the real Qt Quick
command deck this app now has:

~~~
python main.py --qtquick
~~~

A genuinely standalone QML `ApplicationWindow` (`qt_editor_urdf.py` +
`assets/qml/EditorDeck.qml`), never embedded inside the classic
`QMainWindow` - the same proven pattern HYDRA-UMC-OS-REBUILDER,
HYDRA-UMC-UPDATER, URTC-TESTER, URTC-FLASHER and HYDRA-UMC-SUITE already
use, launched alongside the unchanged classic entry point rather than
replacing it. It mirrors the classic dockable workspace's own real
layout (Source and DOF tabbed on the left, Viewport and Properties side
by side, Upload across the bottom) and every one of its 5 panels' real
features - GitHub/gallery/local-folder loading, live DOF validation, an
orbit/pan/zoom 3D preview with a clickable link tree and per-joint jog
sliders, color/scale/joint-limit/mass-and-inertia editing, and the
STUDIO server connect/push/pull round-trip - through the same
`EditorController`, without a second implementation of any of it. The
3D preview reuses the classic viewport's own real rendering code
(`render/viewport.py`'s `UrdfGLRenderer`) through a dedicated
`OffscreenUrdfRenderer`, the same real `QOpenGLContext`/
`QOffscreenSurface`/framebuffer approach HYDRA-UMC-SUITE's own Qt Quick
Viewport panel already uses, fed into QML through a
`QQuickImageProvider`.

---

## 📂 Repository Structure

```text
HYDRA-UMC-EDITOR-URDF/
├── main.py                        # Entry point - QApplication, theme, maximized start, F11 fullscreen toggle; --qtquick switches to the deck below
├── qt_editor_urdf.py               # Qt Quick front end - standalone `--qtquick` command deck, bridges the unchanged EditorController to QML
├── run.bat / run.sh                # Convenience wrapper - activates .venv if present, runs main.py, no auto-close
├── requirements.txt                # PySide6, PyOpenGL, numpy-stl, numpy (pinned)
├── build_exe.bat / build_exe.sh    # Windows/Linux standalone-executable build scripts (PyInstaller) - bumps the version first
├── build-test.bat / build-test.sh  # Non-versioning build/compile check
├── HYDRA-UMC_EDITOR-URDF.spec      # PyInstaller build spec used by build_exe.bat/.sh
├── bump_version.py                 # Odometer-style version bump, called by build_exe.bat/.sh before every real build
├── bump_manifest_version.py        # Syncs hydra-umc.project.json's version to the native one (--sync)
├── CHANGELOG.md                    # Version history
├── README.md                       # This file
├── README_spa.md / README_ita.md / README_fra.md / README_deu.md / README_zho.md / README_jpn.md  # <- translations
├── LICENSE                         # GPL-3.0
├── assets/
│   ├── HYDRA_UMC_ICON.svg          # Animated HYDRA-UMC mark used by the toolbar command deck
│   ├── qss/industrial_dark.qss     # Reused verbatim from HYDRA-UMC-SUITE
│   └── qml/EditorDeck.qml          # Qt Quick UI for the `--qtquick` command deck
├── images/
│   └── HYDRA_UMC_BANNER.svg        # Media and diagrams
├── language/                       # english/spanish/italian/french/german/japanese/chinese.lng - sits beside the exe, not bundled
├── hydra_editor_urdf/
│   ├── __init__.py                 # __version__ - single source of truth, read by the About dialog and rewritten by bump_version.py
│   ├── app.py                      # EditorController - single owner of "what's loaded", Qt signals every panel listens to
│   ├── models.py                   # In-house URDF object tree (Robot/Link/Joint/Visual/Geometry/Material/...)
│   ├── gallery.py                  # Starter list of real, verified public robot-description repositories
│   ├── inertia_calc.py             # Closed-form moment-of-inertia formulas for the primitive geometries
│   ├── i18n.py                     # language/*.lng loader, config persistence - ported from HYDRA-UMC-SUITE's own i18n.py
│   ├── urdf/
│   │   ├── parser.py               # URDF XML -> models.py tree (ElementTree, xacro detected and rejected with a clear error)
│   │   ├── writer.py                # models.py tree -> URDF XML string (export + server upload payload)
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
│   └── INTEGRATION_CONTRACT.md
├── tools/
│   ├── build_test.py               # Build/compile check without bumping version
│   └── ci_validate.py              # Manifest/CHANGELOG/docs validation used by CI
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

---

## 🛠️ Development Environment

### Requirements
- [Python](https://www.python.org/) 3.11 or higher
- pip

### Installation

```bash
pip install -r requirements.txt
```

This pulls in the pinned dependency set: **PySide6** (Qt6 UI), **PyOpenGL** (3D viewport rendering), **numpy** / **numpy-stl** (mesh math and STL loading). No `git` install is required - the GitHub source-loading path downloads a plain zipball over HTTPS.

### Development Mode

```bash
python main.py
```

Or use the convenience wrapper - `run.bat` (Windows) / `run.sh` (Linux/Mac), which activates `.venv` if one exists next to it and forwards any arguments to `main.py`; neither script closes its terminal window on its own when double-clicked.

Starts maximized (not true OS-level fullscreen, so the native window title bar and controls stay visible) - press **F11** to toggle real borderless fullscreen and back.

### Production Build

Compiles a standalone executable (no Python installation needed to run it) via PyInstaller:

- **Windows:** run `build_exe.bat` → produces `dist\HYDRA-UMC_EDITOR-URDF.exe`
- **Linux:** run `./build_exe.sh` (`chmod +x build_exe.sh` once first) → produces `dist/HYDRA-UMC_EDITOR-URDF`

Both scripts create/activate their own `.venv`, install `requirements.txt` plus `pyinstaller`, clean any previous `build`/`dist`, **bump the version number**, compile, and finally copy `README.md`, `LICENSE`, and the whole `language/` folder next to the resulting binary (`language/` is deliberately **not** bundled inside the executable via `--add-data`, so a `.lng` file can be edited or added afterward with no rebuild).

**Versioning:** the app's version (`hydra_editor_urdf/__version__`, shown in the Help → About dialog) follows `MAJOR.MINOR.PATCH`. Every real run of `build_exe.bat`/`build_exe.sh` calls `bump_version.py` first, which applies an odometer-style bump: `PATCH` goes up by 1; once `PATCH` would exceed 9 it resets to 0 and `MINOR` goes up by 1 instead (e.g. `0.0.9` → `0.1.0`). `MAJOR` is never touched automatically - that stays a deliberate, manual decision. See `CHANGELOG.md` for the version history.

If you'd rather run the equivalent steps by hand instead of the script - useful for adapting the build on a platform the scripts don't cover, or for debugging a PyInstaller flag - the manual process is:

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
# Windows: .venv\Scripts\activate.bat   |   Linux/Mac: source .venv/bin/activate

# 2. Install dependencies + PyInstaller
pip install -r requirements.txt
pip install pyinstaller

# 3. Locate PySide6's own install directory (its Qt plugins live under it)
python -c "import PySide6, os; print(os.path.dirname(PySide6.__file__))"
# -> $PYSIDE_DIR below

# 4. Compile - only 4 Qt plugin subfolders are staged explicitly (platforms/
#    styles/imageformats/iconengines), NOT --collect-all PySide6, which would
#    otherwise pull in Qt6WebEngineCore.dll and other multi-hundred-MB pieces
#    this app never uses. PyInstaller's own dependency analyzer finds the
#    actual Qt6Core/Gui/Widgets/OpenGL DLLs by following main.py's real import
#    graph - only the plugin folders need to be added by hand.
#
#    Windows (plugins live directly under PySide6/plugins/):
pyinstaller --onefile --windowed --noconfirm --name "HYDRA-UMC_EDITOR-URDF" \
    --add-data "assets;assets" \
    --add-data "%PYSIDE_DIR%\plugins\platforms;PySide6\plugins\platforms" \
    --add-data "%PYSIDE_DIR%\plugins\styles;PySide6\plugins\styles" \
    --add-data "%PYSIDE_DIR%\plugins\imageformats;PySide6\plugins\imageformats" \
    --add-data "%PYSIDE_DIR%\plugins\iconengines;PySide6\plugins\iconengines" \
    --hidden-import PySide6.QtOpenGL --hidden-import PySide6.QtOpenGLWidgets \
    --hidden-import OpenGL.platform.win32 \
    main.py

#    Linux (plugins live under PySide6/Qt/plugins/ instead - a different
#    layout than Windows, confirmed by reading PyInstaller's own runtime hook
#    pyi_rth_pyside6.py):
pyinstaller --onefile --noconfirm --name "HYDRA-UMC_EDITOR-URDF" \
    --add-data "assets:assets" \
    --add-data "$PYSIDE_DIR/Qt/plugins/platforms:PySide6/Qt/plugins/platforms" \
    --add-data "$PYSIDE_DIR/Qt/plugins/styles:PySide6/Qt/plugins/styles" \
    --add-data "$PYSIDE_DIR/Qt/plugins/imageformats:PySide6/Qt/plugins/imageformats" \
    --add-data "$PYSIDE_DIR/Qt/plugins/iconengines:PySide6/Qt/plugins/iconengines" \
    --hidden-import PySide6.QtOpenGL --hidden-import PySide6.QtOpenGLWidgets \
    main.py

# 5. Copy files that must sit NEXT TO the binary, not inside it
cp README.md LICENSE dist/
cp -r language dist/language
```

On Linux, running the compiled binary needs the system's own OpenGL runtime present (`libGL.so.1` - e.g. `libgl1` on Debian/Ubuntu, `mesa-libGL` on Fedora, `libglvnd` on Arch) plus `libxkbcommon-x11-0`/`xcb-util-cursor` for Qt's own XCB platform plugin; `build_exe.sh` checks for `libGL.so.1` up front and prints the right install command per distro if it's missing, rather than failing deep inside a PyInstaller run.

---

## 🔗 Related Projects

This project is part of the HYDRA-UMC robotics ecosystem by the same author (JuanenRac / Electro Hobby 3D). Worth knowing about, since a request might actually be about one of these rather than this repository.

**Parent Project**
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — the model catalog this editor exists to populate; the finished result is pushed straight to a running STUDIO server via `POST /api/models/submit`.

**Directly Related**
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — owns the real `POST /api/models/submit` endpoint this editor pushes finished models to.
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — consumes the URDF models created here to drive its physics simulation.
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — consumes the URDF models created here to drive its physics simulation.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — generates training data from the models created here.

**Also Part of the Ecosystem**

*Core Hardware & Platform*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — the physical robot-arm motherboard: CM5 host + dual-core STM32H745, orchestrating up to 8 tool arms over CAN-OTA/SPI-OTA.
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — reproducible Raspberry Pi OS product layer for the CM5: read-only agent, validated config/profiles, WiFi first-contact provisioning.
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — the shared JSON-Schema contract and safety-gate boundary every bridge validates its commands against.

*Core Backend & Clients*
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — desktop (PySide6) swarm command center for multiple servers at once, packaged as a standalone executable.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — native Android control app with biometric login and a paired Wear OS companion.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — iOS/iPadOS control app (Flutter) with real-time WebSocket sync.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — native touch UI for the onboard 7" DSI touchscreen, embedded on the CM5 itself.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — coordination boundary for AGV/AMR fleets via a real VDA 5050 MQTT publisher.
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — high-level CNC-cell coordinator with real GRBL status/control-byte access.
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — coordination boundary for legged/humanoid droids, with a real Boston Dynamics Spot command sender.
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — laser-cell safety coordinator reading 3 real key/enclosure/interlock GPIO safeguards.
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — safe high-level board-flow coordinator for OpenPnP pick-and-place.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — safe coordination boundary for Moonraker/Klipper 3D printers, with real gated job commands.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — safety coordinator with a real, lazily-imported rclpy ROS 2 transport.
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — coordination boundary for camera-equipped UAVs, with a real MAVLink command sender.

*URTC Tool Platform*
- **[URTC](https://github.com/JuanenRac/URTC)** — firmware for the physical Universal Robot Tool Controller PCB, 25+ tool profiles over CAN bus.
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — desktop GUI flashing tool for URTC boards, CAN-OTA plus full-chip SWD/JTAG.
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — desktop live CAN-bus diagnostic tool for URTC boards, one panel per tool profile.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — browser-based alternative to URTC-TESTER via the Web Serial API, no local install needed.

*Vision AI Node (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — integration hub for the Hailo-8 vision pipeline, with a real per-stage hardware-readiness check.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — real compiled-model registry with Hailo-architecture/checksum safe-load verification.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — real GStreamer pipeline + MediaMTX config generator with a real HailoRT integration boundary.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — real Position-Based Visual Servoing correction law, safety-gated on upstream zone state.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — real zone-breach checking and E-STOP requesting, with calibration-freshness enforcement.

*Cognitive AI Node (Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — integration hub for the Hailo-10 cognitive pipeline (LLM/VLA/voice orchestration).
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — real action-token encoding/decoding and trajectory generation for a Vision-Language-Action model.
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — real voice front-end (VAD + intent parser) with a bounded, confirmation-gated Watch relay.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — real rule-based task decomposition and semantic error recovery over MCU error codes.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — real stdlib-only TF-IDF document search over this ecosystem's own Markdown docs.

*Orchestration & Swarm*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — integration hub with a real gRPC/Protobuf health-report contract and mission state machine.
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — real priority-based job queue with deduplication, over a real HTTP API.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — real gRPC-based fleet health watchdog with retry/backoff and identity-mismatch detection.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — real RRT-based 3D path planner with real obstacle/workspace collision validation.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — real CRDT LWW-Element-Map state sync, property-tested for multi-cell convergence.

*Digital Twin & Simulation*
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — real hardware-in-the-loop safety interlock routing commands between simulation and real hardware.

*Data & Analytics*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — real sqlite3-backed time-series store with a real ingest/query HTTP API.
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — real FFT + statistical baseline anomaly detector with drift monitoring.
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — real OEE/availability calculation over DATALAKE history, with reproducible CSV export.
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — real CAN/WebSocket ingestion pipeline into DATALAKE, with sequence deduplication.

*Industrial Gateway*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — integration hub relaying to industrial protocols, with a real command allowlist/backpressure layer.
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — real OPC-UA address space, verified with a real binary-protocol client session.
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — real MQTT broker with optional per-client authentication and topic ACLs.
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — real MTConnect `/probe` and `/current` XML endpoints with degraded-mode output.

*Complementary Tools & Ecosystem Operations*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — Smart Summaries and Anomaly Highlighting panels over DATALAKE/ANOMALY-DETECTOR, with an honest statistical fallback.
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — fleet CLI with a real, stable exit-code contract, a genuine live client of HYDRA-UMC-SERVER's own API.
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — WearOS companion app with real haptic alerts and a paired-phone voice relay.
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — firmware for a board-mounting rack with real tool-ID decoding and Smart Idle pre-heating logic.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — firmware plus a real Python vision companion for a thermal/RGB inspection tool head.
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — administrative desktop tool that discovers, clones and updates every repo in this ecosystem.
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** — Windows/Linux desktop tool that builds a ready-to-flash CM5 image pre-loaded with the ecosystem's most current versions, with Raspberry-Pi-Imager-style first-boot Wi-Fi/user/SSH configuration.

---

## 📚 Documentation & Community

- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — the editor's own internal shape: why parsing, feasibility validation, mesh resolution and 3D preview are separate lanes, and what this app deliberately does *not* do (connect to a robot, upload a URDF, or command motion on its own).
- **[docs/BUILD_AND_RUN.md](docs/BUILD_AND_RUN.md)** — the non-mutating `build-test.bat`/`.sh` validation path versus a real `build_exe.bat`/`.sh` package, plus what the command deck actually is today (`QToolBar`, not Qt Quick/QML - see the **Theme** section above).
- **[docs/INTEGRATION_CONTRACT.md](docs/INTEGRATION_CONTRACT.md)** — what a downstream consumer of an exported URDF file must validate on its own; this project provides no network endpoint or hardware-control authority of its own.
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — tech stack and coding guidelines for a pull request.
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — the standards of behavior expected in this community.
- **[SECURITY.md](SECURITY.md)** — how to report a vulnerability, and this project's own real security focus areas.
- **[SUPPORT.md](SUPPORT.md)** — where to ask questions and report bugs.
- **[LICENSE.md](LICENSE.md)** — this project's own license.

## 👤 AUTHOR
**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 LICENSE

HYDRA-UMC EDITOR-URDF is (c) 2026 JuanenRac (Electro Hobby 3D). This notice must be included in any distributions of this project or derivative works.

This project consists of source code and its own documentation, made available under different licenses - each suited to what it actually covers:

1. The source code (`hydra_editor_urdf/`, `main.py`, and any binary built from it via `build_exe.bat`/`build_exe.sh`) is available under the **GNU General Public License v3.0 (GPL-3.0)**. Full text at https://www.gnu.org/licenses/gpl-3.0.html.

2. The documentation (this README and its own translations - `README_spa.md`, `README_ita.md`, `README_fra.md`, `README_deu.md`, `README_zho.md`, `README_jpn.md`) is available under **Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)**. Full text at https://creativecommons.org/licenses/by-sa/4.0/.

This app ships no third-party robot mesh assets of its own - unlike HYDRA-UMC STUDIO's `public/models/`, every mesh this editor ever loads comes from whichever source repo or local folder the operator points it at, under that source's own original license. Reviewing and preserving that upstream license/attribution before submitting a model to a running STUDIO server (whose own `public/models/<slug>/ATTRIBUTION.txt` convention this editor's export feeds into) remains the operator's own responsibility - this app has no way to detect or enforce a source repo's licensing terms automatically.

This editor is the model-authoring tool for the [HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO) catalog - see that repository for its own server-side licensing, which this repository's own license doesn't extend to, and vice versa.

If you build on this project, keep the licensing split in mind: code changes here should stay GPL-3.0, documentation derivatives (this README and its translations) should stay CC BY-SA 4.0, and any mesh asset that passes through this editor (imported, edited, or exported) should stay under whatever license its own original source repo carries, with attribution back to that source.
