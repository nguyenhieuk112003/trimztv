@echo off
chcp 65001 >nul
echo =====================================================================
echo           CON JOB YOUTUBE - TỰ ĐỘNG ĐĂNG VIDEO LÊN YOUTUBE
echo =====================================================================
echo.
set /p VIDEO_PATH="Nhap duong dan file video (.mp4): "
set /p META_PATH="Nhap duong dan file metadata (_SEO.txt hoac _PAYLOAD.json): "
echo.
python youtube_uploader.py --video "%VIDEO_PATH%" --metadata "%META_PATH%"
echo.
pause
