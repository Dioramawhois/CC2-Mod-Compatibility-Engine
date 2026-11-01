@echo off
setlocal
REM Developer build. --no-pause is intended for automation.
pushd "%~dp0" || exit /b 1
call :build
set "BUILD_RESULT=%errorlevel%"
if not "%BUILD_RESULT%"=="0" echo Build failed. See the error above.
popd
if /I not "%~1"=="--no-pause" pause
exit /b %BUILD_RESULT%

:build
REM Prefer Python on PATH; also support the standard Windows Python launcher.
set "BUILD_PYTHON=python"
python -c "import sys; sys.exit(sys.version_info < (3, 12))" >nul 2>&1
if errorlevel 1 (
    py -3 -c "import sys; sys.exit(sys.version_info < (3, 12))" >nul 2>&1
    if errorlevel 1 (
        echo Python 3.12 or newer is required on the developer build machine.
        exit /b 1
    )
    set "BUILD_PYTHON=py -3"
)
if not exist .build-venv\Scripts\python.exe (
    %BUILD_PYTHON% -m venv .build-venv || exit /b 1
)
.build-venv\Scripts\python.exe -c "import sys; sys.exit(sys.version_info < (3, 12))" || exit /b 1
.build-venv\Scripts\python.exe -m pip install --upgrade pip "pyinstaller==6.22.3" || exit /b 1
.build-venv\Scripts\python.exe -m pip install -e .[dev] || exit /b 1
if not exist cc2_mce\tools_data\manifest.json (
    .build-venv\Scripts\python.exe tools\prepare_windows_tools.py || exit /b 1
)
.build-venv\Scripts\python.exe -m pytest -q --junitxml=build/test-results.xml || exit /b 1
.build-venv\Scripts\python.exe -m PyInstaller --noconfirm --clean CC2ModLoader-0.1.0.spec || exit /b 1
.build-venv\Scripts\python.exe tools\check_windows_bundle.py || exit /b 1
echo Built: dist\CC2Engine.exe
exit /b 0
