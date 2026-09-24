@echo off
cd /d "%~dp0"
call RUN_BRIDGE.bat --test all
pause
