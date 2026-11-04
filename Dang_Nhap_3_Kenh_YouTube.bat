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
    set SECRETS=client_secrets_k1.json
    if not exist "client_secrets_k1.json" set SECRETS=client_secrets.json
    python youtube_uploader.py --auth-only --token "tokens/yt_kenh1_raw.json" --secrets "%SECRETS%"
) else if "%CHOICE%"=="2" (
    echo.
    echo [*] Dang mo trinh duyet de dang nhap KENH 2 (Review Anime Tieng Anh)...
    set SECRETS=client_secrets_k2.json
    if not exist "client_secrets_k2.json" set SECRETS=client_secrets.json
    python youtube_uploader.py --auth-only --token "tokens/yt_kenh2_en.json" --secrets "%SECRETS%"
) else if "%CHOICE%"=="3" (
    echo.
    echo [*] Dang mo trinh duyet de dang nhap KENH 3 (Tom Tat Anime Tieng Viet)...
    set SECRETS=client_secrets_k3.json
    if not exist "client_secrets_k3.json" set SECRETS=client_secrets.json
    python youtube_uploader.py --auth-only --token "tokens/yt_kenh3_vi.json" --secrets "%SECRETS%"
) else (
    echo [!] Lua chon khong hop le.
)

echo.
pause
