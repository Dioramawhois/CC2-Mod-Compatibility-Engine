@echo off
REM Build CC2 Mod Loader 0.1.0 as one Windows executable. Run on Windows only.
REM Needs Python 3.12+ on the build machine (players do not need Python).
REM Installs the project itself so its dependencies (jsonschema) are present in the bundle.
python -m venv .build-venv || exit /b 1
.build-venv\Scripts\python.exe -m pip install --upgrade pip pyinstaller || exit /b 1
.build-venv\Scripts\python.exe -m pip install -e . || exit /b 1
.build-venv\Scripts\python.exe -m pytest -q || exit /b 1
.build-venv\Scripts\python.exe -m PyInstaller --noconfirm --onefile --windowed ^
    --name "CC2ModLoader-0.1.0" --paths . --collect-all jsonschema ^
    cc2_mce\gui.py || exit /b 1
echo Built: dist\CC2ModLoader-0.1.0.exe
