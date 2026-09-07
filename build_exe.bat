@echo off
REM HYDRA_UMC_SCRIPT_STANDARD_HEADER_BEGIN
REM *****************************************************************************
REM Project   : HYDRA-UMC-EDITOR-URDF
REM Script    : build_exe.bat
REM Purpose   : Incremental standalone executable build and packaging workflow.
REM Author    : JuanenRac (Electro Hobby 3D)
REM Email     : electrohobby3d@gmail.com
REM Copyright : (C) 2026 JuanenRac
REM License   : GPL-3.0 - see LICENSE
REM *****************************************************************************
REM HYDRA_UMC_SCRIPT_STANDARD_HEADER_END
REM HYDRA_UMC_SCRIPT_STANDARD_BANNER_BEGIN
echo.
echo *****************************************************************************
echo * HYDRA-UMC-EDITOR-URDF - build_exe.bat
echo * Mode      : INCREMENTAL BUILD
echo * Author    : JuanenRac (Electro Hobby 3D)
echo * Email     : electrohobby3d@gmail.com
echo * Copyright : (C) 2026 JuanenRac
echo * License   : GPL-3.0 - see LICENSE
echo * ------------------------------------------------------------------------- *
echo * 1. Increment the project version and synchronise its manifest.
echo * 2. Run this project's declared build, verification and packaging commands.
echo * 3. Report the result and keep an interactive terminal open.
echo *****************************************************************************
echo.
REM HYDRA_UMC_SCRIPT_STANDARD_BANNER_END
setlocal EnableDelayedExpansion
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
REM HYDRA_UMC_SCRIPT_STANDARD_VERSION_STEP
echo [1/6] Incrementing project version and synchronising its manifest...
python bump_version.py
if errorlevel 1 ( echo NATIVE VERSION BUMP FAILED. & pause & exit /b 1 )
REM HYDRA_UMC_SCRIPT_STANDARD_VERSION_CAPTURE_BEFORE
for /f "usebackq delims=" %%V in (`python -c "import json; print(json.load(open(r'%~dp0hydra-umc.project.json', encoding='utf-8'))['version'])"`) do set "HYDRA_UMC_VERSION_BEFORE=%%V"
python "%~dp0bump_manifest_version.py" --sync
if errorlevel 1 ( echo VERSION SYNCHRONIZATION FAILED. & pause & exit /b 1 )
if errorlevel 1 (
    echo       ERROR: bump_version.py failed - see the output above.
    pause
    exit /b 1
)
REM HYDRA_UMC_SCRIPT_STANDARD_VERSION_CAPTURE_AFTER
for /f "usebackq delims=" %%V in (`python -c "import json; print(json.load(open(r'%~dp0hydra-umc.project.json', encoding='utf-8'))['version'])"`) do set "HYDRA_UMC_VERSION_AFTER=%%V"
if not defined HYDRA_UMC_VERSION_BEFORE set "HYDRA_UMC_VERSION_BEFORE=unknown"
if not defined HYDRA_UMC_VERSION_AFTER set "HYDRA_UMC_VERSION_AFTER=unknown"
echo.
echo *****************************************************************************
echo * VERSION INCREMENT COMPLETED
echo * v%HYDRA_UMC_VERSION_BEFORE% ^> v%HYDRA_UMC_VERSION_AFTER%
echo * Project manifest has been synchronised by the project build flow.
echo *****************************************************************************
echo.
echo.
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
    --hidden-import PySide6.QtQml ^
    --hidden-import PySide6.QtQuick ^
    --hidden-import PySide6.QtQuickWidgets ^
    --collect-all PySide6.QtQuick ^
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
