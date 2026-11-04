@echo off
title Trimz.tv - Nhat Ky Hoat Dong & Truy Vet (Tracing Log)
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================================
echo         TRIMZ.TV - NHAT KY HOAT DONG & TRUY VET
echo ========================================================
echo.

if not exist "%~dp0logs\auto_job.log" (
    echo [!] Chua co file nhat ky nao tai: logs\auto_job.log
    echo     File nhat ky se tu dong tao khi con job bat dau chay.
    echo.
    pause
    exit /b
)

echo [i] Dang doc file: logs\auto_job.log
echo [i] Bam Ctrl + C de thoat che do theo doi truc tiep.
echo --------------------------------------------------------
echo.

powershell -NoProfile -Command "Get-Content -Path '%~dp0logs\auto_job.log' -Tail 40 -Wait"

pause
