@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PID_FILE=%~dp0.tradeverse-backend.pid"

echo Stopping TRADEVERSE backend...

if exist "%PID_FILE%" (
    set /p BACKEND_PID=<"%PID_FILE%"
    if defined BACKEND_PID (
        taskkill /PID %BACKEND_PID% /F >nul 2>&1
    )
    del /f /q "%PID_FILE%" >nul 2>&1
)

REM Fallback: stop any tradeverse-backend.exe from this folder
taskkill /IM tradeverse-backend.exe /F >nul 2>&1

echo TRADEVERSE backend stopped.
echo Your portfolio data is saved on this computer.
pause
