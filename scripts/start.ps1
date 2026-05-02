$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location "$scriptDir\.."
docker compose up --build -d
Write-Host "App started at http://localhost:8000"
