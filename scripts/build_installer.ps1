$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$Iscc = Get-Command ISCC.exe -ErrorAction SilentlyContinue
$Spec = Join-Path $ProjectRoot "packaging\inno\streamer_sidekick.iss"

if ($null -eq $Iscc) {
    throw "Inno Setup nao encontrado no PATH. Instale o Inno Setup e tente novamente: https://jrsoftware.org/isdl.php"
}

Push-Location $ProjectRoot
try {
    & (Join-Path $ProjectRoot "scripts\build_exe.ps1")
    & $Iscc.Source $Spec
    Write-Host ""
    Write-Host "Instalador criado em:"
    Write-Host (Join-Path $ProjectRoot "release")
}
finally {
    Pop-Location
}
