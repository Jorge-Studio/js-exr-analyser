@echo off
title EXR Analyzer - Cinema VFX Diagnostic Tool
cd /d "%~dp0"

echo ============================================
echo   EXR Analyzer - Cinema VFX Diagnostic Tool
echo ============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python 3.8+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install core dependencies first (no build step; works on restricted networks)
echo Installing core dependencies (numpy, PyQt5, OpenCV, etc.)...
pip install -q -r requirements-core.txt
if errorlevel 1 (
    echo.
    echo Core install failed. See OFFLINE INSTALL in README if you have network restrictions.
    echo.
) else (
    echo Core dependencies OK.
)

REM Optional: install OpenEXR for full metadata (often fails on Windows without Visual Studio)
echo Installing optional OpenEXR...
pip install -q OpenEXR>=3.0.0 2>nul
if errorlevel 1 (
    echo OpenEXR skipped or failed - app will use OpenCV for EXR. This is OK.
) else (
    echo OpenEXR installed.
)

echo.
echo Starting EXR Analyzer...
echo.

REM Run the application (app also installs requirements on startup as backup)
python exr_analyzer.py %*
set EXIT_CODE=%errorlevel%

REM If app exited with error, keep window open so user can read the message
if not %EXIT_CODE%==0 (
    echo.
    echo ============================================
    echo   EXR Analyzer exited with error code %EXIT_CODE%
    echo ============================================
    echo.
    echo If a popup appeared, check that message.
    echo A full error log may have been saved to: exr_analyzer_crash.log
    echo.
    echo Run "pip install -r requirements-core.txt" in this folder, or see README "Offline install".
    echo.
    pause
)

deactivate
exit /b %EXIT_CODE%
