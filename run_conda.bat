@echo off
title EXR Analyzer - Cinema VFX Diagnostic Tool
cd /d "%~dp0"

REM Find conda
set "CONDA_EXE="
if defined CONDA_EXE (
) else if exist "%USERPROFILE%\miniconda3\Scripts\conda.exe" (
    set "CONDA_EXE=%USERPROFILE%\miniconda3\Scripts\conda.exe"
) else if exist "%USERPROFILE%\miniconda3\condabin\conda.bat" (
    set "CONDA_EXE=%USERPROFILE%\miniconda3\condabin\conda.bat"
) else if exist "%LOCALAPPDATA%\miniconda3\Scripts\conda.exe" (
    set "CONDA_EXE=%LOCALAPPDATA%\miniconda3\Scripts\conda.exe"
) else if exist "C:\ProgramData\miniconda3\Scripts\conda.exe" (
    set "CONDA_EXE=C:\ProgramData\miniconda3\Scripts\conda.exe"
) else if exist "C:\ProgramData\anaconda3\Scripts\conda.exe" (
    set "CONDA_EXE=C:\ProgramData\anaconda3\Scripts\conda.exe"
) else (
    where conda >nul 2>&1
    if not errorlevel 1 set "CONDA_EXE=conda"
)

if "%CONDA_EXE%"=="" (
    echo ERROR: Miniconda not found. Run setup_conda.bat first or install Miniconda.
    pause
    exit /b 1
)

REM Check if exr-analyzer env exists
"%CONDA_EXE%" env list | findstr /b "exr-analyzer " >nul 2>&1
if errorlevel 1 (
    echo Environment "exr-analyzer" not found. Run setup_conda.bat first.
    pause
    exit /b 1
)

echo Starting EXR Analyzer...
"%CONDA_EXE%" run -n exr-analyzer python exr_analyzer.py %*
set EXIT_CODE=%errorlevel%

if not %EXIT_CODE%==0 (
    echo.
    echo App exited with error. Run setup_conda.bat if dependencies are missing.
    pause
)
exit /b %EXIT_CODE%
