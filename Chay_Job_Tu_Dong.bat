@echo off
title Trimz.tv Auto Cron Job - Tu Dong Tai, Xoa Logo & Ghep Video (Max 40p)
chcp 65001 >nul
cd /d "%~dp0"
echo ========================================================
echo   KHOI DONG CON JOB TAI, XOA LOGO & GHEP VIDEO (MAX 40P)
echo ========================================================
python "%~dp0TrimzAutoJob.py" %*
pause
