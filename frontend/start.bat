@echo off
set "PATH=%LOCALAPPDATA%\Programs\nodejs;%PATH%"
cd /d "%~dp0"
echo ========================================================
echo  Pornire SafeTarmac AI (Vite Development Server)
echo  Rol C - Frontend, PWA si Demo (Ariana)
echo ========================================================
echo.
npm run dev
pause
