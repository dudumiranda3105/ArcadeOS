$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$manifestPath = Join-Path $projectRoot '.runtime\processes.json'
if (-not (Test-Path -LiteralPath $manifestPath)) { Write-Output 'Nenhum processo registrado por start-local.ps1.'; return }
$records = @(Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json)
$remaining = @()
foreach ($record in ($records | Sort-Object id -Descending)) {
    $process = Get-Process -Id $record.id -ErrorAction SilentlyContinue
    if (-not $process) { continue }
    # Evita atingir outro processo caso o Windows tenha reutilizado o PID.
    if ([string]$process.StartTime.ToUniversalTime().Ticks -ne $record.start_ticks -or $process.Path -ne $record.executable) {
        Write-Warning "Identidade diferente para $($record.name); não será encerrado."
        continue
    }
    try { Stop-Process -Id $process.Id; Write-Output "$($record.name) encerrado." }
    catch { $remaining += $record; Write-Warning "Não foi possível encerrar $($record.name)." }
}
ConvertTo-Json -InputObject @($remaining) | Set-Content -LiteralPath $manifestPath -Encoding utf8
Write-Output 'Os arquivos do banco foram preservados.'
