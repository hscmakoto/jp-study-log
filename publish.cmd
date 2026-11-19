@echo off
setlocal enabledelayedexpansion
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
rem GitHub Actions 会自动提交 README，先拉取避免 push 被拒。
rem 注意：git 把正常信息写到 stderr，不能用 || 判断，只能看 errorlevel。
git pull --rebase --autostash origin main
if errorlevel 1 goto pull_failed

echo.
echo === building README ===
python scripts\build_readme.py
if errorlevel 1 goto err

echo.
echo === commit ===
git add -A
git commit -m "log: update study records"
if errorlevel 1 echo Nothing new to commit.

echo.
echo === push ===
set "GIT_TERMINAL_PROMPT=0"
git push --set-upstream origin main
if not errorlevel 1 goto pushed

rem push 失败时，从 Windows 凭据管理器取 token 再推一次。
rem GCM 的输入必须从文件重定向，用管道在批处理里不可靠。
echo.
echo [WARN] push failed. Trying windows credential store...
set "GCM=D:\Program Files\Git\mingw64\bin\git-credential-manager.exe"
if not exist "!GCM!" set "GCM="
if not defined GCM (
  for /f "delims=" %%p in ('where git-credential-manager') do if not defined GCM set "GCM=%%p"
)
if not defined GCM goto push_failed

set "CRED_IN=%TEMP%\jp_cred_in.txt"
set "CRED_OUT=%TEMP%\jp_cred_out.txt"
> "!CRED_IN!" (
  echo protocol=https
  echo host=github.com
)
"!GCM!" get < "!CRED_IN!" > "!CRED_OUT!" 2>nul
del "!CRED_IN!" >nul 2>nul

set "GH_USER="
set "GH_TOKEN="
for /f "usebackq tokens=1,* delims==" %%a in ("!CRED_OUT!") do (
  if /i "%%a"=="username" set "GH_USER=%%b"
  if /i "%%a"=="password" set "GH_TOKEN=%%b"
)
del "!CRED_OUT!" >nul 2>nul
if not defined GH_TOKEN goto push_failed

git push "https://!GH_USER!:!GH_TOKEN!@github.com/hscmakoto/jp-study-log.git" main:main
if errorlevel 1 goto push_failed
echo [retried with stored credential]

:pushed
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
echo   - not logged in: open Git Credential Manager or run  gh auth login
echo   - repo does not exist yet on github.com
echo   - remote changed during push: run publish.cmd again
pause
exit /b 1

:err
echo [ERROR] build_readme failed.
pause
exit /b 1
