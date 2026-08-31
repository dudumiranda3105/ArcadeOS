param([string]$Mosquitto = 'mosquitto')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
& $Mosquitto -c (Join-Path $projectRoot 'infra\mosquitto.conf') -v
