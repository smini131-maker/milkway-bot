$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$LogDirectory = Join-Path $ProjectRoot "data"
$LogFile = Join-Path $LogDirectory "milkway-bot.log"

if (-not (Test-Path $Python)) {
    throw "가상환경을 찾을 수 없습니다: $Python"
}
if (-not (Test-Path (Join-Path $ProjectRoot ".env"))) {
    throw ".env 파일을 찾을 수 없습니다."
}

New-Item -ItemType Directory -Path $LogDirectory -Force | Out-Null
Set-Location $ProjectRoot
& $Python -m discord_bot *>> $LogFile
