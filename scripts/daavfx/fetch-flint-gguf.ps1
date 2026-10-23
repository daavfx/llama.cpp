# fetch-flint-gguf.ps1 - download one Flint quant from Hugging Face.
# Resolves the real file name from the repo file list, then downloads with curl.
# Split quants download all shards. Nothing is downloaded until this script is run.
param(
    [Parameter(Mandatory = $true)][string] $Quant,
    [string] $Repo = 'unsloth/flint-GGUF',
    [string] $Dest = '',
    [string] $File = '',
    [switch] $List
)

$ErrorActionPreference = 'Stop'

if (-not $Dest) {
    $eco = Split-Path (Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent) -Parent
    $Dest = Join-Path $eco 'local_llm\GGUF\llm-collection\21-flint'
}

Write-Host "repo: $Repo"
$api = "https://huggingface.co/api/models/$Repo"
$info = Invoke-RestMethod -Uri $api -TimeoutSec 60
$files = @($info.siblings | ForEach-Object { $_.rfilename } | Where-Object { $_ -like '*.gguf' })
if ($files.Count -eq 0) { throw "no .gguf files listed for $Repo" }

if ($List) {
    $files | ForEach-Object { $_ }
    return
}

if ($File) {
    if ($files -notcontains $File) { throw "file not in repo: $File" }
    $downloads = @($File)
} else {
    $hits = @($files | Where-Object { $_ -match [regex]::Escape($Quant) })
    if ($hits.Count -eq 0) {
        Write-Host "no file matches '$Quant'. available:"
        $files | ForEach-Object { "  $_" }
        exit 1
    }
    if ($hits.Count -eq 1) {
        $downloads = $hits
    } else {
        $shardPattern = '^(?<base>.+)-(?<idx>\d{5})-of-(?<total>\d{5})\.gguf$'
        $groups = @{}
        foreach ($h in $hits) {
            $m = [regex]::Match($h, $shardPattern)
            if (-not $m.Success) {
                $groups['single:' + $h] = @($h)
                continue
            }
            $base = $m.Groups['base'].Value
            if (-not $groups.ContainsKey($base)) { $groups[$base] = @() }
            $groups[$base] += $h
        }
        if ($groups.Count -ne 1) {
            Write-Host "ambiguous '$Quant'. Pass -File with one name:"
            $hits | ForEach-Object { "  $_" }
            exit 1
        }
        $key = @($groups.Keys)[0]
        $downloads = @($groups[$key] | Sort-Object { [int]([regex]::Match($_, $shardPattern).Groups['idx'].Value) })
    }
}

New-Item -ItemType Directory -Path $Dest -Force | Out-Null
$curl = Get-Command curl.exe -ErrorAction SilentlyContinue
if (-not $curl) { throw 'curl.exe not found' }

$total = 0
foreach ($item in $downloads) {
    $url = "https://huggingface.co/$Repo/resolve/main/$item"
    $out = Join-Path $Dest (Split-Path $item -Leaf)
    Write-Host "file: $item"
    Write-Host "url : $url"
    Write-Host "out : $out"
    & curl.exe -L --fail --silent --show-error --retry 3 --retry-delay 5 -C - -o $out $url
    if ($LASTEXITCODE -ne 0) { throw "curl failed for $item ($LASTEXITCODE)" }
    $size = (Get-Item -LiteralPath $out).Length
    $total += $size
    Write-Host ("OK: {0:N2} GB" -f ($size / 1GB))
}

Write-Host ("done: {0} file(s), {1:N2} GB total" -f $downloads.Count, ($total / 1GB))
