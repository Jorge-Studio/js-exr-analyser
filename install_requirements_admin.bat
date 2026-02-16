@echo off
title EXR Analyzer - Install Requirements (Admin)
cd /d "%~dp0"

REM Check if already running as administrator
net session >nul 2>&1
if %errorLevel% == 0 goto :install

REM Request administrator privileges (UAC prompt - user enters password)
echo Requesting administrator privileges...
echo A UAC window will appear - approve it to install OpenEXR and all requirements.
echo.
powershell -Command "Start-Process -FilePath 'cmd.exe' -ArgumentList '/c cd /d \"%~dp0\" && \"%~f0\"' -Verb RunAs -Wait"
exit /b %errorLevel%

:install
cd /d "%~dp0"

echo ============================================
echo   EXR Analyzer - Install Requirements (Admin)
echo ============================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo Install Python 3.8+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Create venv if needed
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate.bat

echo Installing all requirements including OpenEXR...
echo.
pip install -r requirements.txt
set PIP_ERR=%errorlevel%

if %PIP_ERR%==0 (
    echo.
    echo ============================================
    echo   Installation complete.
    echo   OpenEXR and all dependencies installed.
    echo ============================================
) else (
    echo.
    echo Installation had errors. OpenEXR may require Visual Studio build tools on Windows.
    echo The app will still run using OpenCV for EXR files.
)

echo.
pause
deactivate
exit /b %PIP_ERR%
