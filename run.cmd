@echo off
setlocal
set "ROOT=%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 "%ROOT%scripts\dev.py" %*
) else (
  python "%ROOT%scripts\dev.py" %*
)
