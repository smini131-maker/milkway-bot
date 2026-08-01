$TaskName = "MilkwayBot"
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
Write-Host "MilkwayBot 자동 시작 작업을 삭제했습니다."
