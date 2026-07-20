@echo off
REM ============================================================
REM 声乐评估系统 — PyInstaller 打包脚本
REM ============================================================
REM 输出: dist\VocalAssessment\VocalAssessment.exe
REM ============================================================

echo.
echo ============================================================
echo   声乐评估系统 — PyInstaller 打包
echo ============================================================
echo.

REM 激活 conda 环境 (如果有)
call conda activate pytorch2 2>nul

REM 清理旧构建 (可选)
if "%1"=="--clean" (
    echo [1/3] 清理旧构建...
    if exist build rmdir /s /q build
    if exist dist\VocalAssessment rmdir /s /q dist\VocalAssessment
    echo       完成
) else (
    echo [1/3] 跳过清理 (使用 --clean 强制清理)
)

REM PyInstaller 构建
echo [2/3] PyInstaller 构建中 (可能需要 10-30 分钟)...
pyinstaller vocal_assessment.spec
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] PyInstaller 构建失败！
    echo   常见问题:
    echo   1. 查看 build\vocal_assessment\warn-vocal_assessment.txt 中的缺失模块
    echo   2. 修改 vocal_assessment.spec 添加 hiddenimports
    echo   3. 重新运行: build.bat --clean
    exit /b %ERRORLEVEL%
)

REM 检查输出
echo [3/3] 验证输出...
if exist "dist\VocalAssessment\VocalAssessment.exe" (
    echo.
    echo ============================================================
    echo   BUILD SUCCESS!
    echo   输出: dist\VocalAssessment\VocalAssessment.exe
    echo ============================================================
    echo.
    REM 显示大小
    for %%A in ("dist\VocalAssessment") do echo   目录大小: %%~zA bytes
    echo.
    echo   运行方式:
    echo     dist\VocalAssessment\VocalAssessment.exe
    echo     dist\VocalAssessment\VocalAssessment.exe --debug
) else (
    echo.
    echo [ERROR] 未找到输出文件，构建可能失败
    echo   检查 build\ 目录中的日志
)
