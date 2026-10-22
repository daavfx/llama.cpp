param(
    [string]$Path
)

$bytes = [System.IO.File]::ReadAllBytes($Path)
$peOffset = [BitConverter]::ToInt32($bytes, 0x3C)

# COFF header starts at peOffset + 4
# SizeOfOptionalHeader at peOffset + 16
$coffSizeOfOptHdr = [BitConverter]::ToUInt16($bytes, $peOffset + 16)
# Optional header starts at peOffset + 20
$optStart = $peOffset + 20
# Magic at optStart
$magic = [BitConverter]::ToUInt16($bytes, $optStart)
# Section headers start at optStart + coffSizeOfOptHdr
$sectStart = $optStart + $coffSizeOfOptHdr
# NumberOfSections at peOffset + 2
$numSections = [BitConverter]::ToUInt16($bytes, $peOffset + 2)

Write-Host "$Path"
Write-Host "  PE offset: 0x$($peOffset.ToString('X'))"
Write-Host "  Magic: 0x$($magic.ToString('X4')) (PE32=0x10B, PE32+=0x20B)"
Write-Host "  Sections: $numSections"
Write-Host ""

# Each section header is 40 bytes
$sectionNames = @()
for ($i = 0; $i -lt $numSections; $i++) {
    $sectHeaderOffset = $sectStart + ($i * 40)
    # Name is 8 bytes
    $name = ""
    for ($j = 0; $j -lt 8; $j++) {
        $c = $bytes[$sectHeaderOffset + $j]
        if ($c -eq 0) { break }
        $name += [char]$c
    }
    # VirtualSize at +8 (4 bytes)
    $vSize = [BitConverter]::ToUInt32($bytes, $sectHeaderOffset + 8)
    # VirtualAddress at +12
    $vAddr = [BitConverter]::ToUInt32($bytes, $sectHeaderOffset + 12)
    # SizeOfRawData at +16
    $rawSize = [BitConverter]::ToUInt32($bytes, $sectHeaderOffset + 16)
    # PointerToRawData at +20
    $rawPtr = [BitConverter]::ToUInt32($bytes, $sectHeaderOffset + 20)
    Write-Host ("  [{0,2}] {1,-10} VAddr=0x{2:X8} VSize=0x{3:X8} RawPtr=0x{4:X8} RawSize=0x{5:X8}" -f $i, $name, $vAddr, $vSize, $rawPtr, $rawSize)
    $sectionNames += [PSCustomObject]@{ Name = $name; RawPtr = $rawPtr; RawSize = $rawSize }
}

return $sectionNames
