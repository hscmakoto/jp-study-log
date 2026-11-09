@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
python scripts\build_readme.py || goto err
git add -A
git commit -m "log: update study records"
if errorlevel 1 echo Nothing new to commit.
git push || goto err
echo Pushed. Refresh the GitHub repo page in a few seconds.
pause
exit /b 0

:err
echo [ERROR] something failed, see output above.
pause
exit /b 1
