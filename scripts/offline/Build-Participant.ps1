# Builds self-contained TRADEVERSE participant package (Windows)
param(
    [Parameter(Mandatory = $true)]
    [string]$TimelineKey,
    [Parameter(Mandatory = $true)]
    [string]$EventPin,
    [switch]$SkipRehearsal,
    [switch]$SkipTauri
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$ParticipantDir = Join-Path $Root "participant-build"
$FrontendDir = Join-Path $Root "frontend"
$BackendDir = Join-Path $Root "backend"
$BakedTimeline = Join-Path $BackendDir "app\seed\tradeverse_timeline.baked.json"

if (-not $SkipRehearsal) {
    $rehearsal = Join-Path $Root "scripts\dev\run-event-rehearsal.ps1"
    if (Test-Path $rehearsal) {
        Write-Host "Running developer rehearsal gate..."
        & $rehearsal
        if ($LASTEXITCODE -ne 0) { throw "developer rehearsal failed — use -SkipRehearsal to override" }
    }
}

Write-Host "Building participant frontend..."
Push-Location $FrontendDir
if (-not (Test-Path "node_modules")) { npm install }
$env:PARTICIPANT_BUILD = "1"
npm run build
if ($LASTEXITCODE -ne 0) { throw "frontend build failed" }
Pop-Location

foreach ($dir in @("admin", "market-screen", "developer")) {
    $target = Join-Path $FrontendDir "out\$dir"
    if (Test-Path $target) { Remove-Item $target -Recurse -Force }
}

Write-Host "Baking timeline and participant .env..."
$envOut = Join-Path $Root "dist-package\.env"
New-Item -ItemType Directory -Path (Split-Path $envOut) -Force | Out-Null
python (Join-Path $BackendDir "scripts\build_event_env.py") `
    --timeline-key $TimelineKey `
    --event-pin $EventPin `
    --output $envOut `
    --bake-timeline $BakedTimeline
if ($LASTEXITCODE -ne 0) { throw "build_event_env.py failed" }

Write-Host "Building backend sidecar (PyInstaller)..."
Push-Location $BackendDir
if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    pip install pyinstaller
}
pyinstaller --noconfirm tradeverse-backend.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed" }
Pop-Location

$sidecar = Join-Path $BackendDir "dist\tradeverse-backend.exe"
if (-not (Test-Path $sidecar)) { throw "tradeverse-backend.exe not found after PyInstaller build" }

if (Test-Path $ParticipantDir) { Remove-Item $ParticipantDir -Recurse -Force }
New-Item -ItemType Directory -Path $ParticipantDir | Out-Null

Copy-Item $sidecar (Join-Path $ParticipantDir "tradeverse-backend.exe")
Copy-Item $envOut (Join-Path $ParticipantDir ".env")
Copy-Item $BakedTimeline (Join-Path $ParticipantDir "tradeverse_timeline.baked.json")
Copy-Item -Recurse (Join-Path $FrontendDir "out") (Join-Path $ParticipantDir "ui")

if (-not $SkipTauri) {
    Write-Host "Building Tauri shell..."
    Push-Location (Join-Path $Root "desktop")
    if (-not (Test-Path "node_modules")) { npm install }
    npm run tauri build
    if ($LASTEXITCODE -ne 0) { throw "Tauri build failed" }
    Pop-Location
    $tauriOut = Get-ChildItem -Path (Join-Path $Root "desktop\src-tauri\target\release\bundle") -Recurse -Filter "TRADEVERSE*.exe" | Select-Object -First 1
    if ($tauriOut) {
        Copy-Item $tauriOut.FullName (Join-Path $ParticipantDir "TRADEVERSE.exe")
        Copy-Item $sidecar (Join-Path $ParticipantDir "tradeverse-backend.exe") -Force
    }
}

$audit = Join-Path $PSScriptRoot "audit-participant-build.ps1"
if (Test-Path $audit) {
    & $audit $ParticipantDir
    if ($LASTEXITCODE -ne 0) { throw "participant build audit failed" }
}

Write-Host ""
Write-Host "Participant build ready: $ParticipantDir"
Write-Host "Distribute TRADEVERSE.exe + tradeverse-backend.exe (same folder)."
Write-Host "Announce EVENT_PIN verbally at event start — hash is baked into .env."
