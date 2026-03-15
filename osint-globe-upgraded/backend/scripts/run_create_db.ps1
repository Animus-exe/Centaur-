# Create Centaur database and user in PostgreSQL
# You will be prompted for the postgres superuser password (if set).
$psql = "C:\Program Files\PostgreSQL\18\bin\psql.exe"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
& $psql -U postgres -f "$scriptDir\create_db.sql"
if ($LASTEXITCODE -eq 0) { Write-Host "Database ready. Start the backend and frontend." } else { Write-Host "If you see 'already exists', that is OK. Otherwise check your postgres password." }
