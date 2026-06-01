$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$DistFolder = Join-Path $ProjectRoot "dist\StreamerSidekick"
$ReleaseFolder = Join-Path $ProjectRoot "release"
$Version = "0.2.0"
$PackageName = "StreamerSidekick-$Version-portable"
$StageFolder = Join-Path $ReleaseFolder $PackageName
$ZipPath = Join-Path $ReleaseFolder "$PackageName.zip"

if (-not (Test-Path (Join-Path $DistFolder "StreamerSidekick.exe"))) {
    throw "Build nao encontrado. Rode primeiro: .\scripts\build_exe.ps1"
}

if (Test-Path $StageFolder) {
    Remove-Item -Recurse -Force $StageFolder
}
if (Test-Path $ZipPath) {
    Remove-Item -Force $ZipPath
}

New-Item -ItemType Directory -Force -Path $StageFolder | Out-Null
Copy-Item -Recurse -Force -Path (Join-Path $DistFolder "*") -Destination $StageFolder

@"
Streamer Sidekick $Version

Como abrir:
1. Extraia esta pasta inteira.
2. Execute StreamerSidekick.exe.

Importante:
- Nao remova a pasta _internal.
- Seus dados ficam no AppData do Windows, nao dentro desta pasta.
- Se as hotkeys nao funcionarem, execute como administrador ou confira a tela Diagnostico.
"@ | Set-Content -Path (Join-Path $StageFolder "LEIA-ME.txt") -Encoding UTF8

Compress-Archive -Path $StageFolder -DestinationPath $ZipPath -CompressionLevel Optimal

Write-Host ""
Write-Host "Pacote portatil criado:"
Write-Host $ZipPath
