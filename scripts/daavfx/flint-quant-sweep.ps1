# flint-quant-sweep.ps1 - quality + MT5 agent bench for a list of Flint quants.
# Phase 1: start a server, run the 12-task quality harness, score.
# Phase 2: run the MT5 MCP agent benchmark through run-flint-bench.ps1.
# Writes one summary JSON. Nothing runs until this script is invoked.
param(
    [string[]] $Quants = @('Q2_K_XL', 'IQ3_XXS', 'Q3_K_XL'),
    [string] $ModelsDir = '',
    [int] $QualityPort = 8083,
    [int] $QualityCtx = 8192,
    [int] $Ngl = 99,
    [int] $Threads = 6,
    [int] $NcMoe = 24,
    [int] $MoeCacheMib = 1024,
    [switch] $SkipQuality,
    [switch] $SkipBench
)

$ErrorActionPreference = 'Stop'

$eco = Split-Path (Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent) -Parent
if (-not $ModelsDir) { $ModelsDir = Join-Path $eco 'local_llm\GGUF\llm-collection\21-flint' }
$server = Join-Path $eco 'shared\llama.cpp-flint-wt\build_flint\bin\Release\llama-server.exe'
$harness = Join-Path $PSScriptRoot 'quality-harness\run-harness.ps1'
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$outDir = Join-Path $PSScriptRoot 'results'
New-Item -ItemType Directory -Path $outDir -Force | Out-Null
$summaryPath = Join-Path $outDir "flint-sweep-$stamp.json"

function Wait-Health([int] $port, [int] $tries) {
    for ($i = 0; $i -lt $tries; $i++) {
        Start-Sleep -Seconds 2
        try {
            $h = Invoke-WebRequest -Uri "http://127.0.0.1:$port/health" -UseBasicParsing -TimeoutSec 3
            if ($h.StatusCode -eq 200) { return $true }
        } catch { }
    }
    return $false
}

$rows = @()
foreach ($q in $Quants) {
    Write-Host "`n=== $q ==="
    $hits = @(Get-ChildItem -LiteralPath $ModelsDir -Filter "*$q*.gguf" -File -ErrorAction SilentlyContinue)
    if ($hits.Count -eq 0) {
        Write-Host "missing: $q (run fetch-flint-gguf.ps1 -Quant $q)"
        $rows += @{ quant = $q; status = 'missing' }
        continue
    }
    $firstShards = @($hits | Where-Object { $_.Name -match '-00001-of-\d{5}\.gguf$' })
    if ($firstShards.Count -eq 1) {
        $model = $firstShards[0].FullName
    } elseif ($hits.Count -eq 1) {
        $model = $hits[0].FullName
    } else {
        $names = ($hits | ForEach-Object { $_.Name }) -join ', '
        throw "ambiguous '$q': $names (pass a single quant or remove stale files)"
    }
    $tag = 'flint-' + $q
    $row = @{ quant = $q; model = $model; quality = $null; bench = $null }

    if (-not $SkipQuality) {
        if (-not (Test-Path -LiteralPath $server)) { throw "server not found: $server (run build-flint-llama.ps1)" }
        $busy = $false
        try { Invoke-WebRequest -Uri "http://127.0.0.1:$QualityPort/health" -UseBasicParsing -TimeoutSec 2 | Out-Null; $busy = $true } catch { }
        if ($busy) { throw "port $QualityPort already serving" }
        $srvArgs = @('-m', $model, '-c', [string]$QualityCtx, '-ngl', [string]$Ngl, '-ncmoe', [string]$NcMoe,
                  '-t', [string]$Threads, '--jinja', '--port', [string]$QualityPort, '--host', '127.0.0.1',
                  '--moe-cache-mib', [string]$MoeCacheMib)
        $log = Join-Path $outDir "server-$tag-$stamp.log"
        $p = Start-Process -FilePath $server -ArgumentList $srvArgs -RedirectStandardOutput $log -RedirectStandardError "$log.err" -PassThru -WindowStyle Hidden
        try {
            if (-not (Wait-Health $QualityPort 90)) { throw "server not ready (see $log)" }
            & $harness -Tag $tag -ServerUrl "http://127.0.0.1:$QualityPort"
            $scoreDir = Join-Path $PSScriptRoot 'quality-harness\results'
            $scoreFile = Get-ChildItem -LiteralPath $scoreDir -Filter "score-$tag-*.jsonl" -File -ErrorAction SilentlyContinue |
                Sort-Object LastWriteTime -Descending | Select-Object -First 1
            if ($scoreFile) {
                $srows = @(Get-Content -LiteralPath $scoreFile.FullName | ForEach-Object { $_ | ConvertFrom-Json })
                $checksTotal = 0
                $checksPass = 0
                foreach ($sr in $srows) {
                    foreach ($c in @($sr.checks)) {
                        $checksTotal++
                        if ($c[1]) { $checksPass++ }
                    }
                }
                $row.quality = [ordered]@{
                    tasks_ok = @($srows | Where-Object { $_.task_ok }).Count
                    tasks_total = $srows.Count
                    checks_pass = $checksPass
                    checks_total = $checksTotal
                    score_file = $scoreFile.FullName
                }
            } else {
                $row.quality = @{ error = 'score file not found' }
            }
        } finally {
            if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
        }
    }

    if (-not $SkipBench) {
        & (Join-Path $PSScriptRoot 'run-flint-bench.ps1') -Quant $q -Ngl $Ngl -NcMoe $NcMoe -MoeCacheMib $MoeCacheMib
        $metrics = Join-Path $eco "main_ecosystem_trading\backtesting_pipeline\llm_bench\runs\$tag\metrics.json"
        if (Test-Path -LiteralPath $metrics) { $row.bench = (Get-Content -LiteralPath $metrics -Raw | ConvertFrom-Json) }
    }

    $rows += $row
}

$rows | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $summaryPath
Write-Host "`nsummary: $summaryPath"
