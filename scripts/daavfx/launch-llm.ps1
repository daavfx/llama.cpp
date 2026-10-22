# launch-llm.ps1 - one-command launcher for the two proven LFM2.5-8B modes.
#
#   .\launch-llm.ps1 -Mode split      # MAX SPEED: dense on GTX, experts on CPU (18.9 t/s)
#   .\launch-llm.ps1 -Mode zerocpu    # ZERO-CPU: moe-cache + async uploads (14-17.5 t/s, CPU idle)
#   .\launch-llm.ps1 -Stop            # kill it (hygiene: never leave it running)
#
# The server is launched DETACHED (WMI), so it survives the shell that started
# it. -Stop kills the recorded pid AND whatever owns the listening port.
# Env: -Port (default 8083), -Model, -Ctx.

param(
    [ValidateSet('split','zerocpu')]
    [string]$Mode = 'split',
    [switch]$Stop,
    [int]$Port = 8083,
    [string]$Model = 'F:\DAAVILE_ECOSYSTEM\trading_ecosystem_11\trading_ecosystem_9.0\local_llm\GGUF\llm-collection\09-LFM2.5-8B-A1B\LFM2.5-8B-A1B-Q4_K_M.gguf',
    [string]$Server = 'F:\llvb\build_vulkan_bench\bin\Release\llama-server.exe',
    [int]$Ctx = 8192
)

$ErrorActionPreference = 'Continue'
$resultsDir = Join-Path $PSScriptRoot 'results'
$pidFile = Join-Path $resultsDir 'llm-server.pid'

if ($Stop) {
    $killed = $false
    if (Test-Path $pidFile) {
        $recorded = (Get-Content $pidFile -Raw).Trim()
        if (Get-Process -Id $recorded -ErrorAction SilentlyContinue) {
            Stop-Process -Id $recorded -Force -ErrorAction SilentlyContinue
            Write-Host "stopped recorded pid $recorded"
            $killed = $true
        }
        Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    }
    $owner = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
             Select-Object -First 1
    if ($owner) {
        Stop-Process -Id $owner.OwningProcess -Force -ErrorAction SilentlyContinue
        Write-Host "stopped port $Port owner pid $($owner.OwningProcess)"
        $killed = $true
    }
    if (-not $killed) { Write-Host "nothing was running on port $Port" }
    exit 0
}

if (-not (Test-Path $Server)) { Write-Host "server not found: $Server"; exit 2 }
if (-not (Test-Path $Model))  { Write-Host "model not found: $Model"; exit 2 }

$busy = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($busy) { Write-Host "port $Port already in use (pid $($busy.OwningProcess)) - use -Stop first"; exit 2 }

New-Item -ItemType Directory -Path $resultsDir -Force | Out-Null

$args = @('-m', "`"$Model`"", '-ngl', '99', '-t', '6', '--jinja', '-c', "$Ctx", '--port', "$Port", '--host', '127.0.0.1')
if ($Mode -eq 'split') {
    $args += @('-ncmoe', '24')
    $env:GGML_VK_ASYNC_USE_TRANSFER_QUEUE = $null
} else {
    $args += @('-ncmoe', '24', '--moe-cache-mib', '1536')
    $env:GGML_VK_ASYNC_USE_TRANSFER_QUEUE = '1'
}

$log = Join-Path $resultsDir "llm-$Mode-server.log"
$cmdline = "cmd /c `"set GGML_VK_ASYNC_USE_TRANSFER_QUEUE=$env:GGML_VK_ASYNC_USE_TRANSFER_QUEUE&& $Server $($args -join ' ') > `"$log`" 2>&1`""
$wmi = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmdline }
if ($wmi.ReturnValue -ne 0) { Write-Host "launch failed (rc $($wmi.ReturnValue))"; exit 1 }
$wmi.ProcessId | Set-Content $pidFile

$ok = $false
foreach ($i in 1..90) {
    Start-Sleep -Seconds 2
    try {
        $h = Invoke-RestMethod "http://127.0.0.1:$Port/health" -TimeoutSec 2
        if ($h.status -eq 'ok') { $ok = $true; break }
    } catch {}
}
if (-not $ok) {
    Write-Host "server did not become healthy in time; see $log"
    exit 1
}
$owner = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
         Select-Object -First 1
Write-Host "mode=$Mode port=$Port pid=$($owner.OwningProcess)  ->  http://127.0.0.1:$Port"
if ($Mode -eq 'split') {
    Write-Host "  dense layers on GTX 1650, experts on the 5600G (CPU busy), ~18.9 t/s"
} else {
    Write-Host "  moe-cache 1536 + async uploads, experts execute on GPU, CPU ~0%, ~14-17.5 t/s"
}
Write-Host "stop it with:  .\launch-llm.ps1 -Stop"
