@echo off
title Trimz.tv - Ghep Cac Video Da Tai (Toi Da 40 Phut)
chcp 65001 >nul
cd /d "%~dp0"
echo ========================================================
echo   GHÉP TẤT CẢ VIDEO ĐÃ TẢI THÀNH CÁC PHẦN TỐI ĐA 40 PHÚT
echo ========================================================
if exist "%~dp0tools\python\python.exe" (
    "%~dp0tools\python\python.exe" "%~dp0TrimzAutoJob.py" --merge-only %*
) else (
    python "%~dp0TrimzAutoJob.py" --merge-only %*
)
pause
