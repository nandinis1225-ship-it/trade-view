@echo off
REM TRADEVERSE developer/testing launcher — opens /developer dashboard (not participant UI)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\offline\start-developer.ps1" %*
