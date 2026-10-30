@echo off
title Trimz.tv Video Downloader
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0TrimzDownloader.ps1"
pause
