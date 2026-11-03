@echo off
chcp 65001 >nul
title Dang Video Len Facebook Fanpage
echo =====================================================================
echo       CON JOB FACEBOOK - ĐĂNG VIDEO LÊN FANPAGE QUA GRAPH API
echo =====================================================================
echo.
set /p VIDEO_PATH="Nhap duong dan file video (.mp4): "
set /p PAGE_ID="Nhap ID Fanpage Facebook: "
set /p TOKEN="Nhap Page Access Token: "
set /p META_PATH="Nhap duong dan file metadata (_PAYLOAD.json hoac de trong): "
echo.
if "%META_PATH%"=="" (
    set /p TITLE="Nhap tieu de video: "
    set /p DESC="Nhap mo ta video: "
    python facebook_uploader.py --video "%VIDEO_PATH%" --page-id "%PAGE_ID%" --token "%TOKEN%" --title "%TITLE%" --description "%DESC%"
) else (
    python facebook_uploader.py --video "%VIDEO_PATH%" --page-id "%PAGE_ID%" --token "%TOKEN%" --metadata "%META_PATH%"
)
echo.
pause

