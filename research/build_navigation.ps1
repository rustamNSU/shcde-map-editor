$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$compiler = Get-ChildItem 'C:\Program Files\Microsoft Visual Studio' -Filter cl.exe -Recurse |
    Where-Object FullName -Like '*Hostx64\x64\cl.exe' | Select-Object -First 1
if (-not $compiler) { throw 'MSVC x64 compiler not found' }
$vcvars = Join-Path ($compiler.FullName.Split('\VC\Tools\')[0]) 'VC\Auxiliary\Build\vcvars64.bat'
$nativeOutput = Join-Path $projectRoot 'editor\assets\native'
New-Item -ItemType Directory -Force -Path $nativeOutput | Out-Null
$buildOutput = Join-Path $projectRoot 'output\navigation-build'
New-Item -ItemType Directory -Force -Path $buildOutput | Out-Null
$batchPath = Join-Path $buildOutput 'build.cmd'
@"
@echo off
call "$vcvars" >nul
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /O2 /MT /LD /EHsc "$projectRoot\editor\native\navigation.cpp" /Fo"$buildOutput\navigation.obj" /link /OUT:"$nativeOutput\navigation.dll" /IMPLIB:"$buildOutput\navigation.lib"
"@ | Set-Content -LiteralPath $batchPath -Encoding ascii
& $batchPath
if ($LASTEXITCODE -ne 0) { throw 'Navigation library build failed' }
