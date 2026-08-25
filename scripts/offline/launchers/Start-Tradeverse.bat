@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PORT=8765"
set "HEALTH_URL=http://127.0.0.1:%PORT%/api/v1/health"
set "TERMINAL_URL=http://127.0.0.1:%PORT%/terminal"
set "PID_FILE=%~dp0.tradeverse-backend.pid"
set "BACKEND_EXE=%~dp0tradeverse-backend.exe"

if not exist "%BACKEND_EXE%" (
    echo ERROR: tradeverse-backend.exe not found in this folder.
    echo Make sure you copied the full TRADEVERSE package.
    pause
    exit /b 1
)

REM If backend already healthy, just open browser (resume after closing browser)
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -Uri '%HEALTH_URL%' -UseBasicParsing -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }"
if %ERRORLEVEL% equ 0 (
    echo TRADEVERSE backend is already running.
    start "" "%TERMINAL_URL%"
    echo.
    echo Browser opened. Enter your PIN to resume if needed.
    echo Use Stop-Tradeverse.bat when the event is finished.
    exit /b 0
)

echo Starting TRADEVERSE backend...
start "" /B "%BACKEND_EXE%"
timeout /t 2 /nobreak >nul

REM Record PID of tradeverse-backend process (most recent)
for /f "tokens=2" %%p in ('tasklist /FI "IMAGENAME eq tradeverse-backend.exe" /FO LIST ^| findstr /I "PID:"') do set "LAST_PID=%%p"
if defined LAST_PID echo %LAST_PID%> "%PID_FILE%"

echo Waiting for backend health check...
set /a ATTEMPTS=0
:wait_loop
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -Uri '%HEALTH_URL%' -UseBasicParsing -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }"
if %ERRORLEVEL% equ 0 goto health_ok
set /a ATTEMPTS+=1
if %ATTEMPTS% geq 60 (
    echo.
    echo ERROR: Backend did not start within 60 seconds.
    echo Check that port %PORT% is free and try again.
    pause
    exit /b 1
)
timeout /t 1 /nobreak >nul
goto wait_loop

:health_ok
echo Backend is ready.
start "" "%TERMINAL_URL%"
echo.
echo TRADEVERSE opened in your browser.
echo.
echo   1. Enter your name and event PIN
echo   2. Trade until the simulation ends
echo   3. Close the browser anytime — reopen this launcher to resume
echo   4. When finished, run Stop-Tradeverse.bat
echo.
exit /b 0
