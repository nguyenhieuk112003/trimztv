@echo off
title Trimz.tv Auto Downloader - Chay 1 Lan (Tai, Xoa Logo & Ghep Video)
chcp 65001 >nul
cd /d "%~dp0"
echo ========================================================
echo   CHAY QUET 1 LAN DUY NHAT (TAI, XOA LOGO & GHEP VIDEO)
echo ========================================================
python "%~dp0TrimzAutoJob.py" --once %*
pause
