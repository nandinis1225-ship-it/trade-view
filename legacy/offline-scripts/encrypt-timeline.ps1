# Encrypt timeline for participant zip (organizer only)
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Backend = Join-Path $Root "backend"

if (-not $env:TIMELINE_DECRYPT_KEY) {
    Write-Host "TIMELINE_DECRYPT_KEY not set - script will generate one."
}

Push-Location $Backend
try {
    if (Test-Path ".venv\Scripts\python.exe") {
        $py = Join-Path $Backend ".venv\Scripts\python.exe"
    } else {
        $py = "py"
        $pyArgs = @("-3.13")
    }
    if ($py -eq "py") {
        try { & $py @pyArgs -m pip install cryptography -q } catch { }
        & $py @pyArgs scripts/encrypt_timeline.py
    } else {
        try { & $py -m pip install cryptography -q } catch { }
        & $py scripts/encrypt_timeline.py
    }
    if ($LASTEXITCODE -ne 0) {
        throw "encrypt_timeline.py failed with exit code $LASTEXITCODE"
    }
} finally {
    Pop-Location
}

Write-Host "Add TIMELINE_DECRYPT_KEY to organizer .env."
Write-Host "Announce the key at event start for participants."
