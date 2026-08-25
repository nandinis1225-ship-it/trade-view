@echo off
title Build TRADEVERSE Participant
cd /d "%~dp0"

set "EVENT_PIN_VAL=%EVENT_PIN%"
if "%EVENT_PIN_VAL%"=="" (
  set /p EVENT_PIN_VAL="Enter EVENT_PIN: "
)

echo Building TRADEVERSE participant package...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\offline\Build-Participant.ps1" -EventPin "%EVENT_PIN_VAL%"
if errorlevel 1 (
  echo.
  echo Build failed. See errors above.
  pause
  exit /b 1
)

echo.
echo Done. Distribute participant-build\windows\ to participants.
echo Announce EVENT_PIN verbally at event start.
echo.
pause
