param([int]$Port = 5050)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$mqttPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $mqttPython)) { $mqttPython = 'python' }
& $mqttPython -c 'import flask; import paho.mqtt.client' 2>$null
if ($LASTEXITCODE -ne 0) {
    throw 'Install project dependencies first: .\.venv\Scripts\python.exe -m pip install -r requirements.txt'
}
& $mqttPython mqtt_setup.py
if ($LASTEXITCODE -ne 0) { throw 'MQTT setup failed; see the message above.' }
& $mqttPython mqtt_bridge.py --public-demo --serve --port $Port
