# How far upstream hex (anomalyco/hex) has moved since our last recorded look.
# We do not fork hex; this is an upstream-watch, same cadence as check-orca-drift.
# Usage:  pwsh scripts/daavfx/check-hex-drift.ps1            (local refs, instant)
#         pwsh scripts/daavfx/check-hex-drift.ps1 -Fetch     (refresh upstream first)
#         pwsh scripts/daavfx/check-hex-drift.ps1 -Log       (append a baseline row)

param([switch]$Fetch, [switch]$Log)

$repo = Join-Path $PSScriptRoot "..\..\..\hex-original"
if (-not (Test-Path $repo)) { Write-Error "missing $repo - clone: git clone --depth 1 https://github.com/anomalyco/hex"; exit 1 }

if ($Fetch) {
    Write-Host "# fetching upstream hex (objects only)"
    git -C $repo fetch --quiet --depth 50 origin HEAD 2>&1 | Out-Null
    git -C $repo fetch --quiet --depth 50 --tags origin 2>&1 | Out-Null
}

$head = git -C $repo log --oneline -1 origin/HEAD 2>$null
if (-not $head) { $head = git -C $repo log --oneline -1 }
$sha = ($head -split '\s+')[0]
$date = git -C $repo show -s --format=%cI $sha
$subject = git -C $repo show -s --format=%s $sha
$newestTag = (git -C $repo describe --tags --abbrev=0 $sha 2>$null)
if (-not $newestTag) { $newestTag = "(no tag reachable at this depth)" }

$ledgerFile = Join-Path $PSScriptRoot "..\..\docs\daavfx\app-lane\HEX-DRIFT.md"
$lastSha = ""
if (Test-Path $ledgerFile) {
    $m = Select-String -Path $ledgerFile -Pattern 'Last recorded SHA: `([0-9a-f]+)`' | Select-Object -Last 1
    if ($m) { $lastSha = $m.Matches[0].Groups[1].Value }
}

Write-Host "# hex upstream-watch @ $(Get-Date -Format o)"
Write-Host "upstream HEAD: $sha ($date) $subject"
Write-Host "newest reachable tag: $newestTag"
if ($lastSha -and $lastSha -ne $sha) {
    $count = git -C $repo rev-list --count "$lastSha..$sha" 2>$null
    if ($count) {
        Write-Host "commits since our last recorded SHA ($lastSha): $count"
        Write-Host "--- features/fixes since then ---"
        git -C $repo log --oneline "$lastSha..$sha" 2>$null |
            Where-Object { $_ -match '(?i)^[0-9a-f]+ (feat|fix|perf)(\(|:)' } |
            Select-Object -First 20
    }
} elseif ($lastSha -eq $sha) {
    Write-Host "no upstream movement since our last recorded SHA"
} else {
    Write-Host "no previous SHA recorded yet - record this run's baseline in HEX-DRIFT.md"
}

if ($Log) {
    $logPath = Join-Path (Join-Path $PSScriptRoot "..\..\docs\daavfx\app-lane") "HEX-DRIFT-LOG.jsonl"
    $row = @{ ts = (Get-Date -Format o); head = $sha; date = $date; tag = $newestTag; subject = $subject }
    Add-Content -Path $logPath -Value ($row | ConvertTo-Json -Compress)
    Write-Host "# appended $logPath"
}
