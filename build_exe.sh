#!/usr/bin/env bash
# HYDRA_UMC_SCRIPT_STANDARD_HEADER_BEGIN
# *****************************************************************************
# Project   : HYDRA-UMC-EDITOR-URDF
# Script    : build_exe.sh
# Purpose   : Incremental standalone executable build and packaging workflow.
# Author    : JuanenRac (Electro Hobby 3D)
# Email     : electrohobby3d@gmail.com
# Copyright : (C) 2026 JuanenRac
# License   : GPL-3.0 - see LICENSE
# *****************************************************************************
# HYDRA_UMC_SCRIPT_STANDARD_HEADER_END
# HYDRA_UMC_SCRIPT_STANDARD_BANNER_BEGIN
printf '\n*******************************************************************************\n'
printf '%s\n' "* HYDRA-UMC-EDITOR-URDF - build_exe.sh"
printf '%s\n' "* Mode      : INCREMENTAL BUILD"
printf '%s\n' "* Author    : JuanenRac (Electro Hobby 3D)"
printf '%s\n' "* Email     : electrohobby3d@gmail.com"
printf '%s\n' "* Copyright : (C) 2026 JuanenRac"
printf '%s\n' "* License   : GPL-3.0 - see LICENSE"
printf '%s\n' "* ------------------------------------------------------------------------- *"
printf '%s\n' "* 1. Increment the project version and synchronise its manifest."
printf '%s\n' "* 2. Run this project's declared build, verification and packaging commands."
printf '%s\n' "* 3. Report the result and keep an interactive terminal open."
printf '%s\n' "*******************************************************************************"
printf '\n'
# HYDRA_UMC_SCRIPT_STANDARD_BANNER_END
# Builds a standalone Linux binary for HYDRA-UMC EDITOR-URDF.
# Run this on the Linux machine you actually want to run it on - PyInstaller
# builds a binary for whatever OS it runs on, not a cross-compile.
#
# Usage:
#   chmod +x build_exe.sh   (one-time)
#   ./build_exe.sh
#
# Output: dist/HYDRA-UMC_EDITOR-URDF (no Python installation needed to run it)
#
# Structurally a port of HYDRA-UMC-SUITE's own build_exe.sh (this
# project's sibling) - per [[No reference -> reuse, don't invent]]. The
# one real difference: no qasync/websockets dependency here (see main.py's
# own header), so those --hidden-import flags are dropped below.
set -euo pipefail

# Keeps the terminal window open until the user presses Enter, on BOTH the
# success path and every error path - including a command that aborts the
# whole script via `set -e` above (not just the explicit `exit 1` calls
# below). A trap on EXIT fires no matter how/where the script exits, so
# this one line covers every exit point without needing a duplicate
# read -p next to each individual error check.
trap 'read -p "Pulsa Enter para cerrar / Press Enter to close..." _ || true' EXIT
if ! python3 -c "import ctypes; ctypes.CDLL('libGL.so.1')" 2>/dev/null; then
    echo "      libGL.so.1 not found."
    echo "      On Debian/Ubuntu:  sudo apt install libgl1 libxkbcommon-x11-0 libxcb-cursor0"
    echo "      On Fedora:         sudo dnf install mesa-libGL libxkbcommon-x11 xcb-util-cursor"
    echo "      On Arch:           sudo pacman -S libglvnd libxkbcommon-x11 xcb-util-cursor"
    exit 1
fi
echo "      Found."
echo

echo "[2/7] Creating/activating virtual environment..."
if [ ! -d .venv ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
echo "      Done."
echo

echo "[3/7] Installing Python dependencies..."
python3 -m pip install --upgrade pip >/dev/null
python3 -m pip install -r requirements.txt
python3 -m pip install pyinstaller
echo "      Done."
echo

echo "[4/7] Cleaning previous build..."
rm -rf build dist
echo "      Done."
echo

echo "[5/7] Bumping version number..."
# Odometer-style bump (see bump_version.py): PATCH+1 per real build,
# carrying into MINOR past 9 (e.g. 1.0.9 -> 1.1.0). Runs for EVERY real
# packaged build, unconditionally - if you're iterating on this script
# without wanting a version bump each time, run the actual PyInstaller
# command by hand instead of through this script. `set -e` above already
# aborts (and the trap above still pauses) if this fails.
# HYDRA_UMC_SCRIPT_STANDARD_VERSION_STEP
printf '%s\n' "[1/7] Incrementing project version and synchronising its manifest..."
python3 bump_version.py || exit 1
# HYDRA_UMC_SCRIPT_STANDARD_VERSION_CAPTURE_BEFORE
HYDRA_UMC_VERSION_BEFORE="$(python3 -c 'import json, pathlib, sys; print(json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))["version"])' "$(dirname "$0")/hydra-umc.project.json")"
python3 "$(dirname "$0")/bump_manifest_version.py" --sync || exit 1
# HYDRA_UMC_SCRIPT_STANDARD_VERSION_CAPTURE_AFTER
HYDRA_UMC_VERSION_AFTER="$(python3 -c 'import json, pathlib, sys; print(json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))["version"])' "$(dirname "$0")/hydra-umc.project.json")"
printf '\n*******************************************************************************\n'
printf '%s\n' '* VERSION INCREMENT COMPLETED'
printf '%s\n' "* v${HYDRA_UMC_VERSION_BEFORE:-unknown} -> v${HYDRA_UMC_VERSION_AFTER:-unknown}"
printf '%s\n' '* Project manifest has been synchronised by the project build flow.'
printf '%s\n' '*******************************************************************************'
printf '\n'
echo "      Done."
echo

echo "[6/7] Compiling HYDRA-UMC_EDITOR-URDF with PyInstaller..."
# See HYDRA-UMC-SUITE's own build_exe.sh for the full reasoning behind
# staging only these 4 Qt plugin subfolders instead of --collect-all
# PySide6 (a ~3x smaller binary for the same working result), and for
# the Qt/plugins/ (not plain plugins/) path PySide6 uses on Linux.
PYSIDE_DIR=$(python3 -c "import PySide6, os; print(os.path.dirname(PySide6.__file__))")
python3 -m PyInstaller --onefile --noconfirm --name "HYDRA-UMC_EDITOR-URDF" \
    --add-data "assets:assets" \
    --add-data "$PYSIDE_DIR/Qt/plugins/platforms:PySide6/Qt/plugins/platforms" \
    --add-data "$PYSIDE_DIR/Qt/plugins/styles:PySide6/Qt/plugins/styles" \
    --add-data "$PYSIDE_DIR/Qt/plugins/imageformats:PySide6/Qt/plugins/imageformats" \
    --add-data "$PYSIDE_DIR/Qt/plugins/iconengines:PySide6/Qt/plugins/iconengines" \
    --hidden-import PySide6.QtOpenGL \
    --hidden-import PySide6.QtOpenGLWidgets \
    main.py
if [ ! -f dist/HYDRA-UMC_EDITOR-URDF ]; then
    echo "      ERROR: PyInstaller did not produce dist/HYDRA-UMC_EDITOR-URDF - see the output above."
    exit 1
fi
echo "      Done."
echo

echo "[7/7] Copying files that must sit next to the binary, not inside it..."
if [ -f README.md ]; then
    cp README.md dist/README.md
    echo "      Copied README.md into dist/"
fi
if [ -f LICENSE ]; then
    cp LICENSE dist/LICENSE
    echo "      Copied LICENSE into dist/"
fi
if [ -d language ]; then
    mkdir -p dist/language
    cp -r language/. dist/language/
    echo "      Copied language/ into dist/language/"
fi
echo "      Done."
echo

echo " ==============================================================="
echo "  Build complete: dist/HYDRA-UMC_EDITOR-URDF is ready to run - no Python needed."
echo "  (chmod +x dist/HYDRA-UMC_EDITOR-URDF if it isn't already executable)"
echo " ==============================================================="
echo
