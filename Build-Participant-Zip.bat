@echo off
title Build TRADEVERSE Participant Zip
cd /d "%~dp0"

set "TIMELINE_KEY=%TIMELINE_DECRYPT_KEY%"
set "EVENT_PIN_VAL=%EVENT_PIN%"
if "%TIMELINE_KEY%"=="" (
  set /p TIMELINE_KEY="Enter TIMELINE_DECRYPT_KEY: "
)
if "%EVENT_PIN_VAL%"=="" (
  set /p EVENT_PIN_VAL="Enter EVENT_PIN: "
)

echo Building Tradeverse-Participant.zip ...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\offline\build-share-package.ps1" -TimelineKey "%TIMELINE_KEY%" -EventPin "%EVENT_PIN_VAL%"
if errorlevel 1 (
  echo.
  echo Build failed. See errors above.
  pause
  exit /b 1
)

echo.
echo Done. Send Tradeverse-Participant.zip to participants.
echo Announce EVENT_PIN verbally at event start.
echo For TRADEVERSE.exe use scripts\offline\Build-Participant.ps1
echo.
pause
