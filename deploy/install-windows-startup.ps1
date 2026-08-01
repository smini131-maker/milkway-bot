$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Runner = Join-Path $PSScriptRoot "run-windows.ps1"
$PowerShell = (Get-Command powershell.exe).Source
$TaskName = "MilkwayBot"

if (-not (Test-Path (Join-Path $ProjectRoot ".venv\Scripts\python.exe"))) {
    throw "먼저 프로젝트 폴더에서 python -m venv .venv 와 pip install -e . 를 실행하세요."
}
if (-not (Test-Path (Join-Path $ProjectRoot ".env"))) {
    throw "먼저 .env 파일을 설정하세요."
}

$Action = New-ScheduledTaskAction `
    -Execute $PowerShell `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$Runner`"" `
    -WorkingDirectory $ProjectRoot
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Days 0)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Milkway Discord Bot 자동 실행" `
    -Force | Out-Null

Start-ScheduledTask -TaskName $TaskName
Write-Host "MilkwayBot 자동 시작 작업을 등록하고 실행했습니다."
Write-Host "상태 확인: Get-ScheduledTask -TaskName MilkwayBot"
Write-Host "로그 위치: $ProjectRoot\data\milkway-bot.log"
Write-Host "주의: Windows가 종료되거나 절전 상태가 되면 봇도 오프라인이 됩니다."
