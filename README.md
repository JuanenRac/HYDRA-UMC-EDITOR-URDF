<!-- =============================================================================
HYDRA-UMC-EDITOR-URDF - Desktop URDF creator and editor for the model catalogue of HYDRA-UMC-STUDIO
Copyright (C) JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE
============================================================================= -->

<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-EDITOR-URDF banner" width="100%">
</p>

# 🖌️ HYDRA-UMC-EDITOR-URDF

<p align="center">🇺🇸 <b>English</b> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | <a href="README_zho.md">🇨🇳 简体中文</a> | <a href="README_jpn.md">🇯🇵 日本語</a> | <a href="README_por.md">🇵🇹 Português</a></p>

### 🖌️ Graphical URDF Creator/Editor for the HYDRA-UMC-STUDIO Model Catalog

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Language-Python%203.11-3776AB.svg" alt="Language">
  <img src="https://img.shields.io/badge/Framework-PySide6-41CD52.svg" alt="Framework">
  <img src="https://img.shields.io/badge/Format-URDF-red.svg" alt="Format">
  <img src="https://img.shields.io/badge/Tests-538%20passing-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Version-0.1.7-0f6cbd.svg" alt="Version">
  <img src="https://img.shields.io/badge/Maturity-established-2EA44F.svg" alt="Maturity">
</p>

---

---

**Honesty check - what actually runs today:** the pure-logic core - URDF parsing/export (`urdf/parser.py`, `urdf/writer.py`), DOF feasibility validation (`urdf/dof.py`), forward kinematics (`render/kinematics.py`), inertia estimation (`inertia_calc.py`), mesh-reference resolution and GitHub-zipball fetching (`source/scan.py`, `source/github_fetcher.py`, `source/local_folder.py`), the in-memory model (`models.py`), the gallery list (`gallery.py`) and the i18n loader (`i18n.py`) - is real and covered by 538 passing tests (`tests/`), none of which import PySide6/PyOpenGL. `test_github_fetcher.py` mocks every network call - a real GitHub zipball download has been run manually, never as part of the automated suite. The Qt/OpenGL layer (`render/viewport.py`'s `UrdfGLRenderer`, `render/mesh.py`, every `ui/*` panel, and the `--qtquick` deck's `OffscreenUrdfRenderer`) is real, working code but has no automated test coverage at all - it needs a real display/Qt platform plugin, which CI doesn't have, so it's verified by hand, not by a test suite. `server/client.py`'s `StudioClient` (login/push/pull against HYDRA-UMC-SERVER's `server.ts`) is real HTTP code, tested against a small local server that keeps the contract of `server.ts` (the token on every call, a name collision, the download of a model, a hostile answer). xacro expansion and COLLADA (`.dae`) mesh loading are explicit, named non-features (a clear error, not a silent misparse) - see the Honesty note in the Overview below and the URDF Parsing/Mesh Loading sections for why. See `CHANGELOG.md` for exactly what has shipped so far. The one exception is opt-in: with `xacro_expand` set to true in `hydra_editor_urdf_config.json` and the `xacro` tool installed on the machine, a xacro file is expanded by that tool (nothing is bundled).

> **Safety and security status:** this ecosystem is not a certified safety system. There is no hardware E-STOP path, no firmware-enforced limits or interlocks and no verified motion command yet; firmware images are checked with CRC-32 and an Ed25519 signature, and a release build refuses the published development keys (the tool heads and expansion boards behind the relay still run URTC bootloaders, which take a shared-key HMAC-SHA256 instead of a signature); TLS and mutual TLS are optional and off by default; no custom board has been populated or tested yet. Read the [security baseline](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md) and the [threat model](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md) before relying on any statement here for the safety of a person.

---

## 📋 At a glance

| | |
|---|---|
| Version | `0.1.7` |
| Maturity | Established |
| Tests | 538 (`python -m pytest tests -q`) |
| Stack | Python / PySide6 / Qt6 / OpenGL |
| Target | The PC of the person using it |
| On real hardware | Not applicable: nothing here runs on hardware |

**Jump to:** [Overview](#-overview) · [Architecture](#-architecture) · [Features](#-features) · [Security & Safety](#-security--safety) · [Interfaces](#-interfaces) · [Configuration](#-configuration) · [Quick start](#-quick-start) · [Testing](#-testing) · [Troubleshooting](#-troubleshooting) · [Repository Structure](#-repository-structure) · [Related Projects](#-related-projects)

## 🚦 Project status

Each line is one part of this repository and the light says how far it is today. It is written from what the repository can show (tests, builds, runs), not from what is planned.

🟢 Done and verified · 🟡 Works, with known limits · 🟠 Partly done or not verified yet · 🔴 Not done or not working

| Area | State | What it means here |
|---|---|---|
| Software | 🟢 | Complete for its purpose and stable; the honesty check above lists the known limits |
| Tests | 🟢 | 538 automated tests, run on every change |
| Real hardware | 🟢 | Not applicable: nothing here runs on hardware |
| Documentation | 🟢 | README in eight languages, checked against the manifest on every change |

## 🎯 Overview

**HYDRA-UMC EDITOR-URDF** is the desktop tool that turns "porting a new robot into [HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)'s model catalog" from a manual, per-robot investigation into a repeatable, graphical workflow. Every real robot model in STUDIO's catalog got there the same way in the past: find a description repo on GitHub, figure out how its mesh references resolve, count the degrees of freedom in its kinematic chain, check whether STUDIO can actually drive that many, and hand-place the result into `public/models/`. This app automates that entire pass - pull the source files from a GitHub URL or an already-downloaded local folder, resolve every `<mesh filename="...">` reference (`package://` URIs included) against the real files on disk, validate the chain's DOF count against what STUDIO's kinematics supports today, edit color/scale/joint limits/joint type with a live 3D preview, and push the finished result straight to a running STUDIO server.

Built with **Python** and **PySide6/Qt6**, using the same architectural patterns already validated in this ecosystem's other desktop tool, [HYDRA-UMC SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE): a Photoshop/Fusion-360-style dockable workspace (`QDockWidget`), a hand-written OpenGL 3D viewport (`QOpenGLWidget` + GLSL 3.3 core-profile shaders, no `glBegin`/`glEnd` legacy path), and one central controller object that owns state and every UI panel listens to via Qt signals. Reusing that pattern here - rather than exploring a new UI/render stack for a sibling tool in the same ecosystem - is a deliberate choice, not an oversight.

**Honesty note, matching the rest of this ecosystem's own documentation convention:** this app does not expand [xacro](http://wiki.ros.org/xacro) macros, and does not load COLLADA (`.dae`) meshes. Both are named, explicit limitations (a clear error message, not a silent misparse or a missing link in the viewport) rather than a half-implemented attempt - see the **URDF Parsing** and **Mesh Loading** sections below for why real support for either would take significant additional work. The one exception is opt-in: with `xacro_expand` set to true in `hydra_editor_urdf_config.json` and the `xacro` tool installed on the machine, a xacro file is expanded by that tool (nothing is bundled).

## 🧩 Role in HYDRA-UMC

**HYDRA-UMC-EDITOR-URDF** is the desktop tool that turns porting a new robot into the model catalogue of HYDRA-UMC-STUDIO from a manual investigation into a repeatable workflow. It loads a URDF from a GitHub repository or a local folder, tells whether the robot fits the 3 to 6 degrees of freedom STUDIO supports, shows it in a live 3D view where links can be recoloured, rescaled and given new joint limits, and exports the URDF or pushes it to a HYDRA-UMC-SERVER.

## 🏛️ Architecture

<p align="center">
  <img src="images/architecture.svg" alt="HYDRA-UMC-EDITOR-URDF architecture" width="100%">
</p>

## ✨ Features

### Source Loading - GitHub or Local Folder

Two ways to point the app at a robot's source files, both landing in the same import path:

- **From a GitHub URL** - accepts a full `https://github.com/owner/repo` URL (with or without `/tree/<branch>`), an SSH-style `git@github.com:owner/repo.git`, or the bare `owner/repo` shorthand. Deliberately does **not** shell out to `git clone`, which would make a `git` install a hard runtime dependency on both Windows and Linux for something a plain HTTPS download already does: GitHub serves a zipball of any branch/tag/commit from `codeload.github.com` with no authentication needed for a public repo, so this uses the standard library's own `urllib.request` + `zipfile` and nothing else. Only public repos are supported - there's no token/credential handling, and a private repo's zipball 404s the same as a nonexistent one.
- **From a local folder** - for a repo already downloaded by hand, or a working copy the operator is actively editing outside this app.
- **From the Gallery** - a small "Gallery" dropdown above the GitHub URL field (`hydra_editor_urdf/gallery.py`) lists a short, hand-checked starter set of real, currently-active robot-description repos (ROS-Industrial's `universal_robot`, ROBOTIS' `open_manipulator`). Picking an entry only fills the URL field and shows its description - it never fetches on its own, the operator still presses Fetch, same as typing a URL by hand. A deliberately short, hand-picked list rather than an auto-scraped one: a gallery entry pointing at a dead or malicious repo would be worse than no gallery at all.

Either way, the app then recursively finds every `*.urdf`/`*.xacro` file under the chosen folder, lists all of them (a real robot description repo often ships more than one - a bare arm plus a "with gripper" variant is a common pairing), and auto-picks the largest by file size as a reasonable default for "the main one" - switching to a different candidate afterward is one double-click in the Source panel, not a re-fetch.

**Mesh reference resolution** is the actual unglamorous work every past manual robot-porting session in this ecosystem did by hand: a URDF's `<mesh filename="package://some_pkg/meshes/link1.stl"/>` is essentially never a directly-openable path once the file is sitting in a plain downloaded folder instead of a live ROS workspace, where `package://` resolves through the ROS package index. The resolver tries, in order: (1) the reference as a path relative to the URDF's own folder, (2) the same reference with a leading `package://`-style package-name segment stripped, (3) as an absolute path if it happens to already be one, and (4) by bare basename anywhere under the source folder - which is what actually handles a real `package://` URI, since the scheme and package name are meaningless outside a live ROS workspace but the mesh's own filename is still findable.

### DOF Feasibility Validation

The automated version of the same judgment call this ecosystem's own past sessions made by hand for every robot added to STUDIO's catalog: **STUDIO's own kinematics supports 3, 4, 5, and 6-DOF serial chains today** (its `RobotState.joints` is a fixed `j1..j6` map) - a handful of real, license-clear candidate arms researched in the past turned out to be 7, 8, or 9-DOF and were discarded for exactly this reason, not hypothetically. On every import (and after every live edit that could change the count - retyping a joint, for instance), the app walks the actual parent/child joint graph and reports:

- **DOF count** - only `revolute`/`continuous`/`prismatic` joints count as a real, controllable degree of freedom; `fixed` contributes none.
- **Unsupported joint types** - a single `floating` or `planar` joint anywhere in the chain makes the whole robot infeasible regardless of DOF count, since STUDIO's joint model has no representation for either.
- **Tree integrity** - exactly one root link is required (a proper tree, not a forest or a cycle); any link not reachable from that root by a joint chain is flagged as disconnected, and any link referenced by no joint at all as an orphan.
- **Missing `<limit>`** - required by the URDF spec for anything but a `continuous` joint; flagged per-joint if absent.

The verdict and every reason behind it render live in the DOF panel, and the Upload panel refuses to push an infeasible robot to a server.

### Live Editing with a Real 3D Preview

The Properties panel edits whichever link is selected in the Viewport panel's link tree, and every edit mutates the loaded model in place and re-validates/re-renders through one signal (`EditorController.notify_tree_changed`) - no panel has to know how the viewport or the DOF report reacts to its own edit:

- **Recolor** - a link's visual material, picked through a standard color dialog. A material shared by name across several links (a real URDF's top-level `<material name="...">` declaration referenced by more than one `<visual>`) recolors every link sharing it together, matching what that shared-material syntax actually means in the spec.
- **Rescale** - per-axis (X/Y/Z) scale factor on a mesh geometry's own `<mesh scale="...">` transform, not a destructive rewrite of the mesh's triangle data itself - the same edit re-applied later starts from the original, unmodified mesh every time.
- **Retype and re-limit a joint** - change a joint's type (any of the 6 the URDF spec defines) and its lower/upper limit, with the DOF panel's verdict updating immediately since a retype can change the DOF count or introduce an unsupported type.
- **Mass & inertia** - "Auto-calculate" fills mass/Ixx/Iyy/Izz from the selected link's own geometry using `inertia_calc.py`'s closed-form uniform-density formulas (Box/Cylinder/Sphere exact, Mesh a bounding-box approximation - said so explicitly, since there's no per-triangle mesh integrator here); an operator-entered mass always wins over the density-based guess, and with no mass entered yet it assumes a generic aluminum density (2700 kg/m³) and notes that it did. "Apply" commits the fields to `Link.inertial` - the same calculate-then-apply two-step pattern as Scale/Joint above, so a computed value can be eyeballed or hand-tweaked before it's written to the model.

The **Viewport panel** hosts the actual OpenGL 3D view plus a jog slider per movable joint, so the operator can preview the URDF moving through its own real range before ever touching STUDIO. Forward kinematics (`render/kinematics.py`) is generic over whatever tree was just imported - unlike HYDRA-UMC SUITE's own kinematics module, which drives a fixed registry of a few dozen known, hand-verified robot models, this app has to pose an arbitrary, previously-unseen URDF, so it composes each joint's real `<origin>`/`<axis>` (Rodrigues' rotation formula for an arbitrary revolute axis, not just the cardinal-direction shortcut a fixed registry could rely on) walking the actual parent/child graph.

**Z-up, not Y-up** - the one deliberate divergence from HYDRA-UMC SUITE's own viewport convention: URDF itself is a Z-up format (gravity is `-Z`, every `<origin>`/`<axis>` in a source file is authored assuming it), and this app's job is to show and edit a URDF faithfully in its own convention, not re-orient it into whatever a downstream viewer (STUDIO's Three.js scene, SUITE's own OpenGL scene) happens to prefer.

### Mesh Loading

`.stl` (via `numpy-stl`) and `.obj` (a small hand-rolled Wavefront loader - `v`/`vn`/`f` only, n-gon faces fan-triangulated) are both first-class. **COLLADA (`.dae`) is not supported** - it's a much larger XML scene-graph format (skeletal animation, multiple coordinate systems, embedded materials/textures) that would need a real parser to handle honestly rather than a best-effort guess at whichever tags a "simple" `.dae` happens to use; a link that references one gets a clear, named error instead of silently missing from the viewport or crashing the whole import. Every loaded mesh also gets the same defensive millimeter-vs-meter guard HYDRA-UMC STUDIO's own `useRealScaleSTL()` and HYDRA-UMC SUITE's own mesh loader apply: a link larger than 5 real-world meters in any axis is far more likely to be a millimeter-scale export with no unit metadata than an actual giant robot part, and gets rescaled by 0.001 automatically.

---

Mesh paths are confined: a `<mesh filename>` is only resolved to a `.stl`, `.obj` or `.dae` file inside the opened folder, the URDF folder or a folder you added with "Locate Missing Meshes"; `..` segments, absolute paths and `file://` URIs that lead anywhere else are ignored, and only those files are ever uploaded. Meshes that are empty, truncated or malformed are reported as not loaded instead of stopping the viewer. The millimetre-to-metre guard rescales any mesh larger than 5 units before the URDF `scale` is applied, so a mesh that is already scaled by the URDF can be reduced twice. Tags the editor does not model (`<dynamics>`, `<safety_controller>`, `<mimic>`, `<transmission>`, `<gazebo>`, material textures) are not kept when a URDF is re-exported.

### URDF Parsing and Export

Plain XML via the standard library's own `xml.etree.ElementTree` - no `lxml` dependency needed for a format this simple. The in-memory model (`hydra_editor_urdf/models.py`) is a deliberately plain, mutable, in-house dataclass tree rather than a wrapper around an existing Python URDF library such as `urdfpy` or `yourdfpy`: this app needs to *edit* the tree interactively and re-render every change live, which a read-mostly parsing library isn't shaped for, and owning the model outright keeps it small, inspectable, and free of a third-party dependency's own release cadence. Field names and defaults follow the real [URDF XML schema](http://wiki.ros.org/urdf/XML) closely, so the parser/writer pair stays a thin, obvious XML↔object mapping.

**xacro is not expanded.** [xacro](http://wiki.ros.org/xacro) is a Python/XML macro preprocessor with its own ROS package and dependency chain, and a real xacro file is only reliably resolvable inside the same ROS package environment it was authored against (macro arguments, `$(find pkg)`-style includes, etc.) - something this app has no way to reproduce honestly. A file that uses `<xacro:...>` tags or declares the xacro namespace gets a clear error explaining the limitation and pointing at the ROS `xacro` command-line tool to preprocess it first, rather than a silent misparse. The one exception is opt-in: with `xacro_expand` set to true in `hydra_editor_urdf_config.json` and the `xacro` tool installed on the machine, a xacro file is expanded by that tool (nothing is bundled).

**Optional checks and exports, all off by default** (switches in `hydra_editor_urdf_config.json`): `self_collision_check` lists, as warnings, pairs of links whose boxes overlap in the home pose or while one joint at a time is jogged (`self_collision_steps`, `self_collision_tolerance_m`; the boxes contain the real shapes, so a near miss can be reported but an overlap is not missed); `license_check` warns about meshes with no LICENSE, COPYING, NOTICE or ATTRIBUTION file in their folders and about licenses with conditions, and an ATTRIBUTION text can be built from what is found; the Export window has a Y-up box that writes the model for a Three.js scene (a root link turns the world a quarter turn, `y_up_scale` scales the lengths). None of them changes feasibility or what is written unless it is switched on.

**Physical check of the model, off by default** (`physical_check` in `hydra_editor_urdf_config.json`; details in `docs/PHYSICAL_CHECK.md`): the DOF screen lists, as warnings, what a real body could not be - more than one root, a cycle, an unused or unreachable link, a mass that is not above 0, an inertia tensor that is not positive definite or whose principal moments break the triangle inequality (Ixx + Iyy >= Izz and the permutations), lower above upper, effort or velocity not above 0, a zero or non-unit axis, a continuous joint with limits, a mesh that is missing or badly scaled, and lengths, angles or masses that look like millimetres, degrees or grams. Each warning gives the rule, the element, the value, the limit and a suggested correction that is never applied. The same check runs without a window with `python main.py --cli physical-check FILE.urdf [--json]` (exit 0 clean, 1 warnings, 2 error). Tested with generated models and simulated cases, not against a catalogue of real robots.

Export (`urdf/writer.py`) re-serializes the current in-memory tree from scratch rather than patching the original source XML text, so every live edit - regardless of which panel made it - is reflected exactly once, through one code path, in both the "Export URDF" menu action and the payload sent to a STUDIO server.

The elements the model has no field for (`<transmission>`, `<gazebo>`, the `<dynamics>`, `<safety_controller>` and `<calibration>` of a joint, and the multiplier and offset of a `<mimic>`) are kept as text when a file is read. The **Export** button opens a window that says how many such elements the file has and has a switch, off by default and off again for every robot that is loaded, to write them back as the source file had them; those that name a joint or a link that was deleted are never written back.

### Dockable Workspace

Real `QDockWidget` panels - drag to float, drag back to dock, merge into tabs, split the workspace - the same mechanism and reasoning HYDRA-UMC SUITE's own main window already applies: Qt's own docking system already does exactly what a Photoshop/Fusion-360-style workspace needs, and a hand-rolled one would only reinvent it with more bugs. Five panels, arranged with a sensible default layout that's fully rearrangeable afterward:

- **Source** - GitHub URL / local folder input, found-`.urdf` list.
- **DOF** - the feasibility verdict and every reason behind it.
- **Viewport** - the live 3D view, link tree, and jog sliders.
- **Properties** - recolor / rescale / retype-and-relimit for the selected link.
- **Upload** - connect to a STUDIO server, push, or pull.

### Server Round-Trip

Talks to HYDRA-UMC-SERVER's own model-submission contract (`POST /api/models/submit`, `GET /api/models`, `GET /api/models/:category/:slug/download` in that project's own `server.ts`, gated behind its own **Config > Models > "Accept model submissions"** toggle) using the standard library's own `urllib.request` - one more HTTP call didn't justify pulling in `httpx`/`requests` for a project that only ever needs 4 endpoints, not a persistent live connection. Every call runs on a background `QThread` so a slow or unreachable server never freezes the UI. This contract used to live inside HYDRA-UMC-STUDIO's own process before that project split into a pure frontend (STUDIO) plus a separate headless backend (HYDRA-UMC-SERVER, see **Related Projects** below) - this app doesn't hardcode either name, the operator just points the **Upload** panel's host/port fields at wherever the real backend is running.

- **Login** - `POST /api/login`; only an `admin`-role token can actually reach `POST /api/models/submit` server-side, so this app is only really usable against an admin account, same as every other admin-only STUDIO feature.
- **Push** - serializes the current robot back to URDF XML and base64-encodes every mesh file its visuals reference (resolved through the same mesh resolver built at import time) inline in the request body, tagged with the operator-picked category (mirroring STUDIO's own Config > UI > Module Visibility categories: Robot 3-6DOF, CNC, Pick & Place, Laser, Vacuum Table, XY Table, Heated Bed, ATC Tools - a URDF has no field of its own that says which of these it is). A name collision comes back as the server's own 409 response; the operator decides whether to resubmit with **Overwrite** checked or rename, this app never guesses.
- **Pull** - downloads an already-submitted model's URDF + meshes back down into a local working folder and loads it straight into the editor - the "extract, edit, resend" round-trip half of this app's own purpose, letting an existing catalog entry be touched up without starting from its original source repo again.

### Multi-Language UI

Full interface translation across **English, Spanish, Italian, French, German, Chinese (simplified), Japanese and Portuguese** (`language/*.lng`), using the exact same plain `KEY=Value` file mechanism as every other Python tool in this ecosystem (URTC Flasher, URTC Tester, HYDRA-UMC SUITE) - not reinvented here, since the mechanism itself carries no project-specific logic. A language switch takes effect after an app restart rather than retranslating every already-built widget live, matching that same convention. `language/` sits **next to** the executable rather than bundled inside it via PyInstaller's `--add-data`, so a translator can edit or add a `.lng` file without a rebuild.

### Theme

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

## 🔒 Security & Safety

| Threat | Defence | Where |
|---|---|---|
| A mesh path that climbs out of the folder | A `<mesh filename>` is only resolved to a `.stl`, `.obj` or `.dae` file inside the opened folder, the URDF folder or a folder you added with "Locate Missing Meshes"; `..`, absolute paths and `file://` URIs that lead elsewhere are ignored, and only those files are ever uploaded | `source/scan.py`, `render/mesh.py` |
| A broken, empty or hostile mesh or URDF file | Empty, truncated or malformed meshes are reported as not loaded instead of stopping the viewer; files that are not UTF-8 or are binary, malformed text and a cycle in the link tree are refused with a message; a mesh larger than 5 units is rescaled once as millimetres | `render/mesh.py`, `urdf/parser.py`, `tests/test_edge_cases.py` |
| A GitHub download that hangs or is not GitHub | Only addresses that the GitHub URL pattern recognises are fetched, as a zipball with a 20 s time limit per request and no `git` call; GitHub's own rate limit of 60 requests an hour per address applies | `source/github_fetcher.py` |
| A robot that STUDIO cannot run, or a model saved with impossible values | The feasibility check accepts 3 to 6 degrees of freedom and refuses floating and planar joints, orphans and disconnected or multi-parent trees; a check runs before saving (joint limits, masses) and the export keeps a backup | `urdf/dof.py`, `urdf/save_check.py` |
| Pushing a model to a server that did not ask for it | The server decides: it must have "Accept model submissions" on (Config > Models) and the account must be an administrator; every call has a 15 s time limit and runs in a background thread; a name that already exists is refused until Overwrite is ticked | `server/client.py` |

**What it never does:** connect to a robot, move one, or give a downstream consumer any guarantee about an exported URDF. Whoever uses the file must check it on their own side.

## 🔌 Interfaces

| Topic or route | What it carries |
|---|---|
| URDF file or folder / GitHub address | what is opened: a folder on disk, or a public GitHub repository downloaded as a zip; `.xacro` files are refused with an explanation and `.dae` meshes are named as unsupported |
| URDF export | the whole tree is written again from the model by `urdf/writer.py`, so every edit is in the file exactly once; the file you overwrite is backed up first |
| `POST /api/login` | signs in; only an `admin` token reaches the submission route, and the client copes with a server that asks for a sign-in even to list models |
| `POST /api/models/submit`, `GET /api/models`, `GET /api/models/:category/:slug/download` | push the URDF with its meshes inline, list the catalogue, and pull a submitted model back into a local working folder |

## ⚙️ Configuration

There is one small configuration file and the pinned dependencies; nothing else is read from the environment.

| Variable | Default | What it sets |
|---|---|---|
| `hydra_editor_urdf_config.json` | `{"language": ...}` | the language of the window, one of the eight `.lng` files in `language/`; the file sits beside the program |
| `requirements.txt` | pinned | numpy 2.5.2, numpy-stl 4.0.0, PyOpenGL 3.1.10 and PySide6 6.11.1 |
| `MIN_SUPPORTED_DOF`, `MAX_SUPPORTED_DOF` | 3, 6 | the degrees of freedom STUDIO can run, in `urdf/dof.py`; change them there if STUDIO changes |

## 🚀 Quick start

Requires Python 3.11 or newer and a graphics driver with OpenGL 3.3. The packages are pinned in `requirements.txt` and no `git` install is needed: the GitHub sources are downloaded as a zip.

```bash
pip install -r requirements.txt  # installs PySide6, PyOpenGL, numpy and numpy-stl at the pinned versions
python main.py                   # starts the editor (run.bat or run.sh do the same inside a .venv when there is one)
python main.py --qtquick         # the separate Qt Quick command deck
python -m pytest tests -q        # runs the tests (pip install -r requirements-dev.txt first)
```

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

## 🧪 Testing

538 automated tests run with `python -m pytest tests -q`. They need no hardware and nothing outside this machine.

The CI runs `HYDRA_UMC_CI=1 python tools/ci_validate.py`, which checks the manifest, the documents, the eight READMEs and the pictures.

### Automated Tests

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ -q
```

Note: this app's own pure logic (URDF parsing/export, DOF feasibility, forward kinematics, inertia estimation, mesh-reference resolution, GitHub fetching, i18n) had zero automated test coverage. Fixed: 538 real tests across 15 test modules, none of which import PySide6/PyOpenGL - `requirements-dev.txt` installs only what `tests/` actually needs (`numpy` + `pytest`), so the suite runs without a display or a Qt platform plugin. Several tests are explicit regressions for bugs already found and fixed earlier and documented inline in the source itself (`render/kinematics.py`'s infinite-loop-on-a-real-cycle guard, `source/scan.py`'s `had_scheme` gating, `urdf/dof.py`'s negative-mass check) - a future edit can't silently reintroduce any of them without a test failing. CI (`.github/workflows/ci.yml`) runs the same command on every push.

## 🏗️ Build & Release

### Production Build

Compiles a standalone executable (no Python installation needed to run it) via PyInstaller:

- **Windows:** run `build_exe.bat` → produces `dist\HYDRA-UMC_EDITOR-URDF.exe`
- **Linux:** run `./build_exe.sh` (`chmod +x build_exe.sh` once first) → produces `dist/HYDRA-UMC_EDITOR-URDF`

Both scripts create their own `.venv`, install `requirements.txt` plus `pyinstaller`, clean any previous `build`/`dist`, compile, and finally copy `README.md`, `LICENSE`, and the whole `language/` folder next to the resulting binary (`language/` is deliberately **not** bundled inside the executable via `--add-data`, so a `.lng` file can be edited or added afterward with no rebuild).

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

## 🩺 Troubleshooting

| You see | Because | Do |
|---|---|---|
| An error that names xacro, or a link that is missing in the viewport | The file uses `<xacro:...>` macros, which are not expanded, or the link points to a `.dae` mesh, which is not loaded | Expand the xacro first with the ROS `xacro` tool, and export the meshes as `.stl` or `.obj` |
| Links with no mesh after opening a repository | The mesh paths do not resolve inside the opened folder, or the meshes are empty or malformed | Use "Locate Missing Meshes" to add the folder that holds them |
| The DOF panel says the robot is not feasible | The robot has fewer than 3 or more than 6 degrees of freedom, a floating or planar joint, an orphan link, or a disconnected or multi-parent tree | Read the reasons listed under the verdict and edit the joint types and limits in the Properties panel |
| The push is refused: a 409, a 401, or "submissions are not accepted" | The name already exists (409), the account is not an administrator or the session is gone (401), or the server has Accept model submissions off | Tick Overwrite to replace, sign in as an administrator, or turn the submissions on in the server's Config > Models |

## 📂 Repository Structure

<p align="center">
  <img src="images/repository-structure.svg" alt="Repository structure of HYDRA-UMC-EDITOR-URDF" width="100%">
</p>

<details>
<summary>Text version of the tree</summary>

```text
HYDRA-UMC-EDITOR-URDF/
├── hydra_editor_urdf/
│   ├── __init__.py                  __version__ - single source of truth, read by the About dialog and rewritten by bump_version.py
│   ├── app.py                       EditorController - single owner of "what's loaded", Qt signals every panel listens to
│   ├── models.py                    In-house URDF object tree (Robot/Link/Joint/Visual/Geometry/Material/...)
│   ├── gallery.py                   Starter list of real, verified public robot-description repositories
│   ├── inertia_calc.py              Closed-form moment-of-inertia formulas for the primitive geometries
│   ├── i18n.py                      language/*.lng loader, config persistence - ported from HYDRA-UMC-SUITE's own i18n.py
│   ├── urdf/                        parser, writer, DOF and save check
│   ├── render/                      meshes, forward kinematics, OpenGL view
│   ├── source/                      GitHub download and local folders
│   ├── server/                      the client of HYDRA-UMC-SERVER
│   └── ui/                          window, docks, dialogs and theme
├── assets/                          icon, dark theme and the Qt Quick deck
├── images/                          banner and the pictures of the README
├── language/                        english/spanish/italian/french/german/japanese/chinese/portuguese.lng - sits beside the exe, not bundled
├── docs/                            documents of the project
├── tests/                           Real pytest suite (355 tests) - pure logic only, no PySide6 import anywhere here
├── tools/                           project tools and CI checks
├── .github/                         CI workflow and issue templates
├── main.py                          Entry point - QApplication, theme, maximized start, F11 fullscreen toggle; --qtquick switches to the deck below
├── qt_editor_urdf.py                Qt Quick front end - standalone `--qtquick` command deck, bridges the unchanged EditorController to QML
├── run.bat / run.sh                 Convenience wrapper - activates .venv if present, runs main.py, no auto-close
├── requirements.txt                 PySide6, PyOpenGL, numpy-stl, numpy (pinned)
├── requirements-dev.txt             numpy + pytest only - what tests/ actually needs, no PySide6
├── build_exe.bat / build_exe.sh     Windows/Linux standalone-executable build scripts (PyInstaller) - bumps the version first
├── build-test.bat / build-test.sh   Non-versioning build/compile check
├── HYDRA-UMC_EDITOR-URDF.spec       PyInstaller build spec used by build_exe.bat/.sh
├── bump_version.py                  explicit version bump
├── bump_manifest_version.py         Syncs hydra-umc.project.json's version to the native one (--sync)
├── CHANGELOG.md                     Version history
├── LICENSE                          GPL-3.0-or-later
├── hydra-umc.project.json           manifest: version, maturity, family
└── test.sh                          non-mutating build check
```

</details>

## 🗺️ Roadmap & Known limits

xacro macros are not expanded and COLLADA (`.dae`) meshes are not loaded; both give a clear error. A robot must fit 3 to 6 degrees of freedom to be accepted by STUDIO. The server round-trip was tried against a local test server only, not against a real HYDRA-UMC-SERVER. The Qt Quick command deck is a separate `--qtquick` window and not part of the dockable workspace.

## 🌍 Languages

This README and the documents of the repository exist in eight languages: English, Spanish, German, French, Italian, Japanese, Chinese and Portuguese (Portugal). They are written together and checked in the CI so that the eight files have the same sections and the same links.

## 🔗 Related Projects

This project is part of the HYDRA-UMC robotics ecosystem by the same author (JuanenRac / Electro Hobby 3D). Worth knowing about, since a request might actually be about one of these rather than this repository.

**Parent Project**
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — the model catalog this editor exists to populate; the finished result is pushed straight to a running STUDIO server via `POST /api/models/submit`.

**Directly Related**
- **[HYDRA-UMC-EDITOR-STL](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-STL)** — sibling desktop editor for the same model catalog's own raw STL geometry, rather than the URDF/kinematics side this tool edits.
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — owns the real `POST /api/models/submit` endpoint this editor pushes finished models to.
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — consumes the URDF models created here to drive its physics simulation.
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — consumes the URDF models created here to drive its physics simulation.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — generates training data from the models created here.

**Also Part of the Ecosystem**

*Core Hardware & Platform*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — the robot-arm motherboard design: CM5 host + dual-core STM32H745, meant to orchestrate up to 8 tool arms over CAN-OTA/SPI-OTA (firmware at an early stage; no populated board yet).
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — reproducible Raspberry Pi OS product layer for the CM5: read-only agent, validated config/profiles, WiFi first-contact provisioning.
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — the shared JSON-Schema contract and software job-gate boundary every bridge validates its commands against (not a certified safety function).
- **[HYDRA-UMC-CONNECTOR-HUB](https://github.com/JuanenRac/HYDRA-UMC-CONNECTOR-HUB)** — declarative adapter-manifest registry and validator for external-machine connectors; extends the SDK's own contract idea to external machines without replacing the industrial-gateway projects.

*Core Backend & Clients*
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — desktop (PySide6) swarm command center for multiple servers at once, packaged as a standalone executable.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — native Android control app with biometric login and a paired Wear OS companion.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — iOS/iPadOS control app (Flutter) with real-time WebSocket sync.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — native touch UI for the onboard 7" DSI touchscreen, embedded on the CM5 itself.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — coordination boundary for AGV/AMR fleets via a VDA 5050 MQTT publisher (tested against an emulated fleet only).
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — high-level CNC-cell coordinator with GRBL status/control-byte access (tested against an emulator only).
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — coordination boundary for legged/humanoid droids, with a Boston Dynamics Spot command sender (tested against an emulator only).
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — laser-cell coordinator reading 3 key/enclosure/interlock GPIO signals (tested against a fake chip only; it cannot arm or fire a laser).
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — safe high-level board-flow coordinator for OpenPnP pick-and-place.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — safe coordination boundary for Moonraker/Klipper 3D printers, with real gated job commands.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — coordinator with a lazily imported rclpy ROS 2 transport (not yet run against a ROS 2 installation).
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — coordination boundary for camera-equipped UAVs, with a MAVLink command sender (tested against an emulator only).

*URTC Tool Platform*
- **[URTC](https://github.com/JuanenRac/URTC)** — firmware for the physical Universal Robot Tool Controller PCB, 25+ tool profiles over CAN bus.
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — desktop GUI flashing tool for URTC boards, CAN-OTA plus full-chip SWD/JTAG.
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — desktop live CAN-bus diagnostic tool for URTC boards, one panel per tool profile.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — browser-based alternative to URTC-TESTER via the Web Serial API, no local install needed.
- **[URTC-GATEWAY](https://github.com/JuanenRac/URTC-GATEWAY)** — gateway in front of the URTC CAN bus: an allowed list of identifiers, a rate limit and a session key; software tested on a computer, not yet on a real bus.

*Vision AI Node (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — integration hub for the Hailo-8 vision pipeline, with a real per-stage hardware-readiness check.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — real compiled-model registry with Hailo-architecture/checksum safe-load verification.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — real GStreamer pipeline + MediaMTX config generator with a real HailoRT integration boundary.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — Position-Based Visual Servoing correction law with authorisation gated on the zone state; no camera pose estimation yet.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — v0 zone-breach, calibration-freshness and E-STOP-request logic that takes object positions from a file; no detector feeds it and no physical E-STOP is wired to it yet.

*Cognitive AI Node (Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — integration hub for the Hailo-10 cognitive pipeline (LLM/VLA/voice orchestration).
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — real action-token encoding/decoding and trajectory generation for a Vision-Language-Action model.
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — real voice front-end (VAD + intent parser) with a bounded, confirmation-gated Watch relay.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — real rule-based task decomposition and semantic error recovery over MCU error codes.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — real stdlib-only TF-IDF document search over this ecosystem's own Markdown docs.
- **[HYDRA-UMC-LOCAL-TECHNICIAN](https://github.com/JuanenRac/HYDRA-UMC-LOCAL-TECHNICIAN)** — local, policy-gated AI maintenance technician for the ecosystem itself - observes, diagnoses and proposes fixes; the two highest risk levels are deliberately not implemented yet.

*Orchestration & Swarm*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — integration hub with a real gRPC/Protobuf health-report contract and mission state machine.
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — real priority-based job queue with deduplication, over a real HTTP API.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — real gRPC-based fleet health watchdog with retry/backoff and identity-mismatch detection.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — real RRT-based 3D path planner with real obstacle/workspace collision validation.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — real CRDT LWW-Element-Map state sync, property-tested for multi-cell convergence.

*Digital Twin & Simulation*
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — hardware-in-the-loop router with a software collision interlock between simulation and real hardware (tested without real hardware).

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
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — WearOS companion app with haptic alert patterns and a paired-phone voice relay (not yet run on a physical watch).
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — firmware for a board-mounting rack with real tool-ID decoding and Smart Idle pre-heating logic.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — firmware plus a real Python vision companion for a thermal/RGB inspection tool head.
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — administrative desktop tool that discovers, clones and updates every repo in this ecosystem.
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** — Windows/Linux desktop tool that builds a ready-to-flash CM5 image pre-loaded with the ecosystem's most current versions, with Raspberry-Pi-Imager-style first-boot Wi-Fi/user/SSH configuration.
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — maintenance-incident coordinator: a low-privilege edge role collects a sanitized inventory/health snapshot, a control-plane role renders it read-only and asks an AI provider to suggest a diagnosis - never applies a patch or deploys anything.
- **[HYDRA-UMC-DEV-SERVER](https://github.com/JuanenRac/HYDRA-UMC-DEV-SERVER)** — reproducible development host (Raspberry Pi 5 / CM5) that stores the ecosystem's source and runs bounded build/test tasks under a durable queue; a dedicated dev role, explicitly not an operational CM5.

## 📚 Documentation

Where to read more:

* [docs/SOURCE_MAP.md](docs/SOURCE_MAP.md) - every source file of the editor with a line on what it does
* [docs/LICENSING.md](docs/LICENSING.md) - how the code, the documents and the meshes are licensed
* **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — the editor's own internal shape: why parsing, feasibility validation, mesh resolution and 3D preview are separate lanes, and what this app deliberately does *not* do (connect to a robot, upload a URDF, or command motion on its own).
* **[docs/BUILD_AND_RUN.md](docs/BUILD_AND_RUN.md)** — the non-mutating `build-test.bat`/`.sh` validation path versus a real `build_exe.bat`/`.sh` package, plus what the command deck actually is today (`QToolBar`, not Qt Quick/QML - see the **Theme** section above).
* **[docs/INTEGRATION_CONTRACT.md](docs/INTEGRATION_CONTRACT.md)** — what a downstream consumer of an exported URDF file must validate on its own; this project provides no network endpoint or hardware-control authority of its own.
* [Security baseline of the ecosystem](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/SECURITY_BASELINE.md)
* [Threat model of the ecosystem](https://github.com/JuanenRac/HYDRA-UMC-DOCS/blob/main/docs/THREAT_MODEL.md)
* [Changelog of this repository](CHANGELOG.md)
* [License of this repository](LICENSE.md)

## 🤝 Contributing & Community

* Before a pull request run `HYDRA_UMC_CI=1 py -3 tools/ci_validate.py` (or `HYDRA_UMC_CI=1 python3 tools/ci_validate.py`): it must print `CI_VALIDATION=PASS`. Do not run `build.sh` or `build.bat` for this check; building is not a check.
* The eight READMEs are written from one source in HYDRA-UMC-DOCS; do not edit them by hand. Change the source and write them again with `tools/make_readmes.py`.
* Do not state in a README what has not run: say "simulated" or "not tried on hardware" where that is the truth.
* See [CONTRIBUTING.md](CONTRIBUTING.md), the [code of conduct](CODE_OF_CONDUCT.md), [SECURITY.md](SECURITY.md) and [SUPPORT.md](SUPPORT.md).

## 👤 AUTHOR

**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 📜 LICENSE

GPL-3.0-or-later - [LICENSE](LICENSE).
