@echo off
chcp 65001 >nul
title Dang Nhap 3 Kenh YouTube Doc Lap
echo =====================================================================
echo       CON JOB YOUTUBE - XÁC THỰC 3 KÊNH YOUTUBE ĐỘC LẬP
echo =====================================================================
echo.
echo Chon kenh YouTube ban muon dang nhap de luu token:
echo   [1] Kenh 1: Phim Goc Full (tokens/yt_kenh1_raw.json)
echo   [2] Kenh 2: Review Anime Tieng Anh (tokens/yt_kenh2_en.json)
echo   [3] Kenh 3: Tom Tat Anime Tieng Viet (tokens/yt_kenh3_vi.json)
echo.
set /p CHOICE="Nhap lua chon (1, 2 hoac 3): "

if "%CHOICE%"=="1" (
    echo.
    echo [*] Dang mo trinh duyet de dang nhap KENH 1 (Phim Goc Full)...
    python youtube_uploader.py --auth-only --token "tokens/yt_kenh1_raw.json"
) else if "%CHOICE%"=="2" (
    echo.
    echo [*] Dang mo trinh duyet de dang nhap KENH 2 (Review Anime Tieng Anh)...
    python youtube_uploader.py --auth-only --token "tokens/yt_kenh2_en.json"
) else if "%CHOICE%"=="3" (
    echo.
    echo [*] Dang mo trinh duyet de dang nhap KENH 3 (Tom Tat Anime Tieng Viet)...
    python youtube_uploader.py --auth-only --token "tokens/yt_kenh3_vi.json"
) else (
    echo [!] Lua chon khong hop le.
)

echo.
pause

