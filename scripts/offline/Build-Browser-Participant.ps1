# Builds browser-based TRADEVERSE participant package (Windows — no Tauri)
param(
    [Parameter(Mandatory = $true)]
    [string]$EventPin,
    [int]$TimelineEvents = 64,
    [switch]$SkipRehearsal,
    [switch]$SkipPyInstaller
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$OutDir = Join-Path $Root "participant-build\windows\TRADEVERSE"
$FrontendDir = Join-Path $Root "frontend"
$BackendDir = Join-Path $Root "backend"
$LaunchersDir = Join-Path $PSScriptRoot "launchers"
$TimelineJson = Join-Path $BackendDir "app\seed\tradeverse_timeline.json"

if (-not (Test-Path $TimelineJson)) {
    throw "Production timeline missing: $TimelineJson (required, $TimelineEvents events)"
}

if (-not $SkipRehearsal) {
    $rehearsal = Join-Path $Root "scripts\dev\run-event-rehearsal.ps1"
    if (Test-Path $rehearsal) {
        Write-Host "Running developer rehearsal gate..."
        & $rehearsal
        if ($LASTEXITCODE -ne 0) { throw "developer rehearsal failed — use -SkipRehearsal to override" }
    }
}

Write-Host "Protecting production timeline ($TimelineEvents events)..."
Push-Location $BackendDir
python scripts/protect_timeline.py --events $TimelineEvents
if ($LASTEXITCODE -ne 0) { throw "protect_timeline.py failed" }
Pop-Location

Write-Host "Building participant frontend..."
Push-Location $FrontendDir
if (-not (Test-Path "node_modules")) { npm install }
npm run build:participant
if ($LASTEXITCODE -ne 0) { throw "frontend build failed" }
Pop-Location

if (-not $SkipPyInstaller) {
    Write-Host "Building backend sidecar (PyInstaller)..."
    Push-Location $BackendDir
    if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
        pip install pyinstaller
    }
    pyinstaller --noconfirm tradeverse-backend.spec
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed" }
    Pop-Location
}

$sidecar = Join-Path $BackendDir "dist\tradeverse-backend.exe"
if (-not (Test-Path $sidecar)) {
    throw "tradeverse-backend.exe not found — build PyInstaller sidecar on Windows"
}

if (Test-Path $OutDir) { Remove-Item $OutDir -Recurse -Force }
New-Item -ItemType Directory -Path $OutDir | Out-Null

Copy-Item $sidecar (Join-Path $OutDir "tradeverse-backend.exe")
Copy-Item -Recurse (Join-Path $FrontendDir "out") (Join-Path $OutDir "ui")

Write-Host "Generating participant .env..."
python (Join-Path $BackendDir "scripts\build_event_env.py") `
    --event-pin $EventPin `
    --output (Join-Path $OutDir ".env")
if ($LASTEXITCODE -ne 0) { throw "build_event_env.py failed" }

Write-Host "Copying browser launchers..."
Copy-Item (Join-Path $LaunchersDir "Start-Tradeverse.bat") (Join-Path $OutDir "Start-Tradeverse.bat")
Copy-Item (Join-Path $LaunchersDir "Stop-Tradeverse.bat") (Join-Path $OutDir "Stop-Tradeverse.bat")

$audit = Join-Path $PSScriptRoot "audit-browser-participant-build.ps1"
if (Test-Path $audit) {
    & $audit $OutDir
    if ($LASTEXITCODE -ne 0) { throw "browser participant build audit failed" }
}

Write-Host ""
Write-Host "Windows browser participant package ready: $OutDir"
Write-Host "Distribute the TRADEVERSE folder. Participants double-click Start-Tradeverse.bat"
Write-Host "(Tauri desktop build remains available via Build-Participant.ps1 for future use.)"
