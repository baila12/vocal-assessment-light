@echo off
title Vocal Assessment v7.0
setlocal enabledelayedexpansion

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
echo   Vocal Assessment System v7.0
echo ========================================
echo.
echo Select launch mode:
echo   [1] FastAPI backend only (v7.0)
echo   [2] Flask backend only (v6.3 legacy)
echo   [3] FastAPI + Vite dev server (v7.0 full stack)
echo   [4] Flask + browser (v6.3 legacy full)
echo.
set /p "MODE=Enter choice (1-4): "

if "%MODE%"=="1" goto fastapi_only
if "%MODE%"=="2" goto flask_only
if "%MODE%"=="3" goto full_v7
if "%MODE%"=="4" goto full_v6
goto fastapi_only

:: ============================================================
:fastapi_only
echo.
echo Starting FastAPI v7.0 backend...
start /b "" python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
goto wait_fastapi

:: ============================================================
:flask_only
echo.
echo Starting Flask v6.3 backend...
start /b "" python web_app.py
goto wait_flask

:: ============================================================
:full_v7
echo.
echo Starting FastAPI v7.0 backend (port 8000)...
start /b "" python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload

echo Waiting for FastAPI...
:wait_fastapi_v7
python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=1)" 2>nul
if %ERRORLEVEL% EQU 0 goto vite_start
timeout /t 1 /nobreak >nul
goto wait_fastapi_v7

:vite_start
echo FastAPI ready! Starting Vite dev server (port 5173)...
echo NOTE: Run 'cd frontend ^&^& npm run dev' in a separate terminal for full HMR
start "" http://127.0.0.1:5173
echo.
echo Backend:  http://127.0.0.1:8000
echo Frontend: http://127.0.0.1:5173 (open manually after 'npm run dev')
echo Health:   http://127.0.0.1:8000/health
echo API Docs: http://127.0.0.1:8000/docs
goto keep_alive

:: ============================================================
:full_v6
echo.
echo Starting Flask v6.3 backend...
start /b "" python web_app.py

echo Waiting for Flask...
:wait_flask_v6
python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health', timeout=1)" 2>nul
if %ERRORLEVEL% EQU 0 goto browser_open
timeout /t 1 /nobreak >nul
goto wait_flask_v6

:browser_open
echo Flask ready! Opening browser...
start "" http://127.0.0.1:5000
goto keep_alive

:: ============================================================
:wait_fastapi
echo Waiting for FastAPI...
:waitloop_fa
python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=1)" 2>nul
if %ERRORLEVEL% EQU 0 goto fastapi_ready
timeout /t 1 /nobreak >nul
goto waitloop_fa

:fastapi_ready
echo FastAPI ready!
echo Health:   http://127.0.0.1:8000/health
echo API Docs: http://127.0.0.1:8000/docs
echo.
pause >nul
goto :eof

:: ============================================================
:wait_flask
echo Waiting for Flask...
:waitloop_fl
python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health', timeout=1)" 2>nul
if %ERRORLEVEL% EQU 0 goto flask_ready
timeout /t 1 /nobreak >nul
goto waitloop_fl

:flask_ready
echo Flask ready! Opening browser...
start "" http://127.0.0.1:5000
echo.
pause >nul
goto :eof

:: ============================================================
:keep_alive
echo.
echo Close this window to stop all servers.
pause >nul
goto :eof
