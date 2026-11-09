@echo off
setlocal
cd /d "%~dp0"
echo === status ===
git status -sb
echo.
echo === stage all ===
git add -A
echo.
echo === commit ===
git commit -m "feat: import history, strict streak, auto-start heatmap"
if errorlevel 1 echo Nothing to commit.
echo.
echo === push ===
git push -u origin main
echo.
echo If it asks for a password, use a Personal Access Token (https://github.com/settings/tokens)
echo with the "repo" scope, NOT your account password.
pause
