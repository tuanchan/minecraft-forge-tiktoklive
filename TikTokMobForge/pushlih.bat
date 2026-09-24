@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\publish_desktop.ps1" %*
set "RESULT=%errorlevel%"
if not "%RESULT%"=="0" echo Build that bai. Xem thong bao phia tren.
exit /b %RESULT%
