@echo off
title CareCloud Voice AI Agent - Patient Registration System
color 0A

echo =========================================================================
echo       CareCloud Voice AI Agent - Patient Registration System
echo       Lead Developer & Author: Ammad Raza
echo =========================================================================
echo.

:: Check for virtual environment
if exist ".venv\Scripts\activate.bat" (
    echo Activating virtual environment (.venv)...
    call .venv\Scripts\activate.bat
) else (
    echo [WARNING] .venv not found. Using system Python...
)

echo Starting Live Backend, Public Tunnel (carecloud-voice-ai.loca.lt), and Voice Agent...
python run_live.py

pause
