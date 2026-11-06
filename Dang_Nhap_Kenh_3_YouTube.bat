@echo off
chcp 65001 >nul
title Dang Nhap YouTube Kenh 3 (Review Tieng Viet)
cd /d "%~dp0"
if not exist "%~dp0tokens" mkdir "%~dp0tokens"
echo =====================================================================
echo      ĐĂNG NHẬP YOUTUBE KÊNH 3 (Review Tiếng Việt)
echo =====================================================================
echo.
echo [*] Trình duyệt sẽ tự động mở lên trong giây lát...
echo [*] Bạn hãy chọn tài khoản Google sở hữu kênh YouTube và bấm "Cho phép" (Allow).
echo.
python youtube_uploader.py --auth-only --token "tokens/yt_kenh3_vi.json" --secrets "client_secrets_k3.json"
echo.
if exist "%~dp0tokens\yt_kenh3_vi.json" (
    echo =====================================================================
    echo 🎉 [THÀNH CÔNG] Đã lưu phiên đăng nhập cho Kênh 3 thành công!
    echo =====================================================================
) else (
    echo [!] Chưa lưu được token. Vui lòng xem thông báo trên cửa sổ này và thử lại.
)
echo.
pause
