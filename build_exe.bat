@echo off
REM HYDRA_UMC_SCRIPT_STANDARD_HEADER_BEGIN
REM *****************************************************************************
REM Project   : HYDRA-UMC-EDITOR-URDF
REM Script    : build_exe.bat
REM Purpose   : Incremental standalone executable build and packaging workflow.
REM Author    : JuanenRac (Electro Hobby 3D)
REM Email     : electrohobby3d@gmail.com
REM Copyright : (C) 2026 JuanenRac
REM License   : GPL-3.0-or-later - see LICENSE
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
echo * License   : GPL-3.0-or-later - see LICENSE
echo * ------------------------------------------------------------------------- *
echo * 1. Read the project version (building never changes it; use the explicit bump command).
echo * 2. Run this project's declared build, verification and packaging commands.
echo * 3. Report the result and keep an interactive terminal open.
echo *****************************************************************************
echo.
REM HYDRA_UMC_SCRIPT_STANDARD_BANNER_END
setlocal EnableDelayedExpansion
rem Keep the window open for people, never in automation (CI / HYDRA_UMC_CI).
set "KEEP_OPEN=pause"
if defined CI set "KEEP_OPEN=ver >nul"
if "%HYDRA_UMC_CI%"=="1" set "KEEP_OPEN=ver >nul"
REM The venv is made with the py launcher when there is one (the python that is first on the PATH may be a stripped one, for example the one of ESP-IDF, whose
REM venv has no activate script), and the scripts use the python of the venv directly instead of activating it.
set "PYMAKE=python"
where py >nul 2>nul && set "PYMAKE=py -3"
if not exist .venv\Scripts\python.exe (
    %PYMAKE% -m venv .venv
    if errorlevel 1 goto :error
)
if not exist .venv\Scripts\python.exe (
    echo ERROR: .venv has no python.exe; delete the .venv folder and run this again.
    goto :error
)
set "VPY=%CD%\.venv\Scripts\python.exe"
echo       Done.
echo.

echo [2/6] Installing Python dependencies...
"%VPY%" -m pip install --upgrade pip >nul
"%VPY%" -m pip install -r requirements.txt
"%VPY%" -m pip install pyinstaller
echo       Done.
echo.

echo [3/6] Cleaning previous build...
if exist build rmdir /s /q build
if exist dist (
    rmdir /s /q dist
    if exist dist (
        echo       ERROR: couldn't remove dist\ - is HYDRA-UMC_EDITOR-URDF.exe currently running?
        echo       Close it first, then run this script again.
        %KEEP_OPEN%
        exit /b 1
    )
)
echo       Done.
echo.

REM HYDRA_UMC_SCRIPT_STANDARD_VERSION_STEP
echo [4/6] Reading the project version (building never changes it)...
for /f "usebackq delims=" %%V in (`python -c "import json; print(json.load(open(r'%~dp0hydra-umc.project.json', encoding='utf-8'))['version'])"`) do set "HYDRA_UMC_VERSION_BUILT=%%V"
if not defined HYDRA_UMC_VERSION_BUILT set "HYDRA_UMC_VERSION_BUILT=unknown"
echo       Building v%HYDRA_UMC_VERSION_BUILT% (building never changes the version)
echo.
echo.
echo       Done.
echo.

echo [5/6] Compiling HYDRA-UMC_EDITOR-URDF.exe with PyInstaller...
REM See HYDRA-UMC-SUITE's own build_exe.bat for the full reasoning behind
REM staging only these 4 Qt plugin subfolders instead of --collect-all
REM PySide6 (a ~3x smaller .exe for the same working result).
if not defined PYSIDE_DIR (
    for /f "delims=" %%P in ('""%VPY%" -c "import PySide6, os; print(os.path.dirname(PySide6.__file__))""') do set PYSIDE_DIR=%%P
)
"%VPY%" -m PyInstaller --onefile --windowed --noconfirm --name "HYDRA-UMC_EDITOR-URDF" ^
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
    %KEEP_OPEN%
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
echo Built v%HYDRA_UMC_VERSION_BUILT%. Building never changes the version; to raise it run: python tools\hydra_project_tool.py bump
echo.
%KEEP_OPEN%
