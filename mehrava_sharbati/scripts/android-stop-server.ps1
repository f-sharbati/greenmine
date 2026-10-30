$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$pidFile = Join-Path $projectRoot '.local/android-server.pid'
if (-not (Test-Path -LiteralPath $pidFile)) { Write-Output 'No managed Android server PID.'; exit }
$serverProcessId = [int](Get-Content -LiteralPath $pidFile)
$serverProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$serverProcessId"
if ($serverProcess -and $serverProcess.CommandLine.Contains($projectRoot) -and $serverProcess.CommandLine.Contains('next')) {
    Stop-Process -Id $serverProcessId
    Write-Output 'Stopped the GreenMine Android server.'
} else { Write-Output 'The recorded server is no longer running. No other process was stopped.' }
