# run-flint-bench.ps1 - run the MT5 MCP agent benchmark on one Flint quant.
# Wraps llm_bench/tools/bench_driver.ps1 with Flint sampling defaults and the
# native OpenAI tool catalog. The driver starts and stops its own server.
param(
    [string] $Quant = '',
    [string] $ModelPath = '',
    [string] $ModelName = '',
    [int] $NcMoe = 24,
    [int] $MoeCacheMib = 1024,
    [int] $Ctx = 8192,
    [int] $MaxTokens = 4096,
    [int] $MaxTurns = 30,
    [double] $Temperature = 1.0,
    [double] $TopP = 0.95,
    [int] $TopK = 20,
    [int] $Ngl = 99,
    [int] $Port = 8077,
    [string] $LlamaServer = ''
)

$ErrorActionPreference = 'Stop'

$eco = Split-Path (Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent) -Parent
$benchRoot = Join-Path $eco 'main_ecosystem_trading\backtesting_pipeline\llm_bench'
$driver = Join-Path $benchRoot 'tools\bench_driver.ps1'
if (-not (Test-Path -LiteralPath $driver)) { throw "driver not found: $driver" }

if (-not $ModelPath) {
    if (-not $Quant) { throw 'pass -Quant or -ModelPath' }
    $models = Join-Path $eco 'local_llm\GGUF\llm-collection\21-flint'
    $hits = @(Get-ChildItem -LiteralPath $models -Filter "*$Quant*.gguf" -File -ErrorAction SilentlyContinue)
    if ($hits.Count -eq 0) { throw "no GGUF matching '$Quant' under $models (run fetch-flint-gguf.ps1 first)" }
    $firstShards = @($hits | Where-Object { $_.Name -match '-00001-of-\d{5}\.gguf$' })
    if ($firstShards.Count -eq 1) {
        $ModelPath = $firstShards[0].FullName
    } elseif ($hits.Count -eq 1) {
        $ModelPath = $hits[0].FullName
    } else {
        $names = ($hits | ForEach-Object { $_.Name }) -join ', '
        throw "ambiguous '$Quant': $names (pass -ModelPath or use -File in fetch-flint-gguf.ps1)"
    }
}
if (-not (Test-Path -LiteralPath $ModelPath)) { throw "model not found: $ModelPath" }
if (-not $ModelName) {
    $tag = $Quant
    if (-not $tag) { $tag = [IO.Path]::GetFileNameWithoutExtension($ModelPath) }
    $ModelName = 'flint-' + $tag
}

if (-not $LlamaServer) {
    $LlamaServer = Join-Path $eco 'shared\llama.cpp-flint-wt\build_flint\bin\Release\llama-server.exe'
}
if (-not (Test-Path -LiteralPath $LlamaServer)) {
    throw "Flint-capable llama-server not found: $LlamaServer (run build-flint-llama.ps1 first)"
}

Write-Host "model : $ModelPath"
Write-Host "name  : $ModelName"
Write-Host "server: $LlamaServer"

& $driver -ModelPath $ModelPath -ModelName $ModelName -Ngl $Ngl -Ctx $Ctx -LlamaPort $Port `
    -MaxTurns $MaxTurns -Temperature $Temperature -TopP $TopP -TopK $TopK -MaxTokens $MaxTokens `
    -NcMoe $NcMoe -MoeCacheMib $MoeCacheMib -LlamaServer $LlamaServer -UseOpenAITools
