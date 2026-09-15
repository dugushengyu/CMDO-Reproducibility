@echo off
setlocal

REM CMDO reviewer one-command Windows launcher.
REM Uses a process-local PowerShell execution-policy bypass only for this run.
REM It does not change the user's machine-wide or account-wide execution policy.

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0RUN_REVIEWER_FROM_ZERO.ps1" %*
set "RC=%ERRORLEVEL%"

if not "%RC%"=="0" (
    echo.
    echo CMDO reviewer run failed with exit code %RC%.
)

exit /b %RC%
