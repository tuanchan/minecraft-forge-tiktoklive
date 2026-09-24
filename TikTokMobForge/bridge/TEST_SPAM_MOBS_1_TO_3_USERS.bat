@echo off
setlocal
cd /d "%~dp0"

echo =============================================
echo   TEST SPAM MOB - CHON SO USER TU 1 DEN 3
echo =============================================
echo Moi user se spam 10 mob.
echo Ket qua dung: moi user chi con 4 mob cuoi.
echo.

choice /C 123 /N /M "Chon so user [1/2/3]: "
set "USER_COUNT=%ERRORLEVEL%"

echo.
echo Dang test spam voi %USER_COUNT% user...
call RUN_BRIDGE.bat --test-spam-users %USER_COUNT%
if errorlevel 1 goto :error

echo.
echo Da gui xong. Kiem tra so quai trong Minecraft.
echo Mong doi: %USER_COUNT% user, moi user 4 quai.
echo Log gui test nam trong bridge\logs.
echo Log spawn/despawn thuc te: tim [TikTokMobLimit] trong logs\latest.log cua Minecraft.
pause
exit /b 0

:error
echo.
echo Test that bai. Hay mo Minecraft, vao world va kiem tra mod dang chay.
pause
exit /b 1
