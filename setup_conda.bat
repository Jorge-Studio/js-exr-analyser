@echo off
title EXR Analyzer - Setup Conda Environment
cd /d "%~dp0"

echo ============================================
echo   EXR Analyzer - Setup with Miniconda
echo   (No admin required - uses conda binaries)
echo ============================================
echo.

REM Find conda - try common Miniconda/Anaconda locations
set "CONDA_EXE="
if defined CONDA_EXE (
    set "CONDA_EXE=%CONDA_EXE%"
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
    if errorlevel 1 (
        echo ERROR: Miniconda/Anaconda not found.
        echo.
        echo Install Miniconda from https://docs.conda.io/en/latest/miniconda.html
        echo Then either:
        echo   1. Run this script from "Anaconda Prompt" or "Miniconda Prompt"
        echo   2. Or ensure conda is in your PATH
        echo.
        pause
        exit /b 1
    )
    set "CONDA_EXE=conda"
)

echo Using conda: %CONDA_EXE%
echo.

REM Initialize conda for this script if using conda.bat
if "%CONDA_EXE%"=="conda" (
    call conda activate base 2>nul
)

echo Creating conda environment "exr-analyzer" with all dependencies...
echo This will install OpenEXR, PyQt5, OpenCV, etc. from conda-forge (pre-built).
echo.

"%CONDA_EXE%" env create -f environment.yml
if errorlevel 1 (
    echo.
    echo If the env already exists, run: conda env update -f environment.yml
    echo Or remove it first: conda env remove -n exr-analyzer
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Setup complete.
echo   Run: run_conda.bat
echo   Or: conda activate exr-analyzer ^&^& python exr_analyzer.py
echo ============================================
echo.
pause
