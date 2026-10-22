# phase1-bench-matrix.ps1 - Phase 1 base-truth rows for LFM2.5-8B-A1B Q4_K_M.
# Protocol per docs/daavfx/BENCH.md culture: llama-bench, tee raw output,
# VRAM sampled during runs, manifest CSV row per run.
# SAFETY: refuses to run without -Go; aborts if port 8082 is listening
# (the human coder's sweep / gemma server owns the box until the go signal).

param(
    [switch]$Go,
    [string]$Bench = $PSScriptRoot + "\..\..\build_vulkan_bench\bin\Release\llama-bench.exe",
    [string]$Model = "F:\DAAVILE_ECOSYSTEM\trading_ecosystem_11\trading_ecosystem_9.0\local_llm\GGUF\llm-collection\09-LFM2.5-8B-A1B\LFM2.5-8B-A1B-Q4_K_M.gguf",
    [string]$OutDir = $PSScriptRoot + "\results\phase1",
    [ValidateSet('BelowNormal','Normal','Idle')]
    [string]$Priority = 'BelowNormal'
)

$ErrorActionPreference = 'Continue'

if (-not $Go) { Write-Host "refusing to run: pass -Go once the coder's sweep is done and gemma is stopped."; exit 2 }
if (-not (Test-Path $Bench)) { Write-Host "llama-bench not found: $Bench (run Phase 0 build first)"; exit 2 }
if (-not (Test-Path $Model)) { Write-Host "model not found: $Model"; exit 2 }
$busy = Get-NetTCPConnection -LocalPort 8082 -State Listen -ErrorAction SilentlyContinue
if ($busy) { Write-Host "refusing to run: port 8082 still listening (llama-server/gemma up). Stop it first or wait for the go signal."; exit 2 }

New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$manifest = Join-Path $OutDir "manifest-$stamp.csv"
"tag,started,duration_s,exitcode,command" | Set-Content $manifest

# rows: tag, extra args. -ncmoe 24 = experts of all layers on CPU.
# llama-bench flags verified against tools/llama-bench/llama-bench.cpp (0.7.0):
# -m -p -n -t -ngl -ncmoe -fa -r -o
$rows = @(
    @{ tag = 'cpu-t6';    args = '-t 6 -ngl 0 -p 512 -n 128 -r 2 -o jsonl' },
    @{ tag = 'cpu-t12';   args = '-t 12 -ngl 0 -p 512 -n 128 -r 2 -o jsonl' },
    @{ tag = 'split';     args = '-t 6 -ngl 99 -ncmoe 24 -p 512 -n 128 -r 2 -o jsonl' },
    @{ tag = 'split-fa0'; args = '-t 6 -ngl 99 -ncmoe 24 -fa 0 -p 512 -n 128 -r 2 -o jsonl' },
    @{ tag = 'split-fa1'; args = '-t 6 -ngl 99 -ncmoe 24 -fa 1 -p 512 -n 128 -r 2 -o jsonl' },
    @{ tag = 'full-oom';  args = '-t 6 -ngl 99 -p 512 -n 128 -r 1 -o jsonl' }
)

function Start-VramSampler {
    param([string]$Tag, [string]$CsvPath)
    $job = Start-Job -ScriptBlock {
        param($t, $csv)
        $sw = [System.IO.StreamWriter]::new($csv, $true)
        $sw.WriteLine('timestamp,tag,used_mib')
        while ($true) {
            $v = & nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>$null
            $sw.WriteLine(("{0},{1},{2}" -f (Get-Date -Format o), $t, ($v -join ';')))
            $sw.Flush()
            Start-Sleep -Seconds 2
        }
        $sw.Close()
    } -ArgumentList $Tag, $CsvPath
    return $job
}

foreach ($r in $rows) {
    $tag = $r.tag
    $cmd = "`"$Bench`" -m `"$Model`" $($r.args)"
    Write-Host "`n=== row $tag ===" -ForegroundColor Cyan
    Write-Host $cmd
    $rowOut = Join-Path $OutDir "$tag-$stamp.jsonl"
    $vramCsv = Join-Path $OutDir "vram-$tag-$stamp.csv"

    $sampler = Start-VramSampler -Tag $tag -CsvPath $vramCsv
    $t0 = Get-Date
    $p = Start-Process -FilePath $Bench -ArgumentList "-m `"$Model`" $($r.args)" `
         -NoNewWindow -PassThru -RedirectStandardOutput $rowOut `
         -RedirectStandardError "$rowOut.err"
    try { $p.PriorityClass = $Priority } catch { Write-Host "  (could not set priority: $($_.Exception.Message))" }
    $p.WaitForExit()
    $dt = [math]::Round(((Get-Date) - $t0).TotalSeconds, 1)
    Stop-Job $sampler -ErrorAction SilentlyContinue
    Remove-Job $sampler -Force -ErrorAction SilentlyContinue

    $ec = $p.ExitCode
    Write-Host ("  exit={0}  {1}s  out={2}" -f $ec, $dt, $rowOut)
    if ($tag -eq 'full-oom' -and $ec -ne 0) { Write-Host "  (expected: this row documents the 4GB wall)" }
    "{0},{1},{2},{3},{4}" -f $tag, (Get-Date $t0 -Format o), $dt, $ec, $cmd | Add-Content $manifest
}

Write-Host "`n=== phase1 done ==="
Write-Host "manifest: $manifest"
Write-Host "next: copy rows into llab-data + docs/daavfx/BENCH.md; then moe-cache smoke (campaign Phase 1 item 6)."
