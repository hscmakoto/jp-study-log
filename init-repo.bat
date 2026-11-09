@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

where git >nul 2>nul
if errorlevel 1 (
  echo [ERROR] git not found. Install Git for Windows first.
  pause
  exit /b 1
)

if exist ".git" (
  echo Repo already initialized.
) else (
  git init
  git branch -M main
)

rem identity: prompt with a dummy default first, so the first answer is never lost
git config user.name >nul 2>nul
set "NEED_NAME=%errorlevel%"
git config user.email >nul 2>nul
set "NEED_EMAIL=%errorlevel%"

if not "%NEED_NAME%"=="0" (
  git config user.name "Your Name"
  set "GIT_NAME="
  set /p GIT_NAME=Your git user name:
  if defined GIT_NAME git config user.name "!GIT_NAME!"
)
if not "%NEED_EMAIL%"=="0" (
  git config user.email "you@example.com"
  set "GIT_EMAIL="
  set /p GIT_EMAIL=Your GitHub email:
  if defined GIT_EMAIL git config user.email "!GIT_EMAIL!"
)

git config user.name
git config user.email

git add -A
git commit -m "init: Japanese study log"
if errorlevel 1 echo Commit skipped: nothing to commit.

echo.
echo Next: create an EMPTY public repo named jp-study-log on github.com,
echo without README / .gitignore / license. Then run:
echo   git remote add origin https://github.com/USER/jp-study-log.git
echo   git push -u origin main
echo.
pause
