# Start TRADEVERSE in developer/testing mode (full internal dashboard, no participant lockdown)
param(
    [int]$Port = 8765,
    [int]$FrontendPort = 3000
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $Root

$env:LOCAL_INSTANCE_MODE = "true"
$env:DEVELOPER_MODE = "true"
$env:PARTICIPANT_EVENT_MODE = "false"
$env:BACKEND_HOST = "127.0.0.1"
$env:BACKEND_PORT = "$Port"
$env:BACKEND_URL = "http://127.0.0.1:$Port"
$env:FRONTEND_URL = "http://127.0.0.1:$FrontendPort"
$env:CORS_ORIGINS = "http://127.0.0.1:$FrontendPort,http://localhost:$FrontendPort,http://127.0.0.1:$Port"
$env:NEXT_PUBLIC_API_URL = "http://127.0.0.1:$Port"
$env:NEXT_PUBLIC_WS_URL = "ws://127.0.0.1:$Port"
$env:NEXT_PUBLIC_LOCAL_INSTANCE = "true"
$env:NEXT_PUBLIC_DEVELOPER_MODE = "true"
$env:AUTO_INIT_DB = "true"

$backendDir = Join-Path $Root "backend"
$frontendDir = Join-Path $Root "frontend"
$venvPython = Join-Path $backendDir ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "Creating backend virtualenv..."
    python -m venv (Join-Path $backendDir ".venv")
    & $venvPython -m pip install -q -r (Join-Path $backendDir "requirements.txt")
}

Write-Host "Starting backend (developer mode) on port $Port..."
$backend = Start-Process -FilePath $venvPython -ArgumentList @(
    "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", $Port
) -WorkingDirectory $backendDir -PassThru -WindowStyle Hidden

Start-Sleep -Seconds 2

Write-Host "Starting frontend dev server on port $FrontendPort..."
Push-Location $frontendDir
if (-not (Test-Path "node_modules")) { npm install }
$frontend = Start-Process -FilePath "npm.cmd" -ArgumentList @("run", "dev", "--", "--port", $FrontendPort, "--hostname", "127.0.0.1") -PassThru -WindowStyle Hidden
Pop-Location

Start-Sleep -Seconds 4
$devUrl = "http://127.0.0.1:$FrontendPort/developer"
Write-Host ""
Write-Host "TRADEVERSE Developer Mode"
Write-Host "  Dashboard: $devUrl"
Write-Host "  Terminal (participant preview): http://127.0.0.1:$FrontendPort/terminal"
Write-Host "  API health: http://127.0.0.1:$Port/api/v1/health"
Write-Host ""
Write-Host "Press Ctrl+C to stop (backend PID $($backend.Id), frontend PID $($frontend.Id))"

try {
    Start-Process $devUrl | Out-Null
    Wait-Process -Id $backend.Id
} finally {
    if (-not $backend.HasExited) { Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue }
    if (-not $frontend.HasExited) { Stop-Process -Id $frontend.Id -Force -ErrorAction SilentlyContinue }
}
