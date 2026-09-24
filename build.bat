@echo off
setlocal
call "%~dp0TikTokMobForge\build.bat" %*
exit /b %errorlevel%
