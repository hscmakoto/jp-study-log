@echo off
setlocal
cd /d "%~dp0"

echo === git status ===
git status -sb
echo.

where gh >nul 2>nul
if errorlevel 1 goto no_gh

gh auth status >nul 2>nul
if errorlevel 1 (
  echo [INFO] gh CLI found but not logged in. Starting browser login...
  gh auth login --hostname github.com --git-protocol https --web
  if errorlevel 1 goto auth_failed
)

echo === syncing git credential helper with gh ===
gh auth setup-git

:no_gh
echo.
echo === syncing with remote ===
rem GitHub Actions 会自动提交 README，先拉取避免 push 被拒
git pull --rebase --autostash origin main || goto pull_failed

echo.
echo === building README ===
python scripts\build_readme.py || goto err

echo.
echo === commit ===
git add -A
git commit -m "log: update study records"
if errorlevel 1 echo Nothing new to commit.

echo.
echo === push ===
git push --set-upstream origin main || goto push_failed
echo.
echo Pushed. Refresh the GitHub repo page in a few seconds.
pause
exit /b 0

:pull_failed
echo.
echo [ERROR] git pull failed. README may have conflicts.
echo   Fix it manually, then run publish.cmd again.
echo   To abort the pull:  git rebase --abort
pause
exit /b 1

:auth_failed
echo.
echo [ERROR] GitHub login failed or was cancelled.
echo Try again, or set a Personal Access Token as the password when git asks.
pause
exit /b 1

:push_failed
echo.
echo [ERROR] push failed. Common causes:
echo   - not logged in: run  gh auth login   (or use a Personal Access Token)
echo   - repo does not exist yet on github.com
echo   - remote changed during push: run publish.cmd again
pause
exit /b 1

:err
echo [ERROR] build_readme failed.
pause
exit /b 1
