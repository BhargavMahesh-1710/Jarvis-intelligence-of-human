@echo off
title MAHI JARVIS SERVER
echo ========================================================
echo               MAHI JARVIS AI ASSISTANT
echo ========================================================
echo.
cd /d "%~dp0"

:: Auto-detect Python executable
set "PYTHON_CMD=python"
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
)

echo Launching browser to http://127.0.0.1:8000 ...
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:8000"
echo Starting Backend Server on port 8000 using %PYTHON_CMD%...
echo.
"%PYTHON_CMD%" backend/main.py
pause

