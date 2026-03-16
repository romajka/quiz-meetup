$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Test-Path ".venv\\Scripts\\python.exe") {
    & ".venv\\Scripts\\python.exe" "run.py"
    exit $LASTEXITCODE
}

$python = Get-Command python -ErrorAction SilentlyContinue
if ($python) {
    & python "run.py"
    exit $LASTEXITCODE
}

Write-Host "Python не найден. Установите Python 3.11+ или создайте .venv."
exit 1
