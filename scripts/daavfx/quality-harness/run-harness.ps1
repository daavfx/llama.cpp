# run-harness.ps1 - FOUNDRY quality-budget harness runner.
# Assumes a llama-server is ALREADY serving the model under test
# (baseline or mutant). Posts each task, saves raw responses, then scores.

param(
    [Parameter(Mandatory=$true)][string]$Tag,
    [string]$ServerUrl = "http://127.0.0.1:8083",
    [string]$Taskset = $PSScriptRoot + "\taskset.json",
    [string]$OutDir = $PSScriptRoot + "\results"
)

$ErrorActionPreference = 'Stop'
$tasks = (Get-Content $Taskset -Raw | ConvertFrom-Json).tasks
$sampling = (Get-Content $Taskset -Raw | ConvertFrom-Json).sampling

New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$responses = Join-Path $OutDir "responses-$Tag-$stamp.jsonl"

foreach ($t in $tasks) {
    $body = @{
        model = $Tag
        messages = @(@{ role = 'user'; content = $t.prompt })
        temperature = $sampling.temperature
        top_k = $sampling.top_k
        max_tokens = $t.max_tokens
        stream = $false
    } | ConvertTo-Json -Depth 5

    $ok = $false; $text = ''; $err = ''
    try {
        $r = Invoke-RestMethod -Uri "$ServerUrl/v1/chat/completions" -Method Post `
             -ContentType 'application/json' -Body $body -TimeoutSec 300
        $text = [string]($r.choices[0].message.content)
        $ok = $true
    } catch { $err = $_.Exception.Message }

    $row = @{ tag = $Tag; id = $t.id; ok = $ok; error = $err; response = $text }
    $row | ConvertTo-Json -Depth 4 -Compress | Add-Content -Encoding UTF8 $responses
    Write-Host ("{0,-24} {1}" -f $t.id, ($(if ($ok) { 'served' } else { "ERROR: $err" })))
}

Write-Host "`nresponses: $responses"
python "$PSScriptRoot\score.py" --responses $responses
