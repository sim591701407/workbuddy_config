@echo off
REM Windows 一键构建：本地 Web 工具 -> 免安装单文件 exe
REM 用受管 venv 的解释器（PyInstaller 装在这里）
setlocal
set PY=C:\Users\%USERNAME%\.workbuddy\binaries\python\envs\default\Scripts\python.exe
if not exist "%PY%" set PY=python
cd /d "%~dp0"
"%PY%" -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
  echo [信息] 未检测到 PyInstaller，正在安装...
  "%PY%" -m pip install pyinstaller || goto :err
)
"%PY%" build_exe.py %*
if errorlevel 1 goto :err
echo.
echo === 构建完成，产物在 dist\ 目录 ===
pause
exit /b 0
:err
echo.
echo === 构建失败，请查看上方输出 ===
pause
exit /b 1
