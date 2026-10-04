@echo off
cd /d "%~dp0"
title LocalConvert

echo.
echo  ===========================================
echo   LocalConvert - Starting up...
echo  ===========================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo.
    echo  Please download and install Python from:
    echo  https://www.python.org/downloads/
    echo.
    echo  IMPORTANT: During install, check the box that says
    echo  "Add Python to PATH" before clicking Install.
    echo.
    pause
    exit /b 1
)

echo [OK] Python found.

:: Create virtual environment if it doesn't exist
if not exist venv (
    echo [+] First-time setup: creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [+] Installing required packages (this takes 1-2 minutes the first time)...
    call venv\Scripts\pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install packages.
        pause
        exit /b 1
    )
    echo [OK] Setup complete!
)

echo.
echo [OK] Launching LocalConvert at http://127.0.0.1:5000
echo      Close this window to stop the app.
echo.

call venv\Scripts\python app.py

pause
