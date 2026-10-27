# capture-manifest-check.ps1 - EXP-1 validator (Batch 1)
# Pure logic: validates a router capture CSV + its .manifest sidecar against
# shape/coverage rules, so a truncated or wrong-shape or selection-less
# capture is mechanically inadmissible as verdict evidence.
#
# Usage:
#   .\capture-manifest-check.ps1 -Csv <csv> [-Manifest <manifest>]
#   .\capture-manifest-check.ps1 -SelfTest
#
# ASCII only. No network, no GPU, no external deps.

param(
    [string] $Csv,
    [string] $Manifest,
    [switch] $SelfTest
)

function Test-Capture {
    param([string]$CsvPath, [string]$ManifestPath)
    if (-not (Test-Path -LiteralPath $CsvPath)) { return @{ verdict = 'NO-CSV'; detail = $CsvPath } }
    $rows = @(Get-Content -LiteralPath $CsvPath | Select-Object -Skip 1 | Where-Object { $_ -match ',' })
    if ($rows.Count -eq 0) { return @{ verdict = 'REJECTED-EMPTY'; detail = 'no data rows' } }
    $sel = 0.0; $layers = @{}; $perLayerExperts = @{}
    foreach ($r in $rows) {
        $c = $r.Split(',')
        if ($c.Count -lt 3) { continue }
        $il = $c[0]; $e = $c[1]; $s = [double]$c[2]
        $sel += $s
        $layers[$il] = $true
        if (-not $perLayerExperts.ContainsKey($il)) { $perLayerExperts[$il] = @{} }
        $perLayerExperts[$il][$e] = $true
    }
    $perLayerCount = 0
    foreach ($v in $perLayerExperts.Values) { if ($v.Count -gt $perLayerCount) { $perLayerCount = $v.Count } }
    $shape = ($rows.Count -eq ($layers.Count * $perLayerCount))
    $m = $null
    if ($ManifestPath -and (Test-Path -LiteralPath $ManifestPath)) { $m = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json }
    if ($sel -eq 0) { return @{ verdict = 'REJECTED-NO-SELECTIONS'; detail = "0 selections across $($rows.Count) rows (capture channel dead or not run)" } }
    if ($m) {
        if ($m.truncated) { return @{ verdict = 'REJECTED-TRUNCATED'; detail = "manifest truncated=true (observed width $($m.observed_expert_width) vs capacity $($m.capacity_experts))" } }
        $mRows = $layers.Count * $m.capacity_experts
        if ($rows.Count -ne $mRows) { return @{ verdict = 'REJECTED-SHAPE-MISMATCH'; detail = "csv rows $($rows.Count) vs manifest capacity math $mRows" } }
        $iat = $m.slots_with_selections
        if ($iat -eq 0) { return @{ verdict = 'REJECTED-NO-SELECTIONS'; detail = 'manifest slots_with_selections=0' } }
        return @{ verdict = 'ADMISSIBLE'; detail = "selections=$([math]::Round($sel)) shape_ok=$shape layers=$($layers.Count) manifest=ok" }
    }
    return @{ verdict = 'ADMISSIBLE-NO-MANIFEST'; detail = "selections=$([math]::Round($sel)) shape_ok=$shape (no manifest - re-capture to get one)" }
}

if ($SelfTest) {
    $tmp = Join-Path $env:TEMP 'manifest-check-selftest'
    New-Item -ItemType Directory -Path $tmp -Force | Out-Null
    $goodCsv = "$tmp\good.csv"; $goodMf = "$tmp\good.csv.manifest"
    $hdr = 'layer,expert,selected,mass_selected,mass_all,tokens'
    $body = @()
    foreach ($il in 2..3) {
        for ($e = 0; $e -lt 256; $e++) {
            $sel = if ($e -lt 3) { 5 - $e } else { 0 }
            $ms = if ($sel -gt 0) { 1.5 } else { 0 }
            $body += "$il,$e,$sel,$ms,9.1,100"
        }
    }
    Set-Content -LiteralPath $goodCsv -Value ($hdr + "`n" + ($body -join "`n"))
    Set-Content -LiteralPath $goodMf -Value @'
{ "csv": "good.csv", "authored_by": "test", "capacity_layers": 48,
  "capacity_experts": 256, "observed_expert_width": 256,
  "observed_layer_span": "2..3", "layers_with_traffic": 2,
  "slots_with_selections": 6, "truncated": false,
  "note": "test" }
'@
    $truncMf = "$tmp\trunc.csv.manifest"
    Set-Content -LiteralPath $truncMf -Value @'
{ "csv": "trunc.csv", "authored_by": "test", "capacity_layers": 24,
  "capacity_experts": 32, "observed_expert_width": 256,
  "observed_layer_span": "2..2", "layers_with_traffic": 1,
  "slots_with_selections": 2, "truncated": true,
  "note": "test" }
'@
    $noseCsv = "$tmp\noselections.csv"
    Set-Content -LiteralPath $noseCsv -Value "layer,expert,selected,mass_selected,mass_all,tokens`n2,0,0,0.0,9.1,100`n2,1,0,0.0,8.2,100"
    "good   : $((Test-Capture $goodCsv $goodMf).verdict) - $((Test-Capture $goodCsv $goodMf).detail)"
    $r1 = Test-Capture $goodCsv $truncMf
    "trunc  : $($r1.verdict) - $($r1.detail)"
    $r2 = Test-Capture $noseCsv
    "nosel  : $($r2.verdict) - $($r2.detail)"
    $ok = ((Test-Capture $goodCsv $goodMf).verdict -eq 'ADMISSIBLE' -and $r1.verdict -eq 'REJECTED-TRUNCATED' -and $r2.verdict -eq 'REJECTED-NO-SELECTIONS')
    if ($ok) { 'SELF-TEST: PASS (all three verdicts correct)' } else { 'SELF-TEST: FAIL' }
} else {
    $r = Test-Capture $Csv $Manifest
    "$($r.verdict) - $($r.detail)"
}
