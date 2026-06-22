@echo off
title BestBrand AI Agent Launcher
color 0A
echo.
echo  ╔══════════════════════════════════════════╗
echo  ║        BestBrand AI Agent — USB          ║
echo  ║     Offline AI · No Internet Needed      ║
echo  ╚══════════════════════════════════════════╝
echo.

:: Check if Ollama is installed
where ollama >nul 2>&1
if %errorlevel% neq 0 (
    echo  [!] Ollama is not installed.
    echo.
    echo  Please install Ollama first:
    echo  → https://ollama.com/download
    echo.
    echo  After installing, run this script again.
    pause
    start https://ollama.com/download
    exit /b 1
)

:: Start Ollama if not running
tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I /N "ollama.exe" >NUL
if %errorlevel% neq 0 (
    echo  [*] Starting Ollama...
    start /min "" ollama serve
    timeout /t 3 /nobreak >nul
)

:: Check if a model is installed
for /f "tokens=*" %%i in ('ollama list 2^>^&1') do (
    set MODELS=%%i
)

:: Launch the app
echo  [*] Launching BestBrand AI Agent...
echo.

:: Look for portable exe in same directory
if exist "%~dp0BestBrand-AI-Agent-Portable.exe" (
    start "" "%~dp0BestBrand-AI-Agent-Portable.exe"
    echo  [✓] App launched!
) else if exist "%~dp0app\BestBrand AI Agent.exe" (
    start "" "%~dp0app\BestBrand AI Agent.exe"
    echo  [✓] App launched!
) else (
    echo  [!] Could not find the app executable.
    echo      Make sure BestBrand-AI-Agent-Portable.exe is in this folder.
    pause
)
