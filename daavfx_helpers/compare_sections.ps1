param(
    [string]$LivePath,
    [string]$WorktreePath
)

function Get-Sections([string]$Path) {
    $bytes = [System.IO.File]::ReadAllBytes($Path)
    $peOffset = [BitConverter]::ToInt32($bytes, 0x3C)
    # PE signature at peOffset (4 bytes "PE\0\0")
    # COFF header at peOffset+4:
    #   Machine (2) at peOffset+4
    #   NumberOfSections (2) at peOffset+6
    #   TimeDateStamp (4) at peOffset+8
    #   ...
    #   SizeOfOptionalHeader (2) at peOffset+20
    # Optional header at peOffset+24
    # Section headers at peOffset+24+SizeOfOptionalHeader
    $numSections = [BitConverter]::ToUInt16($bytes, $peOffset + 6)
    $coffSizeOfOptHdr = [BitConverter]::ToUInt16($bytes, $peOffset + 20)
    $sectStart = $peOffset + 24 + $coffSizeOfOptHdr
    $sections = @()
    for ($i = 0; $i -lt $numSections; $i++) {
        $sh = $sectStart + ($i * 40)
        $name = ""
        for ($j = 0; $j -lt 8; $j++) {
            $c = $bytes[$sh + $j]
            if ($c -eq 0) { break }
            $name += [char]$c
        }
        $rawSize = [BitConverter]::ToUInt32($bytes, $sh + 16)
        $rawPtr = [BitConverter]::ToUInt32($bytes, $sh + 20)
        if ($rawSize -gt 0) {
            $ms = New-Object System.IO.MemoryStream
            $ms.Write($bytes, $rawPtr, $rawSize)
            $ms.Position = 0
            $sha = (Get-FileHash -InputStream $ms -Algorithm SHA256).Hash
            $ms.Dispose()
        } else {
            $sha = "<empty>"
        }
        $sections += [PSCustomObject]@{ Name = $name; Size = $rawSize; SHA = $sha }
    }
    return $sections
}

$live = Get-Sections $LivePath
$wt = Get-Sections $WorktreePath

Write-Host "Section-by-section SHA256 comparison:"
Write-Host ("{0,-10} {1,10} {2,10} {3,8} {4,8}" -f "Name", "LiveSize", "WTSize", "Size=", "SHA=")
Write-Host ("-" * 60)
foreach ($l in $live) {
    $w = $wt | Where-Object { $_.Name -eq $l.Name } | Select-Object -First 1
    if ($w) {
        $sameSize = if ($l.Size -eq $w.Size) { "OK" } else { "DIFF" }
        $sameSha = if ($l.SHA -eq $w.SHA) { "MATCH" } else { "DIFFER" }
        Write-Host ("{0,-10} {1,10} {2,10} {3,8} {4,8}" -f $l.Name, $l.Size, $w.Size, $sameSize, $sameSha)
    }
}

Write-Host ""
Write-Host "Full SHA256 of each section:"
foreach ($l in $live) {
    $w = $wt | Where-Object { $_.Name -eq $l.Name } | Select-Object -First 1
    if ($w) {
        Write-Host "  $($l.Name):"
        Write-Host "    Live:  $($l.SHA)"
        Write-Host "    WT:    $($w.SHA)"
    }
}
