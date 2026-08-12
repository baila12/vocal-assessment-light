@echo off
title Vocal Assessment v7.9
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
call conda activate pytorch2 2>nul || (
    echo ERROR: Cannot activate conda environment
    pause
    exit /b 1
)

:: Go to project dir
cd /d "%~dp0"

echo ========================================
echo   Vocal Assessment System v7.9
echo ========================================
echo.
echo Select launch mode:
echo   [1] FastAPI backend only (v7.9, :8000, 服务 frontend/dist)
echo   [2] FastAPI + Vite dev server (v7.9 full stack)
echo.
set /p "MODE=Enter choice (1-2): "

if "%MODE%"=="1" goto fastapi_only
if "%MODE%"=="2" goto full_v7
goto fastapi_only

:: ============================================================
:fastapi_only
echo.
echo Starting FastAPI v7.9 backend (:8000)...
start /b "" python backend/main.py
goto wait_fastapi

:: ============================================================
:full_v7
echo.
echo Starting FastAPI v7.9 backend (:8000)...
start /b "" python backend/main.py

echo Waiting for FastAPI...
:wait_fastapi_v7
python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=1)" 2>nul
if %ERRORLEVEL% EQU 0 goto ready
timeout /t 1 /nobreak >nul
goto wait_fastapi_v7

:ready
echo FastAPI ready!
echo.
echo NOTE: Run 'cd frontend ^&^& npm run dev' in a separate terminal for Vite HMR (:5173)
start "" http://127.0.0.1:8000
echo.
echo Backend:  http://127.0.0.1:8000
echo API Docs: http://127.0.0.1:8000/docs
echo Health:   http://127.0.0.1:8000/health
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
:keep_alive
echo.
echo Close this window to stop all servers.
pause >nul
goto :eof
