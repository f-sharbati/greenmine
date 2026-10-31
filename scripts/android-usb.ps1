param([string]$Serial = '', [int]$ServerPort = 3001)
$ErrorActionPreference = 'Stop'
# The phone's localhost:3000 is forwarded to this computer's ServerPort.
$env:APP_ORIGIN = 'http://localhost:3000'
if (-not $env:PYTHON_EXECUTABLE) { $env:PYTHON_EXECUTABLE = 'python' }
if (-not $env:SMTP_REQUIRE_SETUP) { $env:SMTP_REQUIRE_SETUP = '1' }
$projectRoot = Split-Path $PSScriptRoot -Parent
$adb = if ($env:ANDROID_HOME) { Join-Path $env:ANDROID_HOME 'platform-tools/adb.exe' } else { 'adb' }
if (-not $Serial) {
    $devices = @(& $adb devices | Select-String '^([^\s]+)\s+device$' | ForEach-Object { $_.Matches[0].Groups[1].Value })
    if ($devices.Count -ne 1) { throw 'Connect and authorize one phone, or provide -Serial DEVICE_ID.' }
    $Serial = $devices[0]
}
$apk = Join-Path $projectRoot 'android/app/build/outputs/apk/debug/app-debug.apk'
& {
    Push-Location (Join-Path $projectRoot 'android')
    try { & ./gradlew.bat assembleDebug -PgreenmineLocal=true; if ($LASTEXITCODE -ne 0) { throw 'Android build failed.' } } finally { Pop-Location }
}
if (-not (Test-Path -LiteralPath (Join-Path $projectRoot '.next/BUILD_ID'))) {
    Push-Location $projectRoot
    try { & npm run build; if ($LASTEXITCODE -ne 0) { throw 'Web build failed.' } } finally { Pop-Location }
}
$listening = Get-NetTCPConnection -LocalPort $ServerPort -State Listen -ErrorAction SilentlyContinue
if (-not $listening) {
    $logDir = Join-Path $projectRoot '.local'
    New-Item -ItemType Directory -Force $logDir | Out-Null
    $next = Join-Path $projectRoot 'node_modules/next/dist/bin/next'
    $node = (Get-Command node).Source
    $process = Start-Process -FilePath $node -ArgumentList @("`"$next`"", 'start', '--hostname', '127.0.0.1', '--port', $ServerPort) -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logDir 'android-server.log') -RedirectStandardError (Join-Path $logDir 'android-server-error.log')
    Set-Content -Path (Join-Path $logDir 'android-server.pid') -Value $process.Id
    $ready = $false
    for ($i=0; $i -lt 30; $i++) {
        try { $response=Invoke-WebRequest "http://127.0.0.1:$ServerPort" -UseBasicParsing -TimeoutSec 3; if ($response.StatusCode -eq 200) {$ready=$true; break} } catch { Start-Sleep -Seconds 1 }
    }
    if (-not $ready) { throw 'Server did not start. Check .local/android-server-error.log.' }
}
& $adb -s $Serial reverse tcp:3000 "tcp:$ServerPort"
if ($LASTEXITCODE -ne 0) { throw 'USB reverse connection failed.' }
& $adb -s $Serial install -r $apk
if ($LASTEXITCODE -ne 0) { throw 'APK installation failed.' }
& $adb -s $Serial shell am start -n ir.greenmine.app.preview/ir.greenmine.app.MainActivity
Write-Output 'GreenMine is running on your phone. Keep the server running and USB connected.'
