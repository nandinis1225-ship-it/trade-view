# Run full event rehearsal gate before building participant package.
param(
    [int]$Speed = 60,
    [switch]$SkipRehearsal
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$backendDir = Join-Path $Root "backend"
$venvPython = Join-Path $backendDir ".venv\Scripts\python.exe"

if ($SkipRehearsal) {
    Write-Host "Skipping developer rehearsal (-SkipRehearsal)"
    exit 0
}

if (-not (Test-Path $venvPython)) {
    Write-Host "Backend venv missing - run developer-launch.bat once or create .venv"
    exit 1
}

$env:DEVELOPER_MODE = "true"
$env:LOCAL_INSTANCE_MODE = "true"
$env:DATABASE_URL = "sqlite+pysqlite:///:memory:"
$env:SIMULATION_SPEED = "$Speed"

$gateTests = @(
    "tests/test_phase5_accelerated_rehearsal.py",
    "tests/test_phase5_gates.py",
    "tests/test_phase3_validation.py",
    "tests/test_recovery.py",
    "tests/test_participant_privacy.py",
    "tests/test_event_mode.py",
    "tests/test_pin_security.py",
    "tests/test_identity_lock.py",
    "tests/test_dissolution.py",
    "tests/test_developer_mode_gating.py",
    "tests/test_cross_sector_news.py"
)

Push-Location $backendDir
& $venvPython -m pytest @gateTests -q
$code = $LASTEXITCODE
Pop-Location

if ($code -ne 0) {
    Write-Host "Developer rehearsal gate FAILED at $($Speed)x speed profile." -ForegroundColor Red
    exit $code
}

Write-Host "Developer rehearsal gate PASSED at $($Speed)x speed profile." -ForegroundColor Green
exit 0
