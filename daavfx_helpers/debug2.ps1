$Path = "F:\DAAVILE_ECOSYSTEM\trading_ecosystem_11\trading_ecosystem_9.0\shared\llama.cpp-atomic\build_vulkan_ninja\bin\llama-server.exe"
$bytes = [System.IO.File]::ReadAllBytes($Path)
$peOffset = [BitConverter]::ToInt32($bytes, 0x3C)
$coffSizeOfOptHdr = [BitConverter]::ToUInt16($bytes, $peOffset + 16)
$sectStart = $peOffset + 20 + $coffSizeOfOptHdr
$numSections = [BitConverter]::ToUInt16($bytes, $peOffset + 2)
Write-Host "peOffset=$peOffset, sectStart=$sectStart, numSections=$numSections"
$bytes[$sectStart..($sectStart+50)] | ForEach-Object { Write-Host "$_" }
