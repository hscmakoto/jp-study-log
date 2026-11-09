@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] python not found. Install Python 3.10+ and add it to PATH.
  pause
  exit /b 1
)
set PYTHONUTF8=1
python scripts\jp_log.py %*
if errorlevel 1 pause
python scripts\build_readme.py
echo.
echo Done. Run publish.cmd to push to GitHub.
pause
