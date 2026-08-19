#!/usr/bin/env bash
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

echo
echo " ==============================================================="
echo "  H Y D R A - U M C   E D I T O R - U R D F  -  Linux build"
echo " ==============================================================="
echo "  Graphical URDF creator/editor for HYDRA-UMC-STUDIO's catalog"
echo "  Author:  JuanenRac (Electro Hobby 3D)"
echo "  E-mail:  electrohobby3d@gmail.com"
echo "  License: GPL-3.0 (see LICENSE)"
echo " ==============================================================="
echo

echo "[1/6] Checking for system Qt/OpenGL runtime libraries..."
if ! python3 -c "import ctypes; ctypes.CDLL('libGL.so.1')" 2>/dev/null; then
    echo "      libGL.so.1 not found."
    echo "      On Debian/Ubuntu:  sudo apt install libgl1 libxkbcommon-x11-0 libxcb-cursor0"
    echo "      On Fedora:         sudo dnf install mesa-libGL libxkbcommon-x11 xcb-util-cursor"
    echo "      On Arch:           sudo pacman -S libglvnd libxkbcommon-x11 xcb-util-cursor"
    exit 1
fi
echo "      Found."
echo

echo "[2/6] Creating/activating virtual environment..."
if [ ! -d .venv ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
echo "      Done."
echo

echo "[3/6] Installing Python dependencies..."
python3 -m pip install --upgrade pip >/dev/null
python3 -m pip install -r requirements.txt
python3 -m pip install pyinstaller
echo "      Done."
echo

echo "[4/6] Cleaning previous build..."
rm -rf build dist
echo "      Done."
echo

echo "[5/6] Compiling HYDRA-UMC_EDITOR-URDF with PyInstaller..."
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

echo "[6/6] Copying files that must sit next to the binary, not inside it..."
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
