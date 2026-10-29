# Licensing

How the code, the documents and the third-party assets of this repository are licensed. The short statement is in the License section of the README; this is the full text of it.

HYDRA-UMC EDITOR-URDF is (c) 2026 JuanenRac (Electro Hobby 3D). This notice must be included in any distributions of this project or derivative works.

This project consists of source code and its own documentation, made available under different licenses - each suited to what it actually covers:

1. The source code (`hydra_editor_urdf/`, `main.py`, and any binary built from it via `build_exe.bat`/`build_exe.sh`) is available under the **GNU General Public License v3.0 or later (GPL-3.0-or-later)**. Full text at https://www.gnu.org/licenses/gpl-3.0.html.

2. The documentation (this README and its own translations - `README_spa.md`, `README_ita.md`, `README_fra.md`, `README_deu.md`, `README_zho.md`, `README_jpn.md`, `README_por.md`) is available under **Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)**. Full text at https://creativecommons.org/licenses/by-sa/4.0/.

This app ships no third-party robot mesh assets of its own - unlike HYDRA-UMC STUDIO's `public/models/`, every mesh this editor ever loads comes from whichever source repo or local folder the operator points it at, under that source's own original license. Reviewing and preserving that upstream license/attribution before submitting a model to a running STUDIO server (whose own `public/models/<slug>/ATTRIBUTION.txt` convention this editor's export feeds into) remains the operator's own responsibility - this app has no way to detect or enforce a source repo's licensing terms automatically.

This editor is the model-authoring tool for the [HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO) catalog - see that repository for its own server-side licensing, which this repository's own license doesn't extend to, and vice versa.

If you build on this project, keep the licensing split in mind: code changes here should stay GPL-3.0-or-later, documentation derivatives (this README and its translations) should stay CC BY-SA 4.0, and any mesh asset that passes through this editor (imported, edited, or exported) should stay under whatever license its own original source repo carries, with attribution back to that source.
