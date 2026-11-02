@echo off
title Trimz.tv Auto Downloader - Giu Nguyen Video Goc
chcp 65001 >nul
cd /d "%~dp0"
echo ========================================================
echo   CHAY TAI VIDEO GOC (KHONG RE-ENCODE XOA LOGO)
echo ========================================================
python "%~dp0TrimzAutoJob.py" --no-delogo %*
pause
