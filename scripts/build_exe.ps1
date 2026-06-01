$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Spec = Join-Path $ProjectRoot "packaging\streamer_sidekick.spec"

if (-not (Test-Path $Python)) {
    throw "Venv nao encontrado em $Python. Crie com: python -m venv .venv"
}

Push-Location $ProjectRoot
try {
    & $Python -m PyInstaller --noconfirm --clean $Spec
    Write-Host ""
    Write-Host "Build concluido:"
    Write-Host (Join-Path $ProjectRoot "dist\StreamerSidekick\StreamerSidekick.exe")
}
finally {
    Pop-Location
}
