@echo off
cd /d "%~dp0"
call RUN_BRIDGE.bat
if errorlevel 1 goto :error
pause
exit /b 0
:error
echo Cai dat that bai.
pause
exit /b 1
