# Builds TRADEVERSE public projector package (Windows)
param(
    [Parameter(Mandatory = $true)]
    [string]$TimelineKey,
    [switch]$SkipTauri
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$ProjectorDir = Join-Path $Root "projector-build"
$FrontendDir = Join-Path $Root "frontend"
$BackendDir = Join-Path $Root "backend"
$BakedTimeline = Join-Path $BackendDir "app\seed\tradeverse_timeline.baked.json"

Write-Host "Building projector frontend..."
Push-Location $FrontendDir
if (-not (Test-Path "node_modules")) { npm install }
npm run build:projector
if ($LASTEXITCODE -ne 0) { throw "projector frontend build failed" }
Pop-Location

Write-Host "Baking timeline for projector..."
$envOut = Join-Path $Root "dist-package\.env.projector"
New-Item -ItemType Directory -Path (Split-Path $envOut) -Force | Out-Null
python (Join-Path $BackendDir "scripts\build_event_env.py") `
    --timeline-key $TimelineKey `
    --event-pin "0000" `
    --output $envOut `
    --bake-timeline $BakedTimeline `
    --projector
if ($LASTEXITCODE -ne 0) { throw "build_event_env.py failed" }

Write-Host "Building backend sidecar..."
Push-Location $BackendDir
if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) { pip install pyinstaller }
pyinstaller --noconfirm tradeverse-backend.spec
Pop-Location

$sidecar = Join-Path $BackendDir "dist\tradeverse-backend.exe"
if (-not (Test-Path $sidecar)) { throw "tradeverse-backend.exe not found" }

if (Test-Path $ProjectorDir) { Remove-Item $ProjectorDir -Recurse -Force }
New-Item -ItemType Directory -Path $ProjectorDir | Out-Null
Copy-Item $sidecar (Join-Path $ProjectorDir "tradeverse-backend.exe")
Copy-Item $envOut (Join-Path $ProjectorDir ".env")
Copy-Item $BakedTimeline (Join-Path $ProjectorDir "tradeverse_timeline.baked.json")
Copy-Item -Recurse (Join-Path $FrontendDir "out") (Join-Path $ProjectorDir "ui")

Write-Host "Projector package ready: $ProjectorDir"
Write-Host "Open ui/projector/index.html via backend on http://127.0.0.1:8765/projector"
