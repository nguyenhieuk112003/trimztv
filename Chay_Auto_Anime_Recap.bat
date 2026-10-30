@echo off
title Auto Anime Recap Pipeline - Trimz to YouTube
chcp 65001 >nul
"%~dp0tools\python\python.exe" "%~dp0AutoAnimeRecap.py" %*
pause
