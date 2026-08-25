# Audit participant package for forbidden content
$ErrorActionPreference = "Stop"
$Root = if ($args[0]) { $args[0] } else { (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path }
$failures = @()

$forbiddenPatterns = @(
    "EUPHORIA",
    "supabase.co",
    "current_phase",
    "tradeverse_timeline.json",
    "Start now",
    "30s countdown"
)

$scanPaths = @(
    (Join-Path $Root "frontend\out"),
    (Join-Path $Root "frontend\public\tradeverse-runtime.json"),
    (Join-Path $Root ".env")
)

foreach ($path in $scanPaths) {
    if (-not (Test-Path $path)) { continue }
    if ((Get-Item $path).PSIsContainer) {
        Get-ChildItem $path -Recurse -File | ForEach-Object {
            $content = Get-Content $_.FullName -Raw -ErrorAction SilentlyContinue
            if (-not $content) { return }
            foreach ($pat in $forbiddenPatterns) {
                if ($content -match $pat) {
                    $failures += "$($_.FullName): contains '$pat'"
                }
            }
        }
    } else {
        $content = Get-Content $path -Raw
        foreach ($pat in $forbiddenPatterns) {
            if ($content -match $pat) {
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
