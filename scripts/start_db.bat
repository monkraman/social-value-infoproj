@echo off
REM Batch script to start local PostgreSQL 17 with pgvector on port 5434
set PGDIR=C:\Users\hp\pgsql17
set PGDATA=%PGDIR%\data
set PGLOG=%PGDIR%\logfile.log

if not exist "%PGDATA%" (
    echo Initializing data directory at %PGDATA%...
    "%PGDIR%\bin\initdb.exe" -D "%PGDATA%" -U postgres -A trust -E UTF8
)

echo Starting PostgreSQL server on port 5434...
"%PGDIR%\bin\pg_ctl.exe" -D "%PGDATA%" -o "-p 5434" -l "%PGLOG%" start
echo PostgreSQL started on port 5434. Log: %PGLOG%
