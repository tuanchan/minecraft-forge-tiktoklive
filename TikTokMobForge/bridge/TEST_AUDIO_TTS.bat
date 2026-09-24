@echo off
cd /d "%~dp0"
call RUN_BRIDGE.bat --test-tts
if errorlevel 1 (
  echo.
  echo Test audio that bai. Kiem tra ELEVENLABS_API_KEY trong bridge\.env.
) else (
  echo.
  echo Test audio thanh cong.
)
pause
