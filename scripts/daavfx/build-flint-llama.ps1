# build-flint-llama.ps1 - build the Flint-capable abeliant fork.
# Configure + build with MSVC. Does not run inference.
# Default: Vulkan enabled (GTX 1650), CPU fallback always available.
param(
    [string] $Worktree = 'F:\DAAVILE_ECOSYSTEM\trading_ecosystem_11\trading_ecosystem_9.0\shared\llama.cpp-flint-wt',
    [string] $ShortLink = 'F:\llvb_flint',
    [string] $BuildDir = 'build_flint',
    [switch] $CpuOnly,
    [switch] $Clean,
    [string] $Config = 'Release'
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $Worktree)) { throw "worktree not found: $Worktree" }

# MSVC environment
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
if (-not (Test-Path -LiteralPath $vswhere)) { throw "vswhere not found: $vswhere" }
$vsPath = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $vsPath) { throw 'Visual Studio with C++ tools not found' }
$vcvars = Join-Path $vsPath 'VC\Auxiliary\Build\vcvars64.bat'
if (-not (Test-Path -LiteralPath $vcvars)) { throw "vcvars64 not found: $vcvars" }

# Short junction keeps MSVC scratch paths under MAX_PATH.
if (-not (Test-Path -LiteralPath $ShortLink)) {
    New-Item -ItemType Junction -Path $ShortLink -Target $Worktree | Out-Null
    Write-Host "junction: $ShortLink -> $Worktree"
} else {
    $link = Get-Item -LiteralPath $ShortLink -Force
    $target = @($link.Target) | Select-Object -First 1
    $expected = $Worktree.TrimEnd('\')
    if ($link.LinkType -ne 'Junction' -or -not $target -or $target.TrimEnd('\') -ne $expected) {
        throw "$ShortLink exists but is not a junction to $Worktree"
    }
}

$build = Join-Path $ShortLink $BuildDir
if ($Clean -and (Test-Path -LiteralPath $build)) {
    Write-Host "removing $build"
    Remove-Item -LiteralPath $build -Recurse -Force
}

$cfgArgs = @('-S', $ShortLink, '-B', $build, '-G', 'Visual Studio 17 2022', '-A', 'x64',
             '-DGGML_NATIVE=ON', '-DBUILD_SHARED_LIBS=OFF')
if (-not $CpuOnly) { $cfgArgs += '-DGGML_VULKAN=ON' }

$cfgLine = 'cmake ' + ($cfgArgs -join ' ')
$buildLine = 'cmake --build "' + $build + '" --config ' + $Config + ' --target llama-server llama-cli -- /m'

Write-Host "configure: $cfgLine"
& cmd.exe /c ('call "' + $vcvars + '" >nul && ' + $cfgLine)
if ($LASTEXITCODE -ne 0) { throw "cmake configure failed ($LASTEXITCODE)" }

Write-Host "build: $buildLine"
& cmd.exe /c ('call "' + $vcvars + '" >nul && ' + $buildLine)
if ($LASTEXITCODE -ne 0) { throw "cmake build failed ($LASTEXITCODE)" }

$server = Join-Path $build "bin\$Config\llama-server.exe"
if (-not (Test-Path -LiteralPath $server)) { throw "build finished but $server is missing" }
Write-Host "OK: $server"
& $server --version
