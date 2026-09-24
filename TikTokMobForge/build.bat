@echo off
setlocal
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\build_and_install_mod.ps1" %*
set "RESULT=%errorlevel%"
if not "%RESULT%"=="0" echo Build hoac cap nhat mod that bai. Xem thong bao phia tren.
exit /b %RESULT%
