@echo off
setlocal
set "PYTHONUTF8=1"
cd /d "%~dp0"

if exist "%~dp0..\python\python.exe" (
  "%~dp0..\python\python.exe" "%~dp0bridge.py" %*
  exit /b
)

where py >nul 2>nul || (
  echo Chua cai Python 3.10 tro len: https://www.python.org/downloads/
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Dang tao moi truong Python rieng cho bridge...
  py -3 -m venv .venv || exit /b 1
  .venv\Scripts\python.exe -m pip install --upgrade pip || exit /b 1
)

.venv\Scripts\python.exe -c "import TikTokLive, elevenlabs, dotenv, edge_tts, imageio_ffmpeg, PIL" >nul 2>nul || (
  echo Dang cai thu vien TikTok Live va TTS...
  .venv\Scripts\python.exe -m pip install -r requirements.txt || exit /b 1
)

.venv\Scripts\python.exe bridge.py %*
exit /b %errorlevel%
