param([switch]$NoDemo, [int]$Port = 5000)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$projectPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $projectPython)) { $projectPython = 'python' }
& $projectPython -c 'import flask' 2>$null
if ($LASTEXITCODE -ne 0) {
    throw 'Flask is missing. Run: python -m venv .venv; .\.venv\Scripts\python.exe -m pip install -r requirements.txt'
}
if ($NoDemo) { & $projectPython app.py --port $Port }
else { & $projectPython app.py --demo --port $Port }
