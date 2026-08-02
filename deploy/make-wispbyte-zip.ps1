$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$OutputPath = Join-Path (Split-Path -Parent $ProjectRoot) "milkway-wispbyte.zip"
$StagePath = Join-Path $env:TEMP "milkway-wispbyte-stage"

Remove-Item $StagePath -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $OutputPath -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $StagePath -Force | Out-Null

$ExcludedNames = @(
    ".git",
    ".github",
    ".venv",
    ".env",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "logs"
)

Get-ChildItem -Path $ProjectRoot -Force | Where-Object {
    $_.Name -notin $ExcludedNames
} | ForEach-Object {
    Copy-Item $_.FullName -Destination $StagePath -Recurse -Force
}

Get-ChildItem -Path $StagePath -Recurse -Directory -Filter "__pycache__" |
    Remove-Item -Recurse -Force
Get-ChildItem -Path $StagePath -Recurse -File -Include "*.pyc", "*.pyo" |
    Remove-Item -Force

Compress-Archive -Path (Join-Path $StagePath "*") -DestinationPath $OutputPath -Force
Remove-Item $StagePath -Recurse -Force

Write-Host "Wispbyte upload ZIP created: $OutputPath"
Write-Host ".env and local virtual environments were excluded."
