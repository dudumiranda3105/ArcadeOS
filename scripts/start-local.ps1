param([switch]$Simulate)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $projectRoot
$runtimeDir = Join-Path $projectRoot '.runtime'
New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null
$manifestPath = Join-Path $runtimeDir 'processes.json'
$owned = @()
if (Test-Path -LiteralPath $manifestPath) {
    $owned = @(Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json)
}
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
$nodeCommand = Get-Command node -ErrorAction SilentlyContinue
$nodePath = if ($nodeCommand) { $nodeCommand.Source } else {
    Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe'
}
$mosquittoPath = Join-Path $projectRoot '.tools\mosquitto\mosquitto.exe'
if (-not (Test-Path -LiteralPath $mosquittoPath)) {
    $mosquittoPath = 'C:\Program Files\mosquitto\mosquitto.exe'
}
$influxPath = Join-Path $projectRoot '.tools\influxdb\influxd.exe'
if (-not (Test-Path -LiteralPath $influxPath)) {
    $influxCommand = Get-Command influxd -ErrorAction SilentlyContinue
    if ($influxCommand) { $influxPath = $influxCommand.Source }
}
foreach ($required in @($pythonPath, $nodePath, $mosquittoPath, $influxPath, (Join-Path $projectRoot 'node_modules\vite\bin\vite.js'), (Join-Path $projectRoot 'backend\.env'))) {
    if (-not (Test-Path -LiteralPath $required)) { throw "Arquivo necessário ausente: $required. Siga primeiro a instalação no README." }
}
function Test-LocalPort([int]$Port) {
    $connection = New-Object System.Net.Sockets.TcpClient
    try { $connection.Connect('127.0.0.1', $Port); return $true }
    catch { return $false }
    finally { $connection.Dispose() }
}
function Start-ArcadeProcess([string]$Name, [string]$Executable, [string]$Arguments, [int]$Port = 0) {
    if ($Port -and (Test-LocalPort $Port)) { Write-Output "$Name já está na porta $Port; mantido."; return }
    # Retém somente processos iniciados por este script; o stop-local não encerra terceiros.
    if (-not $Port) {
        foreach ($record in $script:owned) {
            if ($record.name -ne $Name) { continue }
            $existing = Get-Process -Id $record.id -ErrorAction SilentlyContinue
            if ($existing -and [string]$existing.StartTime.ToUniversalTime().Ticks -eq $record.start_ticks) { Write-Output "$Name já iniciado."; return }
        }
    }
    $process = Start-Process -FilePath $Executable -ArgumentList $Arguments -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtimeDir "$Name.log") -RedirectStandardError (Join-Path $runtimeDir "$Name.error.log")
    $script:owned += [pscustomobject]@{ name=$Name; id=$process.Id; start_ticks=[string]$process.StartTime.ToUniversalTime().Ticks; executable=$Executable }
    ConvertTo-Json -InputObject @($script:owned) | Set-Content -LiteralPath $manifestPath -Encoding utf8
    if ($Port) {
        $deadline = (Get-Date).AddSeconds(20)
        while (-not (Test-LocalPort $Port)) {
            if ($process.HasExited -or (Get-Date) -gt $deadline) { throw "$Name não iniciou. Veja .runtime/$Name.error.log." }
            Start-Sleep -Milliseconds 300
        }
    }
    Write-Output "$Name iniciado."
}
$env:PATH = (Split-Path $nodePath -Parent) + ';' + $env:PATH
Start-ArcadeProcess 'mosquitto' $mosquittoPath ('-c "' + (Join-Path $projectRoot 'infra\mosquitto.conf') + '" -v') 1883
$dataRoot = Join-Path $runtimeDir 'influxdb'
New-Item -ItemType Directory -Path $dataRoot -Force | Out-Null
$influxArgs = '--http-bind-address 127.0.0.1:8086 --reporting-disabled --bolt-path "' + (Join-Path $dataRoot 'influxd.bolt') + '" --sqlite-path "' + (Join-Path $dataRoot 'influxd.sqlite') + '" --engine-path "' + (Join-Path $dataRoot 'engine') + '"'
Start-ArcadeProcess 'influxdb' $influxPath $influxArgs 8086
Start-ArcadeProcess 'backend' $pythonPath '-m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000' 8000
Start-ArcadeProcess 'frontend' $nodePath 'node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5173 --strictPort' 5173
if ($Simulate) { Start-ArcadeProcess 'simulator' $pythonPath '-u backend/simulate.py --scenario cycle' }
Write-Output 'ArcadeOS: http://127.0.0.1:5173'
Write-Output 'Demonstração visual: http://127.0.0.1:5173/?demo=1'
Write-Output 'Para encerrar somente os processos criados por este script: .\scripts\stop-local.ps1'
