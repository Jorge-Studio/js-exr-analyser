@echo off
title EXR Analyzer - Prepare offline install
cd /d "%~dp0"

echo ============================================
echo   EXR Analyzer - Prepare offline install
echo ============================================
echo.
echo This script downloads all core dependencies into a "wheels" folder.
echo Run it on a PC that HAS internet, then copy the project (including
echo "wheels") to the restricted PC and install with:
echo   pip install --no-index --find-links=wheels -r requirements-core.txt
echo.

if not exist "requirements-core.txt" (
    echo ERROR: requirements-core.txt not found.
    pause
    exit /b 1
)

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.11 or 3.12 and try again.
    pause
    exit /b 1
)

if not exist "wheels" mkdir wheels
echo Downloading packages into wheels\...
python -m pip download -r requirements-core.txt -d wheels
if errorlevel 1 (
    echo.
    echo Download failed. Check your internet connection.
    pause
    exit /b 1
)

echo.
echo Done. Copy this entire folder (including "wheels") to the target PC.
echo On the target PC, in this folder, run:
echo   venv\Scripts\activate
echo   pip install --no-index --find-links=wheels -r requirements-core.txt
echo   python exr_analyzer.py
echo.
pause
