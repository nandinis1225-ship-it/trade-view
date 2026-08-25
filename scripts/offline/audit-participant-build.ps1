# Audit participant package for forbidden content
$ErrorActionPreference = "Stop"
$Root = if ($args[0]) { $args[0] } else { (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path }
$failures = @()

$forbiddenPatterns = @(
    "TIMELINE_DECRYPT_KEY",
    "tradeverse_timeline.json",
    "tradeverse_timeline.baked.json",
    "tradeverse_timeline.pkg",
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
    "MARKET_PULSE",
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

$scanPaths = @(
    (Join-Path $Root "ui"),
    (Join-Path $Root ".env")
)

foreach ($path in $scanPaths) {
    if (-not (Test-Path $path)) { continue }
    if ((Get-Item $path).PSIsContainer) {
        foreach ($dir in $forbiddenDirs) {
            $bad = Join-Path $path $dir
            if (Test-Path $bad) {
                $failures += "$bad`: developer route directory must not exist in participant build"
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
    Write-Host "AUDIT FAILED" -ForegroundColor Red
    $failures | ForEach-Object { Write-Host "  $_" }
    exit 1
}

Write-Host "AUDIT PASSED" -ForegroundColor Green
