# Builds TRADEVERSE public projector package (Windows)
param(
    [switch]$SkipPyInstaller
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$ProjectorDir = Join-Path $Root "projector-build\TRADEVERSE"
$FrontendDir = Join-Path $Root "frontend"
$BackendDir = Join-Path $Root "backend"
$LaunchersDir = Join-Path $PSScriptRoot "launchers"

Write-Host "Ensuring protected production timeline (64 events)..."
Push-Location $BackendDir
python scripts/ensure_production_timeline_pkg.py --events 64
if ($LASTEXITCODE -ne 0) { throw "ensure_production_timeline_pkg.py failed" }
Pop-Location

Write-Host "Building projector frontend..."
Push-Location $FrontendDir
if (-not (Test-Path "node_modules")) { npm install }
npm run build:projector
if ($LASTEXITCODE -ne 0) { throw "projector frontend build failed" }
Pop-Location

if (-not $SkipPyInstaller) {
    Write-Host "Building backend sidecar (PyInstaller)..."
    Push-Location $BackendDir
    if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) { pip install pyinstaller }
    pyinstaller --noconfirm tradeverse-backend.spec
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed" }
    Pop-Location
}

$sidecar = Join-Path $BackendDir "dist\tradeverse-backend.exe"
if (-not (Test-Path $sidecar)) { throw "tradeverse-backend.exe not found" }

if (Test-Path $ProjectorDir) { Remove-Item $ProjectorDir -Recurse -Force }
New-Item -ItemType Directory -Path $ProjectorDir | Out-Null

Copy-Item $sidecar (Join-Path $ProjectorDir "tradeverse-backend.exe")
Copy-Item -Recurse (Join-Path $FrontendDir "out") (Join-Path $ProjectorDir "ui")

Write-Host "Generating projector .env..."
python (Join-Path $BackendDir "scripts\build_event_env.py") `
    --output (Join-Path $ProjectorDir ".env") `
    --projector
if ($LASTEXITCODE -ne 0) { throw "build_event_env.py failed" }

if (Test-Path (Join-Path $LaunchersDir "Start-Tradeverse-Projector.bat")) {
    Copy-Item (Join-Path $LaunchersDir "Start-Tradeverse-Projector.bat") (Join-Path $ProjectorDir "Start-Tradeverse-Projector.bat")
}

$audit = Join-Path $PSScriptRoot "audit-projector-build.ps1"
if (Test-Path $audit) {
    & $audit $ProjectorDir
    if ($LASTEXITCODE -ne 0) { throw "projector build audit failed" }
}

Write-Host ""
Write-Host "Projector package ready: $ProjectorDir"
Write-Host "Open http://127.0.0.1:8765/projector after starting the backend."
