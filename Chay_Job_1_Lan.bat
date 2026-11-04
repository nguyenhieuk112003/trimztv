@echo off
title Trimz.tv Auto Downloader - Chay 1 Lan (Tai, Xoa Logo & Ghep Video)
chcp 65001 >nul
cd /d "%~dp0"
echo ========================================================
echo   CHAY QUET 1 LAN DUY NHAT (TAI, XOA LOGO & GHEP VIDEO)
echo ========================================================
if exist "%~dp0tools\python\python.exe" (
    "%~dp0tools\python\python.exe" "%~dp0TrimzAutoJob.py" --once %*
) else (
    python "%~dp0TrimzAutoJob.py" --once %*
)
pause
