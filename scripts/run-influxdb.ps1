param([string]$Influxd = 'influxd')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$dataRoot = Join-Path $projectRoot '.runtime\influxdb'
New-Item -ItemType Directory -Path $dataRoot -Force | Out-Null
& $Influxd --http-bind-address 127.0.0.1:8086 --bolt-path (Join-Path $dataRoot 'influxd.bolt') --sqlite-path (Join-Path $dataRoot 'influxd.sqlite') --engine-path (Join-Path $dataRoot 'engine') --reporting-disabled
