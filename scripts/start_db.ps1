# PowerShell script to start local PostgreSQL 17 with pgvector on port 5434
$pgDir = "C:\Users\hp\pgsql17"
$pgData = "$pgDir\data"
$pgLog = "$pgDir\logfile.log"

if (-not (Test-Path $pgData)) {
    Write-Host "Initializing data directory at $pgData..." -ForegroundColor Yellow
    & "$pgDir\bin\initdb.exe" -D $pgData -U postgres -A trust -E UTF8
}

Write-Host "Starting PostgreSQL server on port 5434..." -ForegroundColor Green
& "$pgDir\bin\pg_ctl.exe" -D $pgData -o "-p 5434" -l $pgLog start
Write-Host "PostgreSQL started. Log: $pgLog" -ForegroundColor Cyan
