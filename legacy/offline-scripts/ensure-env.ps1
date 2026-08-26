# Merge offline defaults with existing .env (your Supabase keys and overrides are kept).
param(
    [string]$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
)

$ErrorActionPreference = "Stop"
$templatePath = Join-Path $Root ".env.offline-participant.example"
$envPath = Join-Path $Root ".env"

if (-not (Test-Path $templatePath)) {
    throw "Missing template: $templatePath"
}

function Read-EnvMap([string]$path) {
    $map = [ordered]@{}
    if (-not (Test-Path $path)) { return $map }
    foreach ($line in Get-Content $path -Encoding UTF8) {
        if ($line -match '^\s*([^#][^=]+)=(.*)$') {
            $map[$matches[1].Trim()] = $matches[2].Trim()
        }
    }
    return $map
}

$defaults = Read-EnvMap $templatePath
$user = Read-EnvMap $envPath
$merged = [ordered]@{}

foreach ($key in $defaults.Keys) {
    if ($user.Contains($key) -and -not [string]::IsNullOrWhiteSpace($user[$key])) {
        $merged[$key] = $user[$key]
    } else {
        $merged[$key] = $defaults[$key]
    }
}

foreach ($key in $user.Keys) {
    if (-not $merged.Contains($key)) {
        $merged[$key] = $user[$key]
    }
}

# Mirror Supabase keys so backend + Next.js always agree
if ($merged.Contains("SUPABASE_URL") -and -not [string]::IsNullOrWhiteSpace($merged["SUPABASE_URL"])) {
    if (-not $merged.Contains("NEXT_PUBLIC_SUPABASE_URL") -or [string]::IsNullOrWhiteSpace($merged["NEXT_PUBLIC_SUPABASE_URL"])) {
        $merged["NEXT_PUBLIC_SUPABASE_URL"] = $merged["SUPABASE_URL"]
    }
}
if ($merged.Contains("SUPABASE_ANON_KEY") -and -not [string]::IsNullOrWhiteSpace($merged["SUPABASE_ANON_KEY"])) {
    if (-not $merged.Contains("NEXT_PUBLIC_SUPABASE_ANON_KEY") -or [string]::IsNullOrWhiteSpace($merged["NEXT_PUBLIC_SUPABASE_ANON_KEY"])) {
        $merged["NEXT_PUBLIC_SUPABASE_ANON_KEY"] = $merged["SUPABASE_ANON_KEY"]
    }
}
if ($merged.Contains("NEXT_PUBLIC_SUPABASE_URL") -and -not [string]::IsNullOrWhiteSpace($merged["NEXT_PUBLIC_SUPABASE_URL"])) {
    if (-not $merged.Contains("SUPABASE_URL") -or [string]::IsNullOrWhiteSpace($merged["SUPABASE_URL"])) {
        $merged["SUPABASE_URL"] = $merged["NEXT_PUBLIC_SUPABASE_URL"]
    }
}
if ($merged.Contains("NEXT_PUBLIC_SUPABASE_ANON_KEY") -and -not [string]::IsNullOrWhiteSpace($merged["NEXT_PUBLIC_SUPABASE_ANON_KEY"])) {
    if (-not $merged.Contains("SUPABASE_ANON_KEY") -or [string]::IsNullOrWhiteSpace($merged["SUPABASE_ANON_KEY"])) {
        $merged["SUPABASE_ANON_KEY"] = $merged["NEXT_PUBLIC_SUPABASE_ANON_KEY"]
    }
}
if (-not $merged.Contains("SUPABASE_LEADERBOARD_TABLE") -or [string]::IsNullOrWhiteSpace($merged["SUPABASE_LEADERBOARD_TABLE"])) {
    $merged["SUPABASE_LEADERBOARD_TABLE"] = "participant_snapshots"
}
if (-not $merged.Contains("NEXT_PUBLIC_SUPABASE_LEADERBOARD_TABLE") -or [string]::IsNullOrWhiteSpace($merged["NEXT_PUBLIC_SUPABASE_LEADERBOARD_TABLE"])) {
    $merged["NEXT_PUBLIC_SUPABASE_LEADERBOARD_TABLE"] = $merged["SUPABASE_LEADERBOARD_TABLE"]
}

$lines = @("# TRADEVERSE offline participant - auto-merged $(Get-Date -Format 'yyyy-MM-dd HH:mm')")
foreach ($pair in $merged.GetEnumerator()) {
    $lines += "$($pair.Key)=$($pair.Value)"
}
Set-Content -Path $envPath -Value $lines -Encoding UTF8

# Next.js reads frontend/.env.local — sync public vars there
$frontendEnv = Join-Path $Root "frontend\.env.local"
$publicLines = @()
foreach ($pair in $merged.GetEnumerator()) {
    if ($pair.Key.StartsWith("NEXT_PUBLIC_")) {
        $publicLines += "$($pair.Key)=$($pair.Value)"
    }
}
Set-Content -Path $frontendEnv -Value $publicLines -Encoding UTF8

$runtimePath = Join-Path $Root "frontend\public\tradeverse-runtime.json"
$runtime = @{
    apiUrl                   = $merged["NEXT_PUBLIC_API_URL"]
    wsUrl                    = $merged["NEXT_PUBLIC_WS_URL"]
    apiPrefix                = $merged["NEXT_PUBLIC_API_PREFIX"]
    supabaseUrl              = $merged["NEXT_PUBLIC_SUPABASE_URL"]
    supabaseAnonKey          = $merged["NEXT_PUBLIC_SUPABASE_ANON_KEY"]
    supabaseLeaderboardTable = $merged["NEXT_PUBLIC_SUPABASE_LEADERBOARD_TABLE"]
    localInstance            = $true
}
$runtime | ConvertTo-Json -Compress | Set-Content -Path $runtimePath -Encoding UTF8

Write-Host "Environment ready (.env + frontend/.env.local + runtime config)"
