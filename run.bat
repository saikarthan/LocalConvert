@echo off
setlocal enabledelayedexpansion
title LocalConvert

cd /d "%~dp0"

echo.
echo ===================================================
echo   LocalConvert - Privacy-First Local File Toolbox
echo ===================================================
echo.

:: Try 'python' first, then 'py'
where python >nul 2>&1
if %errorlevel% equ 0 (
    set PY_CMD=python
) else (
    where py >nul 2>&1
    if %errorlevel% equ 0 (
        set PY_CMD=py
    ) else (
        echo [ERROR] Python was not found on your system!
        echo.
        echo Please download and install Python from:
        echo https://www.python.org/downloads/
        echo.
        echo IMPORTANT: Check the box "Add Python to PATH" during installation.
        echo.
        pause
        exit /b 1
    )
)

echo [OK] Using Python command: %PY_CMD%

:: Check if virtual environment exists, if not create it
if not exist "venv\Scripts\python.exe" (
    echo [+] Setting up local environment (one-time setup)...
    %PY_CMD% -m venv venv
    if not exist "venv\Scripts\python.exe" (
        echo [!] Virtual environment creation failed. Falling back to system Python...
        set PY_EXE=%PY_CMD%
    ) else (
        set PY_EXE=venv\Scripts\python.exe
    )
) else (
    set PY_EXE=venv\Scripts\python.exe
)

echo [+] Starting LocalConvert on http://127.0.0.1:5001 ...
echo [!] Keep this window open while using LocalConvert.
echo.

"%PY_EXE%" app.py

if %errorlevel% neq 0 (
    echo.
    echo [!] LocalConvert stopped with an error code (%errorlevel%).
)

echo.
echo Press any key to close this window.
pause >nul
