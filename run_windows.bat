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

REM Install/update all dependencies (required versions from requirements.txt)
echo Installing dependencies...
pip install --upgrade pip -q
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo WARNING: Some dependencies may have failed. Check your internet connection.
    echo Trying to start the app anyway...
    echo.
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
    echo The application exited with an error. See message above.
    pause
)

deactivate
exit /b %EXIT_CODE%
