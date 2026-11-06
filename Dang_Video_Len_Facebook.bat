@echo off
chcp 65001 >nul
title Dang Video Len Facebook Fanpage
echo =====================================================================
echo       CON JOB FACEBOOK - ĐĂNG VIDEO LÊN FANPAGE QUA GRAPH API
echo =====================================================================
echo.
set /p VIDEO_PATH="Nhap duong dan file video (.mp4): "
set /p PAGE_ID="Nhap ID Fanpage (bam Enter de dung mac dinh Voi review): "
set /p TOKEN="Nhap Page Access Token (bam Enter de dung token tu .env): "
set /p META_PATH="Nhap duong dan file metadata (_PAYLOAD.json hoac de trong): "
echo.

set CMD_ARGS=--video "%VIDEO_PATH%"
if not "%PAGE_ID%"=="" set CMD_ARGS=%CMD_ARGS% --page-id "%PAGE_ID%"
if not "%TOKEN%"=="" set CMD_ARGS=%CMD_ARGS% --token "%TOKEN%"

if "%META_PATH%"=="" (
    set /p TITLE="Nhap tieu de video: "
    set /p DESC="Nhap mo ta video: "
    python facebook_uploader.py %CMD_ARGS% --title "%TITLE%" --description "%DESC%"
) else (
    python facebook_uploader.py %CMD_ARGS% --metadata "%META_PATH%"
)
echo.
pause
