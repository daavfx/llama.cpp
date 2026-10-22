@echo off
setlocal
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\Common7\Tools\VsDevCmd.bat" -arch=x64 -host_arch=x64
where ml64.exe
where cl.exe
where link.exe
echo --- PATH ASM dirs ---
echo %PATH% | tr ";" "\n" | findstr /i "asm masm ml64"
