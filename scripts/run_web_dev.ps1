$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$FrontendDir = Join-Path $Root "hermina-crawler-fe"

if (-not (Test-Path (Join-Path $Root "apps\api\main.py"))) {
    throw "FastAPI backend tidak ditemukan di apps\api\main.py"
}

if (-not (Test-Path (Join-Path $FrontendDir "package.json"))) {
    throw "Next.js frontend tidak ditemukan di hermina-crawler-fe"
}

Write-Host "Starting Hermina Review Intelligence..." -ForegroundColor Green
Write-Host "Backend : http://localhost:8000/api/docs" -ForegroundColor Cyan
Write-Host "Frontend: http://localhost:3000" -ForegroundColor Cyan
Write-Host "Tekan Ctrl+C untuk stop FE dan BE." -ForegroundColor Yellow
Write-Host ""

$backendJob = Start-Job -Name "hermina-api" -ScriptBlock {
    param($RootPath)
    Set-Location $RootPath
    $env:PYTHONUNBUFFERED = "1"
    & python -m uvicorn apps.api.main:app --reload --port 8000 2>&1 | ForEach-Object { $_ }
} -ArgumentList $Root

$frontendJob = Start-Job -Name "hermina-web" -ScriptBlock {
    param($FrontendPath)
    Set-Location $FrontendPath
    & npm run dev -- --hostname 127.0.0.1 --port 3000 2>&1 | ForEach-Object { $_ }
} -ArgumentList $FrontendDir

try {
    while ($true) {
        Receive-Job -Job $backendJob, $frontendJob -ErrorAction Continue

        if ($backendJob.State -eq "Failed") {
            Receive-Job -Job $backendJob -ErrorAction Continue
            throw "Backend process gagal. Cek output di atas."
        }

        if ($frontendJob.State -eq "Failed") {
            Receive-Job -Job $frontendJob -ErrorAction Continue
            throw "Frontend process gagal. Cek output di atas."
        }

        if ($backendJob.State -in @("Stopped", "Completed")) {
            Receive-Job -Job $backendJob -ErrorAction Continue
            throw "Backend process berhenti. Cek output di atas."
        }

        if ($frontendJob.State -in @("Stopped", "Completed")) {
            Receive-Job -Job $frontendJob -ErrorAction Continue
            throw "Frontend process berhenti. Cek output di atas."
        }

        Start-Sleep -Seconds 1
    }
}
finally {
    Write-Host "Stopping dev processes..." -ForegroundColor Yellow
    Stop-Job -Job $backendJob, $frontendJob -ErrorAction SilentlyContinue
    Remove-Job -Job $backendJob, $frontendJob -Force -ErrorAction SilentlyContinue
}
