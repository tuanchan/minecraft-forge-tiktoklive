@echo off
setlocal
cd /d "%~dp0"

if exist "%~dp0TikTokMobForge\artifacts\desktop\TikTokMobForge.Desktop.exe" (
  start "" "%~dp0TikTokMobForge\artifacts\desktop\TikTokMobForge.Desktop.exe"
  exit /b 0
)

if exist "%~dp0TikTokMobForge\bridge\.venv\Scripts\pythonw.exe" (
  start "LIVE Control" "%~dp0TikTokMobForge\bridge\.venv\Scripts\pythonw.exe" "%~dp0TikTokMobForge\web\launch_gui.py"
  exit /b 0
)

where pyw >nul 2>nul || (
  echo Chua cai Python 3.10 tro len. Tai tai https://www.python.org/downloads/
  pause
  exit /b 1
)

start "LIVE Control WebView" pyw -3 "%~dp0TikTokMobForge\web\launch_gui.py"
exit /b 0
