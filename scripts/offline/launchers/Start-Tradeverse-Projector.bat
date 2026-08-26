@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "BACKEND_EXE=%~dp0tradeverse-backend.exe"
set "PID_FILE=%~dp0.tradeverse-projector.pid"
set "PORT=8765"
set "URL=http://127.0.0.1:%PORT%/projector"

if not exist "%BACKEND_EXE%" (
    echo tradeverse-backend.exe not found in %~dp0
    exit /b 1
)

if exist "%PID_FILE%" (
    for /f %%p in (%PID_FILE%) do (
        tasklist /FI "PID eq %%p" 2>nul | find "%%p" >nul
        if not errorlevel 1 (
            echo Projector backend already running PID %%p
            start "" "%URL%"
            exit /b 0
        )
    )
)

echo Starting TRADEVERSE projector backend...
start "" /B "%BACKEND_EXE%"
timeout /t 2 /nobreak >nul

for /f "tokens=2" %%p in ('tasklist /FI "IMAGENAME eq tradeverse-backend.exe" /FO LIST ^| find "PID:"') do set "LAST_PID=%%p"
if defined LAST_PID echo %LAST_PID%>"%PID_FILE%"

set /a tries=0
:wait_health
set /a tries+=1
powershell -NoProfile -Command "try { (Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:%PORT%/api/v1/health' -TimeoutSec 2).StatusCode } catch { 0 }" | find "200" >nul
if errorlevel 1 (
    if %tries% lss 30 (
        timeout /t 1 /nobreak >nul
        goto wait_health
    )
    echo Backend health check failed.
    exit /b 1
)

start "" "%URL%"
echo TRADEVERSE projector opened at %URL%
exit /b 0
