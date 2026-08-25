# Audit browser-based TRADEVERSE participant package
$ErrorActionPreference = "Stop"
$Root = if ($args[0]) { $args[0] } else { (Resolve-Path (Join-Path $PSScriptRoot "..\..\participant-build\windows\TRADEVERSE")).Path }
$failures = @()

$requiredFiles = @(
    "Start-Tradeverse.bat",
    "Stop-Tradeverse.bat",
    "tradeverse-backend.exe",
    "ui\terminal\index.html"
)

$forbiddenPatterns = @(
    "TIMELINE_DECRYPT_KEY",
    "tradeverse_timeline.json",
    "tradeverse_timeline.baked.json",
    "mse_dev.db",
    "SUPABASE",
    "supabase.co",
    "railway.app",
    "leaderboard",
    "EUPHORIA",
    "CRASH",
    "RECOVERY",
    "PHASE 1",
    "PHASE 2",
    "PHASE 3",
    "PHASE 4",
    "AI_TICK",
    "sector_impacts",
    "effective_impact",
    "stop_loss",
    "take_profit",
    "current_phase",
    "OrganizerDebugPanel",
    "/developer",
    "adminLogin"
)

$forbiddenDirs = @("admin", "market-screen", "developer")
$forbiddenDbPatterns = @("mse_dev.db", "mse_dev.db-shm", "mse_dev.db-wal")

foreach ($file in $requiredFiles) {
    $path = Join-Path $Root $file
    if (-not (Test-Path $path)) {
        $failures += "Missing required file: $file"
    }
}

foreach ($pat in $forbiddenDbPatterns) {
    $matches = Get-ChildItem $Root -Recurse -Filter $pat -ErrorAction SilentlyContinue
    if ($matches) {
        $failures += "Development database must not be shipped: $pat"
    }
}

$scanPaths = @(
    (Join-Path $Root "ui"),
    (Join-Path $Root ".env"),
    (Join-Path $Root "Start-Tradeverse.bat"),
    (Join-Path $Root "Stop-Tradeverse.bat")
)

foreach ($path in $scanPaths) {
    if (-not (Test-Path $path)) { continue }
    if ((Get-Item $path).PSIsContainer) {
        foreach ($dir in $forbiddenDirs) {
            $bad = Join-Path $path $dir
            if (Test-Path $bad) {
                $failures += "$bad`: forbidden route directory"
            }
        }
        Get-ChildItem $path -Recurse -File | ForEach-Object {
            $content = Get-Content $_.FullName -Raw -ErrorAction SilentlyContinue
            if (-not $content) { return }
            foreach ($pat in $forbiddenPatterns) {
                if ($content -match [regex]::Escape($pat)) {
                    $failures += "$($_.FullName): contains '$pat'"
                }
            }
        }
    } else {
        $content = Get-Content $path -Raw
        foreach ($pat in $forbiddenPatterns) {
            if ($content -match [regex]::Escape($pat)) {
                $failures += "$path`: contains '$pat'"
            }
        }
    }
}

if ($failures.Count -gt 0) {
    Write-Host "BROWSER PACKAGE AUDIT FAILED" -ForegroundColor Red
    $failures | ForEach-Object { Write-Host "  $_" }
    exit 1
}

Write-Host "BROWSER PACKAGE AUDIT PASSED" -ForegroundColor Green
