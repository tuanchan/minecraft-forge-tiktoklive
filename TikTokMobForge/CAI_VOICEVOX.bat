@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install_voicevox.ps1"
if errorlevel 1 (
  echo Cai VOICEVOX that bai. Xem loi o tren.
  pause
  exit /b 1
)
echo Da cai VOICEVOX. Bam Tai giong hoac Test trong GUI.
pause
