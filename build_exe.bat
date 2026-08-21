@echo off
setlocal EnableDelayedExpansion
REM Builds a standalone Windows .exe for HYDRA-UMC EDITOR-URDF.
REM Run this on a Windows machine with Python installed.
REM
REM Usage:
REM   build_exe.bat
REM
REM Output: dist\HYDRA-UMC_EDITOR-URDF.exe (no Python installation needed to run it)
REM
REM Structurally a port of HYDRA-UMC-SUITE's own build_exe.bat (this
REM project's sibling, same PySide6/PyInstaller toolchain) - per
REM [[No reference -> reuse, don't invent]]. The one real difference:
REM this app has no qasync/websockets dependency (see main.py's own
REM header for why), so those 2 --hidden-import flags are dropped below.

echo.
echo  ===============================================================
echo   H Y D R A - U M C   E D I T O R - U R D F  -  Windows build
echo  ===============================================================
echo   Graphical URDF creator/editor for HYDRA-UMC-STUDIO's catalog
echo   Author:  JuanenRac (Electro Hobby 3D)
echo   E-mail:  electrohobby3d@gmail.com
echo   License: GPL-3.0 (see LICENSE)
echo  ===============================================================
echo.

echo [1/6] Creating/activating virtual environment...
if not exist .venv (
    python -m venv .venv
)
call .venv\Scripts\activate.bat
echo       Done.
echo.

echo [2/6] Installing Python dependencies...
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt
python -m pip install pyinstaller
echo       Done.
echo.

echo [3/6] Cleaning previous build...
if exist build rmdir /s /q build
if exist dist (
    rmdir /s /q dist
    if exist dist (
        echo       ERROR: couldn't remove dist\ - is HYDRA-UMC_EDITOR-URDF.exe currently running?
        echo       Close it first, then run this script again.
        pause
        exit /b 1
    )
)
echo       Done.
echo.

echo [4/6] Bumping version number...
REM Odometer-style bump (see bump_version.py): PATCH+1 per real build,
REM carrying into MINOR past 9 (e.g. 1.0.9 -> 1.1.0). This happens for
REM EVERY real packaged build, unconditionally - if you're iterating on
REM this script without wanting a version bump each time, run the actual
REM PyInstaller command by hand instead of through this script.
python bump_version.py
if errorlevel 1 (
    echo       ERROR: bump_version.py failed - see the output above.
    pause
    exit /b 1
)
echo       Done.
echo.

echo [5/6] Compiling HYDRA-UMC_EDITOR-URDF.exe with PyInstaller...
REM See HYDRA-UMC-SUITE's own build_exe.bat for the full reasoning behind
REM staging only these 4 Qt plugin subfolders instead of --collect-all
REM PySide6 (a ~3x smaller .exe for the same working result).
if not defined PYSIDE_DIR (
    for /f "delims=" %%P in ('python -c "import PySide6, os; print(os.path.dirname(PySide6.__file__))"') do set PYSIDE_DIR=%%P
)
python -m PyInstaller --onefile --windowed --noconfirm --name "HYDRA-UMC_EDITOR-URDF" ^
    --add-data "assets;assets" ^
    --add-data "%PYSIDE_DIR%\plugins\platforms;PySide6\plugins\platforms" ^
    --add-data "%PYSIDE_DIR%\plugins\styles;PySide6\plugins\styles" ^
    --add-data "%PYSIDE_DIR%\plugins\imageformats;PySide6\plugins\imageformats" ^
    --add-data "%PYSIDE_DIR%\plugins\iconengines;PySide6\plugins\iconengines" ^
    --hidden-import PySide6.QtOpenGL ^
    --hidden-import PySide6.QtOpenGLWidgets ^
    --hidden-import OpenGL.platform.win32 ^
    main.py
if not exist dist\HYDRA-UMC_EDITOR-URDF.exe (
    echo       ERROR: PyInstaller did not produce dist\HYDRA-UMC_EDITOR-URDF.exe - see the output above.
    pause
    exit /b 1
)
echo       Done.
echo.

echo [6/6] Copying files that must sit next to the .exe, not inside it...
if exist README.md (
    copy /Y README.md dist\README.md >nul
    echo       Copied README.md into dist\
)
if exist LICENSE (
    copy /Y LICENSE dist\LICENSE >nul
    echo       Copied LICENSE into dist\
)
REM language\ sits NEXT TO the .exe, not bundled inside via --add-data -
REM i18n.py's own LANGUAGE_FOLDER resolves via sys.executable's own
REM directory for a frozen build, and this also lets a translator edit/
REM add a .lng file after the fact with no rebuild needed.
if exist language (
    xcopy /E /I /Y language dist\language >nul
    echo       Copied language\ into dist\language\
)
echo       Done.
echo.

echo  ===============================================================
echo   dist\HYDRA-UMC_EDITOR-URDF.exe is ready to run - no Python needed.
echo  ===============================================================
echo.
pause
