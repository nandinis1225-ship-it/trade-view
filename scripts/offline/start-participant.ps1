$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $Root

function Get-PyLauncherVersions() {
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $out = & py -0p 2>$null
    $ErrorActionPreference = $prev
    $versions = @()
    foreach ($line in $out) {
        if ($line -match '-V:([\d.]+)') {
            $versions += $Matches[1]
        }
    }
    return $versions
}

function Require-Command([string]$name, [string]$installHint) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
        Write-Host ""
        Write-Host "ERROR: '$name' not found." -ForegroundColor Red
        Write-Host $installHint
        exit 1
    }
}

function Resolve-PythonForVenv {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $available = @(Get-PyLauncherVersions)
        $preferred = @("3.12", "3.13", "3.11", "3.10")
        foreach ($ver in $preferred) {
            if ($available -contains $ver) {
                return @{ Mode = "py"; VersionTag = $ver }
            }
        }
        foreach ($ver in $available) {
            if ($ver -ne "3.14") {
                return @{ Mode = "py"; VersionTag = $ver }
            }
        }
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $prev = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        $ver = (& python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')").Trim()
        $ErrorActionPreference = $prev
        if ($ver -ne "3.14") {
            return @{ Mode = "exe"; Exe = (Get-Command python).Source; VersionTag = $ver }
        }
    }
    return $null
}

function Resolve-PythonExecutable([hashtable]$Python) {
    if ($Python.Executable -and (Test-Path $Python.Executable)) {
        return $Python.Executable
    }
    if ($Python.Mode -eq "exe" -and $Python.Exe) {
        $exe = $Python.Exe.Trim()
        if (Test-Path $exe) { return $exe }
    }
    if ($Python.Mode -eq "py" -and $Python.VersionTag) {
        $ver = $Python.VersionTag.Trim()
        $prev = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        $exe = (& py "-$ver" -c "import sys; print(sys.executable)" 2>$null | Out-String).Trim()
        $ErrorActionPreference = $prev
        if ($exe -and (Test-Path $exe)) { return $exe }
    }
    return $null
}

function Assert-InstallPathWarnings([string]$Path) {
    $warnings = @()
    if ($Path -match 'WhatsApp|\\Packages\\|\\transfers\\|\\LocalState\\sessions\\') {
        $warnings += "Folder is inside WhatsApp transfers (paths are too long/restricted for Python)."
    }
    if ($Path -match '[()]') {
        $warnings += "Folder path contains parentheses."
    }
    if ($Path.Length -gt 100) {
        $warnings += "Folder path is very long ($($Path.Length) characters)."
    }
    return $warnings
}

function Get-ParticipantVenvPath() {
    $parent = Join-Path $env:LOCALAPPDATA "Tradeverse"
    if (-not (Test-Path $parent)) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }
    return Join-Path $parent "backend-venv"
}

function Bootstrap-PipInVenv([string]$BasePy, [string]$VenvPy, [string]$VenvPath) {
    $prevEa = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $out = & $VenvPy -m ensurepip --upgrade --default-pip 2>&1
    $ok = $LASTEXITCODE -eq 0 -and (Test-VenvHealthy $VenvPath)
    if ($ok) {
        $ErrorActionPreference = $prevEa
        return @{ Ok = $true; Error = "" }
    }
    Write-Host "ensurepip failed; bootstrapping pip from system Python..." -ForegroundColor Yellow
    $boot = & $BasePy -m pip install --python $VenvPy pip setuptools wheel 2>&1
    $ok = $LASTEXITCODE -eq 0 -and (Test-VenvHealthy $VenvPath)
    $ErrorActionPreference = $prevEa
    if ($ok) { return @{ Ok = $true; Error = "" } }
    $err = (($out | Out-String) + "`n" + ($boot | Out-String)).Trim()
    return @{ Ok = $false; Error = $err }
}

function Create-PythonVenv([string]$BasePy, [string]$VenvPath) {
    $prevEa = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $venvPy = Get-VenvPythonExe $VenvPath
    $allErr = ""

    $out1 = Invoke-PythonModule $BasePy "venv" @($VenvPath) 2>&1
    if ($LASTEXITCODE -eq 0 -and (Test-Path $venvPy) -and (Test-VenvHealthy $VenvPath)) {
        $ErrorActionPreference = $prevEa
        return @{ Ok = $true; Error = "" }
    }
    $allErr += ($out1 | Out-String)

    if (Test-Path $VenvPath) { Remove-VenvSafe $VenvPath }
    Write-Host "Retrying venv without bundled pip..." -ForegroundColor Yellow
    $out2 = Invoke-PythonModule $BasePy "venv" @("--without-pip", $VenvPath) 2>&1
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $venvPy)) {
        $allErr += "`n" + ($out2 | Out-String)
        $ErrorActionPreference = $prevEa
        return @{ Ok = $false; Error = $allErr.Trim() }
    }

    $boot = Bootstrap-PipInVenv $BasePy $venvPy $VenvPath
    if ($boot.Ok) {
        $ErrorActionPreference = $prevEa
        return @{ Ok = $true; Error = "" }
    }
    $allErr += "`n" + $boot.Error
    $ErrorActionPreference = $prevEa
    return @{ Ok = $false; Error = $allErr.Trim() }
}

function Write-DebugLog([string]$HypothesisId, [string]$Location, [string]$Message, [hashtable]$Data) {
    # #region agent log
    try {
        $logPath = Join-Path $Root "debug-ac2555.log"
        $entry = @{
            sessionId    = "ac2555"
            hypothesisId = $HypothesisId
            location     = $Location
            message      = $Message
            data         = $Data
            timestamp    = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
        }
        ($entry | ConvertTo-Json -Compress) | Add-Content -Path $logPath -Encoding UTF8
    } catch { }
    # #endregion
}

function Invoke-PythonModule([string]$PythonExe, [string]$Module, [string[]]$ModuleArgs) {
    $args = @("-m", $Module) + $ModuleArgs
    Write-DebugLog "F" "Invoke-PythonModule" "argv" @{
        pythonExe = $PythonExe
        args      = $args
    }
    & $PythonExe @args
}

function Get-VenvPythonExe([string]$VenvPath) {
    return Join-Path $VenvPath "Scripts\python.exe"
}

function Test-VenvHealthy([string]$VenvPath) {
    $py = Get-VenvPythonExe $VenvPath
    if (-not (Test-Path $py)) { return $false }
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & $py -c "import pip" 2>$null
    $ok = $LASTEXITCODE -eq 0
    $ErrorActionPreference = $prev
    return $ok
}

function Get-VenvPythonVersion([string]$VenvPath) {
    $py = Get-VenvPythonExe $VenvPath
    if (-not (Test-Path $py)) { return $null }
    return (& $py -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')").Trim()
}

function Stop-StaleTradeverse {
    foreach ($port in @("8765", "3000")) {
        $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
        foreach ($c in $conns) {
            Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue
        }
    }
    Get-Job -ErrorAction SilentlyContinue | Stop-Job -ErrorAction SilentlyContinue
    Get-Job -ErrorAction SilentlyContinue | Remove-Job -Force -ErrorAction SilentlyContinue
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -match '^(python|pythonw|node)\.exe$' -and
            $_.ExecutablePath -and
            ($_.ExecutablePath -like '*Tradeverse*' -or $_.ExecutablePath -like '*mocktraderlocal*' -or $_.ExecutablePath -like '*\Tradeverse\backend-venv*')
        } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 2
}

function Remove-VenvSafe([string]$VenvPath) {
    Stop-StaleTradeverse
    $bak = "$VenvPath.old"
    if (Test-Path $bak) {
        Remove-Item $bak -Recurse -Force -ErrorAction SilentlyContinue
    }
    if (Test-Path $VenvPath) {
        try {
            Move-Item $VenvPath $bak -Force
            Remove-Item $bak -Recurse -Force -ErrorAction SilentlyContinue
        } catch {
            Remove-Item $VenvPath -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
}

function Ensure-PythonVenv(
    [hashtable]$Python,
    [string]$BackendDir,
    [string]$VenvPath,
    [string]$TargetVer
) {
    $requirements = Join-Path $BackendDir "requirements.txt"
    for ($attempt = 1; $attempt -le 2; $attempt++) {
        Stop-StaleTradeverse
        $venvPy = Get-VenvPythonExe $VenvPath
        $uvicornExe = Join-Path $VenvPath "Scripts\uvicorn.exe"

        if (Test-Path $VenvPath) {
            $healthy = Test-VenvHealthy $VenvPath
            $venvVer = Get-VenvPythonVersion $VenvPath
            Write-DebugLog "B" "Ensure-PythonVenv:existing" "venv state before create" @{
                attempt = $attempt
                venvExists = $true
                healthy = $healthy
                venvVer = $venvVer
                targetVer = $TargetVer
                hasUvicorn = (Test-Path $uvicornExe)
            }
            if (-not $healthy) {
                Write-Host "Removing incomplete Python environment..." -ForegroundColor Yellow
                Remove-VenvSafe $VenvPath
            } elseif ($venvVer -eq "3.14" -or ($TargetVer -and $venvVer -and $venvVer -ne $TargetVer)) {
                Write-Host "Recreating Python environment (was $venvVer, need $TargetVer)..." -ForegroundColor Yellow
                Remove-VenvSafe $VenvPath
            }
        } else {
            Write-DebugLog "B" "Ensure-PythonVenv:missing" "no venv folder" @{ attempt = $attempt }
        }

        if (-not (Test-Path $VenvPath)) {
            Write-Host "Creating Python environment (attempt $attempt)..." -ForegroundColor Yellow
            $basePy = Resolve-PythonExecutable $Python
            if (-not $basePy) {
                Write-Host "Could not resolve Python executable for venv." -ForegroundColor Red
                return @{ Ok = $false; UvicornExe = $null; PythonExe = $null }
            }
            $Python.Executable = $basePy
            Write-DebugLog "C" "Ensure-PythonVenv:create" "creating venv" @{
                basePy   = $basePy
                venvPath = $VenvPath
                root     = $Root
            }
            $created = Create-PythonVenv $basePy $VenvPath
            Write-DebugLog "A" "Ensure-PythonVenv:after-create" "venv create result" @{
                ok         = $created.Ok
                stderr     = $created.Error
                venvPyExists = (Test-Path $venvPy)
                healthy    = (Test-VenvHealthy $VenvPath)
            }
            if (-not $created.Ok -or -not (Test-Path $venvPy)) {
                Write-Host "Python venv creation failed." -ForegroundColor Red
                if ($created.Error) { Write-Host $created.Error }
                if ($attempt -lt 2) {
                    Remove-VenvSafe $VenvPath
                    continue
                }
                return @{ Ok = $false; UvicornExe = $null; PythonExe = $null }
            }
        }

        Write-Host "Checking Python dependencies..."
        Write-DebugLog "D" "Ensure-PythonVenv:pip" "install deps" @{
            venvPy = $venvPy
            venvPyExists = (Test-Path $venvPy)
            requirements = $requirements
        }
        $prevEa = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        & $venvPy -m pip install -q -r "$requirements"
        $pipOk = $LASTEXITCODE -eq 0
        $ErrorActionPreference = $prevEa
        $hasUvicorn = Test-Path $uvicornExe

        Write-DebugLog "E" "Ensure-PythonVenv:after-pip" "pip result" @{
            pipOk = $pipOk
            hasUvicorn = $hasUvicorn
        }

        if ($pipOk -and $hasUvicorn) {
            return @{ Ok = $true; UvicornExe = $uvicornExe; PythonExe = $venvPy }
        }

        if ($attempt -lt 2) {
            Write-Host "Install blocked or incomplete. Cleaning up and retrying..." -ForegroundColor Yellow
            Remove-VenvSafe $VenvPath
        }
    }
    return @{ Ok = $false; UvicornExe = $null; PythonExe = $null }
}

Clear-Host
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  TRADEVERSE - starting..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Require-Command "node" "Install Node.js 20+ from https://nodejs.org then run this again."
$python = Resolve-PythonForVenv
Write-DebugLog "C" "start:python-resolve" "resolved python" @{
    found = ($null -ne $python)
    mode = if ($python) { $python.Mode } else { $null }
    versionTag = if ($python) { $python.VersionTag } else { $null }
    exe = if ($python -and $python.Exe) { $python.Exe } else { $null }
    pyVersions = @(Get-PyLauncherVersions)
}
if (-not $python) {
    Write-Host "ERROR: Need Python 3.11, 3.12, or 3.13 (not 3.14)." -ForegroundColor Red
    Write-Host "You have Python 3.14 as default. Install 3.12 from https://www.python.org/downloads/"
    Write-Host "Or ensure Anaconda 3.13 is available: py -3.13"
    exit 1
}
if ($python.VersionTag) {
    Write-Host "Using Python $($python.VersionTag)"
}
$pythonExe = Resolve-PythonExecutable $python
Write-DebugLog "C" "start:python-exe" "resolved executable" @{
    pythonExe = $pythonExe
    root      = $Root
    rootHasParen = ($Root -match '[()]')
}
if (-not $pythonExe) {
    Write-Host "ERROR: Could not find Python executable." -ForegroundColor Red
    exit 1
}
$python.Executable = $pythonExe
$pathWarnings = Assert-InstallPathWarnings $Root
if ($pathWarnings.Count -gt 0) {
    Write-Host ""
    Write-Host "NOTE: Game folder location may cause issues:" -ForegroundColor Yellow
    foreach ($w in $pathWarnings) { Write-Host "  - $w" -ForegroundColor Yellow }
    Write-Host "  Python packages install to: $(Get-ParticipantVenvPath)" -ForegroundColor Yellow
    Write-Host "  For best results, still move the game folder to C:\Tradeverse" -ForegroundColor Yellow
    Write-Host ""
}

& $PSScriptRoot\ensure-env.ps1 -Root $Root

Stop-StaleTradeverse

$BackendDir = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend"

# Backend venv lives outside the game folder (avoids WhatsApp/long-path ensurepip failures)
$Venv = Get-ParticipantVenvPath
Write-Host "Python environment: $Venv"
$targetVer = $python.VersionTag
$venvResult = Ensure-PythonVenv -Python $python -BackendDir $BackendDir -VenvPath $Venv -TargetVer $targetVer
if (-not $venvResult.Ok) {
    Write-Host ""
    Write-Host "ERROR: Python packages failed to install." -ForegroundColor Red
    Write-Host "Close all TRADEVERSE windows and try again."
    Read-Host "Press Enter to close"
    exit 1
}
$uvicornExe = $venvResult.UvicornExe
$pythonExe = $venvResult.PythonExe

# Load .env into this process so init_db sees LOCAL_INSTANCE_MODE + SQLite path
Get-Content (Join-Path $Root ".env") | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
        Set-Item -Path "env:$($matches[1].Trim())" -Value $matches[2].Trim()
    }
}
if ($env:LOCAL_INSTANCE_MODE -eq "true") {
    Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
}
$env:PYTHONPATH = $BackendDir
Write-Host "Initializing local database..."
& $pythonExe -c "from app.core.database import init_db; init_db(); print('Database ready')"
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Could not initialize database." -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 1
}

$Port = if ($env:BACKEND_PORT) { $env:BACKEND_PORT } else { "8765" }
$eventMode = ($env:PARTICIPANT_EVENT_MODE -eq "true")
$serveStatic = ($env:SERVE_STATIC_UI -eq "true") -or $eventMode
$terminalUrl = if ($serveStatic) { "http://127.0.0.1:$Port/terminal" } else { "http://127.0.0.1:3000/terminal" }
$marketUrl = "https://frontend-azure-three-51.vercel.app/market-screen"

if ($serveStatic -and -not (Test-Path (Join-Path $FrontendDir "out\terminal\index.html")) -and -not (Test-Path (Join-Path $FrontendDir "out\terminal.html"))) {
    Write-Host "Building static frontend (one-time)..." -ForegroundColor Yellow
    if (-not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
        Push-Location $FrontendDir
        npm install
        Pop-Location
    }
    Push-Location $FrontendDir
    $env:PARTICIPANT_BUILD = "1"
    npm run build
    Pop-Location
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Frontend build failed." -ForegroundColor Red
        Read-Host "Press Enter to close"
        exit 1
    }
}

# Frontend deps (dev mode only)
if (-not $serveStatic -and -not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
    Write-Host "First run: installing Node packages (3-8 min)..." -ForegroundColor Yellow
    Push-Location $FrontendDir
    npm install
    Pop-Location
}

$LogsDir = Join-Path $Root "logs"
New-Item -ItemType Directory -Force -Path $LogsDir | Out-Null
$backendLog = Join-Path $LogsDir "backend.log"
$backendErr = Join-Path $LogsDir "backend.err"
$frontendLog = Join-Path $LogsDir "frontend.log"
$frontendErr = Join-Path $LogsDir "frontend.err"

$env:PYTHONPATH = $BackendDir
$backendProc = Start-Process -FilePath $uvicornExe -ArgumentList @(
    "app.main:app", "--host", "127.0.0.1", "--port", $Port, "--workers", "1"
) -WorkingDirectory $BackendDir -RedirectStandardOutput $backendLog -RedirectStandardError $backendErr -PassThru -WindowStyle Hidden

$frontendProc = $null
if (-not $serveStatic) {
    $frontendProc = Start-Process -FilePath "cmd.exe" -ArgumentList @(
        "/c", "npm run dev -- --hostname 127.0.0.1 --port 3000"
    ) -WorkingDirectory $FrontendDir -RedirectStandardOutput $frontendLog -RedirectStandardError $frontendErr -PassThru -WindowStyle Hidden
}

Write-Host "Waiting for backend on port $Port..."
$healthOk = $false
for ($i = 0; $i -lt 90; $i++) {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/api/v1/health" -UseBasicParsing -TimeoutSec 2
        if ($r.StatusCode -eq 200) { $healthOk = $true; break }
    } catch { }
    Start-Sleep -Seconds 1
    if ($i % 5 -eq 4) { Write-Host "  still starting..." }
}

if (-not $healthOk) {
    Write-Host "Backend failed to start. See logs\backend.log" -ForegroundColor Red
    if ($backendProc -and -not $backendProc.HasExited) { Stop-Process -Id $backendProc.Id -Force -ErrorAction SilentlyContinue }
    if ($frontendProc -and -not $frontendProc.HasExited) { Stop-Process -Id $frontendProc.Id -Force -ErrorAction SilentlyContinue }
    Read-Host "Press Enter to close"
    exit 1
}

Write-Host "Waiting for frontend..."
$frontOk = $serveStatic
if (-not $serveStatic) {
    for ($i = 0; $i -lt 90; $i++) {
        try {
            $r = Invoke-WebRequest -Uri "http://127.0.0.1:3000" -UseBasicParsing -TimeoutSec 2
            if ($r.StatusCode -eq 200) { $frontOk = $true; break }
        } catch { }
        Start-Sleep -Seconds 1
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  TRADEVERSE is running" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Trade here:  $terminalUrl"
if (-not $eventMode) {
    Write-Host "  Projector (organizer only): http://127.0.0.1:3000/market-screen?organizer=finclub123"
    Write-Host "  Projector (leaderboard only, any device): $marketUrl"
    Write-Host ""
    Write-Host "  Enter your name, then Start when ready."
} else {
    Write-Host ""
    Write-Host "  Enter the event PIN when prompted. The simulation starts automatically."
}
Write-Host "  Close this window to stop the game."
Write-Host ""

Start-Process $terminalUrl

try {
    while ($true) { Start-Sleep -Seconds 2 }
} finally {
    Write-Host "Stopping..."
    if ($backendProc -and -not $backendProc.HasExited) {
        Stop-Process -Id $backendProc.Id -Force -ErrorAction SilentlyContinue
    }
    if ($frontendProc -and -not $frontendProc.HasExited) {
        Stop-Process -Id $frontendProc.Id -Force -ErrorAction SilentlyContinue
    }
    Stop-StaleTradeverse
}
