$bytes = [System.IO.File]::ReadAllBytes("F:\DAAVILE_ECOSYSTEM\trading_ecosystem_11\trading_ecosystem_9.0\shared\llama.cpp-atomic\build_vulkan_ninja\bin\llama-server.exe")
Write-Host "File size: $($bytes.Length)"
$peOffset = [BitConverter]::ToInt32($bytes, 0x3C)
Write-Host "PE offset: 0x$($peOffset.ToString('X'))"
$numSections = [BitConverter]::ToUInt16($bytes, $peOffset + 2)
Write-Host "Num sections: $numSections"
$coffSizeOfOptHdr = [BitConverter]::ToUInt16($bytes, $peOffset + 16)
Write-Host "COFF size of optional header: $coffSizeOfOptHdr"
$sectStart = $peOffset + 20 + $coffSizeOfOptHdr
Write-Host "Section table start: 0x$($sectStart.ToString('X'))"

# Try a simpler parser
$ms = New-Object System.IO.MemoryStream
$ms.Write($bytes, 0, $bytes.Length)
$ms.Position = 0
$br = New-Object System.IO.BinaryReader($ms)
$ms.Position = 0x3C
$peSigOffset = $br.ReadInt32()
Write-Host "PE sig offset: $peSigOffset"
$ms.Position = $peSigOffset
$peSig = $br.ReadUInt32()
Write-Host "PE sig: 0x$($peSig.ToString('X8')) (should be 0x00004550 'PE\0\0')"
$coffMachine = $br.ReadUInt16()
Write-Host "Machine: 0x$($coffMachine.ToString('X4'))"
$numSec = $br.ReadUInt16()
Write-Host "Num sections: $numSec"
