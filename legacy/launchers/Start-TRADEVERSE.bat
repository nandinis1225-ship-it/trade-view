@echo off
title TRADEVERSE
cd /d "%~dp0"

where node >nul 2>&1
if errorlevel 1 (
  echo.
  echo Node.js is not installed. Download from https://nodejs.org
  echo.
  pause
  exit /b 1
)

where python >nul 2>&1
if errorlevel 1 (
  where py >nul 2>&1
  if errorlevel 1 (
    echo.
    echo Python 3 is not installed. Download from https://www.python.org/downloads/
    echo Check "Add python.exe to PATH" during install.
    echo.
    pause
    exit /b 1
  )
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\offline\start-participant.ps1"
if errorlevel 1 pause
