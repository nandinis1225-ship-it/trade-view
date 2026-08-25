# Run full event rehearsal in developer mode before building participant package.
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
    Write-Host "Backend venv missing — run developer-launch.bat once or create .venv"
    exit 1
}

$env:DEVELOPER_MODE = "true"
$env:LOCAL_INSTANCE_MODE = "true"
$env:DATABASE_URL = "sqlite+pysqlite:///:memory:"
$env:SIMULATION_SPEED = "$Speed"

Push-Location $backendDir
& $venvPython -m pytest tests/test_developer_mode_gating.py tests/test_checkpoint_jump.py -q
$code = $LASTEXITCODE
Pop-Location

if ($code -ne 0) {
    Write-Host "Developer rehearsal tests FAILED — fix before building participant package." -ForegroundColor Red
    exit $code
}

Write-Host "Developer rehearsal tests PASSED at ${Speed}x speed profile." -ForegroundColor Green
exit 0
