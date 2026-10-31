@echo off
REM Build CC2 Mod Loader 0.1.0 as a single Windows executable.
REM Run on Windows only: PyInstaller produces an .exe for the OS it runs on.
REM Requires Python 3.11+ on the build machine (not needed by players).
python -m pip install --upgrade pyinstaller || exit /b 1
python -m PyInstaller --noconfirm --onefile --windowed --name "CC2ModLoader-0.1.0" ^
    --paths . --hidden-import tkinter cc2_mce\gui.py || exit /b 1
echo Built: dist\CC2ModLoader-0.1.0.exe
