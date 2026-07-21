@echo off
REM ============================================================
REM 嵌入式 Python 运行时构建脚本
REM ADR-1: 替代 PyInstaller, 启动 <2s, 支持增量更新
REM ============================================================
set PYTHON_VERSION=3.12.7
set BUILD_DIR=.\build\python

echo ========================================
echo   Build Embedded Python Runtime
echo   Version: %PYTHON_VERSION%
echo ========================================

REM 1. Download Python embeddable package
if not exist python-embed.zip (
    echo [1/6] Downloading Python %PYTHON_VERSION% embeddable...
    curl -L -o python-embed.zip ^
      https://www.python.org/ftp/python/%PYTHON_VERSION%/python-%PYTHON_VERSION%-embed-amd64.zip
    if %ERRORLEVEL% NEQ 0 (
        echo ERROR: Failed to download Python embeddable package
        exit /b 1
    )
) else (
    echo [1/6] Using cached python-embed.zip
)

REM 2. Extract
echo [2/6] Extracting...
if exist %BUILD_DIR% rmdir /s /q %BUILD_DIR%
mkdir %BUILD_DIR% 2>nul
tar -xf python-embed.zip -C %BUILD_DIR%
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to extract Python
    exit /b 1
)

REM 3. Install pip
echo [3/6] Installing pip...
if not exist get-pip.py (
    curl -L -o get-pip.py https://bootstrap.pypa.io/get-pip.py
)
%BUILD_DIR%\python.exe get-pip.py --no-warn-script-location
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install pip
    exit /b 1
)

REM 4. CRITICAL: Uncomment "import site" in python312._pth
echo [4/6] Patching python312._pth...
powershell -Command ^
  "(Get-Content %BUILD_DIR%\python312._pth) -replace '^#import site', 'import site' | Set-Content %BUILD_DIR%\python312._pth"
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to patch python312._pth
    exit /b 1
)

REM 5. Install dependencies
echo [5/6] Installing Python packages...
%BUILD_DIR%\Scripts\pip.exe install ^
  fastapi uvicorn[standard] pydantic pydantic-settings ^
  numpy scipy soundfile pyyaml ^
  structlog alembic sqlalchemy ^
  --target %BUILD_DIR%\Lib\site-packages
if %ERRORLEVEL% NEQ 0 (
    echo WARNING: Some packages failed to install
)

REM 6. Cleanup
echo [6/6] Cleaning up...
del python-embed.zip 2>nul
del get-pip.py 2>nul

echo.
echo ========================================
echo   Build Complete!
echo   Output: %BUILD_DIR%
echo ========================================
echo.
echo Next steps:
echo   1. Test: %BUILD_DIR%\python.exe backend\main.py --port=0
echo   2. Electron: copy %BUILD_DIR% to electron/resources/python/
