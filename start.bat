@echo off
title Vocal Assessment

:: Find conda
set "CONDA_BASE=C:\Users\jack\anaconda3"
if not exist "%CONDA_BASE%\Scripts\activate.bat" (
    set "CONDA_BASE=C:\Users\jack\miniconda3"
)
if not exist "%CONDA_BASE%\Scripts\activate.bat" (
    echo ERROR: Cannot find conda installation
    pause
    exit /b 1
)

:: Activate environment
call "%CONDA_BASE%\Scripts\activate.bat" "%CONDA_BASE%"
call conda activate pytorch2 2>nul || call conda activate vocal_build 2>nul || (
    echo ERROR: Cannot activate conda environment
    pause
    exit /b 1
)

:: Go to project dir
cd /d "%~dp0"

echo ========================================
echo   Vocal Assessment System
echo ========================================
echo Starting server, please wait...

:: Start Flask in background
start /b "" python web_app.py

:: Wait for server to be ready
echo Waiting for server...
:waitloop
python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health', timeout=1)" 2>nul
if %ERRORLEVEL% EQU 0 goto ready
timeout /t 1 /nobreak >nul
goto waitloop

:ready
echo Server is ready!
start "" http://127.0.0.1:5000
echo Browser opened at http://127.0.0.1:5000
echo Close this window to stop the server.

:: Keep window open (Flask runs in background)
pause >nul
