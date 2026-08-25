# Builds Tradeverse-Participant.zip for sharing with club members
param(
    [Parameter(Mandatory = $true)]
    [string]$TimelineKey,
    [Parameter(Mandatory = $true)]
    [string]$EventPin,
    [switch]$SkipRehearsal
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$OutDir = Join-Path $Root "dist-package"
$ZipPath = Join-Path $Root "Tradeverse-Participant.zip"
$FrontendDir = Join-Path $Root "frontend"

if (-not $SkipRehearsal) {
    $rehearsal = Join-Path $Root "scripts\dev\run-event-rehearsal.ps1"
    if (Test-Path $rehearsal) {
        Write-Host "Running developer rehearsal gate..."
        & $rehearsal
        if ($LASTEXITCODE -ne 0) { throw "developer rehearsal failed — use -SkipRehearsal to override" }
    }
}

$excludeNames = @(
    ".git", "node_modules", "__pycache__", ".next", ".venv",
    "dist-package", "leaderboard-data", "test-data", ".env", ".cursor", "logs"
)

$excludeFilePatterns = @("*.docx", "*News_Brief*")

$excludePaths = @(
    "backend\app\seed\tradeverse_timeline.json",
    "backend\tests",
    "leaderboard-collector",
    "EVENT-DAY.md",
    "DEPLOY-VERCEL.md",
    "Start-TRADEVERSE-Organizer.bat",
    "Build-Participant-Zip.bat",
    "scripts\offline\encrypt-timeline.ps1",
    "scripts\offline\build-share-package.ps1"
)

function ShouldExclude($relativePath, $name, $isDir) {
    if ($excludeNames -contains $name) { return $true }
    foreach ($pat in $excludeFilePatterns) {
        if ($name -like $pat) { return $true }
    }
    $norm = $relativePath -replace "/", "\"
    foreach ($p in $excludePaths) {
        if ($norm -eq $p -or $norm.StartsWith($p + "\")) { return $true }
    }
    return $false
}

function Copy-Tree($src, $dest, $relBase) {
    Get-ChildItem $src -Force | ForEach-Object {
        $rel = if ($relBase) { Join-Path $relBase $_.Name } else { $_.Name }
        if (ShouldExclude $rel $_.Name $_.PSIsContainer) { return }
        $target = Join-Path $dest $_.Name
        if ($_.PSIsContainer) {
            New-Item -ItemType Directory -Path $target -Force | Out-Null
            Copy-Tree $_.FullName $target $rel
        } else {
            Copy-Item $_.FullName $target
        }
    }
}

# Ensure encrypted timeline exists for participant package
$encPath = Join-Path $Root "backend\app\seed\tradeverse_timeline.enc"
if (-not (Test-Path $encPath)) {
    Write-Host "Encrypted timeline missing - running encrypt-timeline.ps1..."
    & (Join-Path $PSScriptRoot "encrypt-timeline.ps1")
}

if (Test-Path $OutDir) { Remove-Item $OutDir -Recurse -Force }
New-Item -ItemType Directory -Path $OutDir | Out-Null

Write-Host "Building static participant frontend..."
Push-Location $FrontendDir
if (-not (Test-Path "node_modules")) { npm install }
$env:PARTICIPANT_BUILD = "1"
npm run build
Pop-Location
if ($LASTEXITCODE -ne 0) { throw "frontend build failed" }

# Remove developer-only routes from participant static export
$pruneDirs = @("admin", "market-screen", "developer")
foreach ($dir in $pruneDirs) {
    $target = Join-Path $FrontendDir "out\$dir"
    if (Test-Path $target) {
        Write-Host "Pruning participant build: frontend/out/$dir"
        Remove-Item $target -Recurse -Force
    }
}

Copy-Tree $Root $OutDir ""
Copy-Item (Join-Path $Root "Start-TRADEVERSE.bat") (Join-Path $OutDir "Start-TRADEVERSE.bat") -ErrorAction SilentlyContinue
Copy-Item (Join-Path $Root "Start-TRADEVERSE-Participant.bat") (Join-Path $OutDir "Start-TRADEVERSE-Participant.bat") -ErrorAction SilentlyContinue
if (Test-Path (Join-Path $Root "PARTICIPANT-README.md")) {
    Copy-Item (Join-Path $Root "PARTICIPANT-README.md") (Join-Path $OutDir "PARTICIPANT-README.md")
}

$envScript = Join-Path $Root "backend\scripts\build_event_env.py"
$envOut = Join-Path $OutDir ".env"
python $envScript --timeline-key $TimelineKey --event-pin $EventPin --output $envOut
if ($LASTEXITCODE -ne 0) { throw "build_event_env.py failed" }

$runtimeOut = Join-Path $OutDir "frontend\public\tradeverse-runtime.json"
@'
{
  "apiUrl": "http://127.0.0.1:8765",
  "wsUrl": "ws://127.0.0.1:8765",
  "apiPrefix": "/api/v1",
  "localInstance": true,
  "participantEventMode": true,
  "pinRequired": true
}
'@ | Set-Content -Path $runtimeOut -Encoding UTF8

# Replace universe with participant-safe copy (no phase/IPO/dissolution schedule spoilers)
$sanitizeScript = Join-Path $Root "backend\scripts\sanitize_universe_for_participants.py"
$universeOut = Join-Path $OutDir "backend\app\seed\tradeverse_universe.json"
if (Test-Path $sanitizeScript) {
    Write-Host "Sanitizing tradeverse_universe.json for participant package..."
    python $sanitizeScript --output $universeOut
    if ($LASTEXITCODE -ne 0) {
        throw "sanitize_universe_for_participants.py failed"
    }
}

if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
Compress-Archive -Path (Join-Path $OutDir "*") -DestinationPath $ZipPath -Force

Write-Host "Created: $ZipPath"
Write-Host ""
Write-Host "Send participants: Tradeverse-Participant.zip"
Write-Host "Announce EVENT_PIN verbally at event start (also baked into each package)."
Write-Host "Requires on each laptop: Python 3.11-3.13 (Node only needed for organizer rebuilds)."
