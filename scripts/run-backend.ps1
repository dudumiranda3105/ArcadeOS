$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $projectRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Crie o ambiente primeiro: python -m venv .venv; instale backend/requirements.txt.'
}
& $pythonPath -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
