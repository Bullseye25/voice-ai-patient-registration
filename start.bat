@echo off
setlocal
cd /d "%~dp0"
title CareCloud Voice AI Agent - Patient Registration System
color 0A

echo =========================================================================
echo       CareCloud Voice AI Agent - Patient Registration System
echo       Lead Developer: Ammad Raza
echo =========================================================================
echo.

if exist ".venv\Scripts\python.exe" (
    echo [INFO] Starting CareCloud Voice AI System via virtual environment...
    echo.
    ".venv\Scripts\python.exe" -u run_live.py
) else (
    echo [INFO] Starting CareCloud Voice AI System via system Python...
    echo.
    python -u run_live.py
)

echo.
pause
