@echo off
chcp 65001 >nul
title Dung Con Job Chay Ngam
echo ========================================================
echo        DỪNG TIẾN TRÌNH CON JOB ĐANG CHẠY NGẦM
echo ========================================================
echo.
echo Đang quét và tắt tiến trình TrimzAutoJob...
wmic process where "commandline like '%%TrimzAutoJob.py%%'" call terminate >nul 2>&1
powershell -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*TrimzAutoJob.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1
echo.
echo [✓] Đã dừng con job thành công!
echo.
pause
