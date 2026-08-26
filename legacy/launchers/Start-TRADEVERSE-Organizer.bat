@echo off
title TRADEVERSE Organizer (Leaderboard)
cd /d "%~dp0"

echo Starting leaderboard collector on port 9000...
echo Participants should set LEADERBOARD_SYNC_URL=http://YOUR_LAN_IP:9000/api/v1/snapshot
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\offline\start-organizer.ps1"
pause
