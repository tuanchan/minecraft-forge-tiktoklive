@echo off
chcp 65001 >nul
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    set PY=py
) else (
    set PY=python
)

%PY% -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo Cai thu vien that bai.
    pause
    exit /b 1
)

%PY% main.py
pause
