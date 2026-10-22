$liveCache = "F:\DAAVILE_ECOSYSTEM\trading_ecosystem_11\trading_ecosystem_9.0\shared\llama.cpp-atomic\build_vulkan_ninja\CMakeCache.txt"
$wtCache = "F:\DAAVILE_ECOSYSTEM\trading_ecosystem_11\trading_ecosystem_9.0\u_studio\llama.cpp-atomic-daavfx\build\CMakeCache.txt"

# Read both as hashtables: name -> value
function Parse-Cache([string]$Path) {
    $h = @{}
    Get-Content $Path | ForEach-Object {
        if ($_ -match "^([A-Z_][A-Z0-9_]*):([A-Z]+)=(.+)$") {
            $h[$Matches[1]] = $Matches[3]
        }
    }
    return $h
}

$live = Parse-Cache $liveCache
$wt = Parse-Cache $wtCache

$allKeys = @($live.Keys) + @($wt.Keys) | Sort-Object -Unique
$diffs = @()
foreach ($k in $allKeys) {
    $lv = if ($live.ContainsKey($k)) { $live[$k] } else { "<missing>" }
    $wv = if ($wt.ContainsKey($k)) { $wt[$k] } else { "<missing>" }
    if ($lv -ne $wv) {
        $diffs += [PSCustomObject]@{ Key = $k; Live = $lv; Wt = $wv }
    }
}
Write-Host "Total differing keys: $($diffs.Count)"
$diffs | Where-Object { $_.Key -match "^(GGML_|LLAMA_|CMAKE_BUILD_TYPE|CMAKE_GENERATOR|CMAKE_C_COMPILER|CMAKE_CXX)" } | Format-Table -AutoSize
