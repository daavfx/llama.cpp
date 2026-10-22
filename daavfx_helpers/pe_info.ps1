param([string]$Path)
$bytes = [System.IO.File]::ReadAllBytes($Path)
# PE header offset is at 0x3C
$peOffset = [BitConverter]::ToInt32($bytes, 0x3C)
# COFF header is at peOffset + 4
# Timestamp is at peOffset + 4 + 4 = peOffset + 8
$tsOffset = $peOffset + 8
$ts = [BitConverter]::ToUInt32($bytes, $tsOffset)
$dt = (Get-Date "1970-01-01 00:00:00").AddSeconds($ts)
Write-Host "$Path"
Write-Host "  PE offset: 0x$($peOffset.ToString('X'))"
Write-Host "  Timestamp: $ts ($($dt.ToString('yyyy-MM-dd HH:mm:ss'))) UTC"
Write-Host "  Size: $((Get-Item $Path).Length) bytes"
