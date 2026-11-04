@echo off
title Trimz.tv Auto Cron Job - Tu Dong Tai, Xoa Logo & Ghep Video (Max 40p)
chcp 65001 >nul
cd /d "%~dp0"
echo ========================================================
echo   KHOI DONG CON JOB TAI, XOA LOGO & GHEP VIDEO (MAX 40P)
echo ========================================================
if exist "%~dp0tools\python\python.exe" (
    "%~dp0tools\python\python.exe" "%~dp0TrimzAutoJob.py" %*
) else (
    python "%~dp0TrimzAutoJob.py" %*
)
pause
