-- Run as postgres: psql -U postgres -f create_db.sql
-- Creates osint user and database (idempotent).
-- PostGIS is enabled by the app on first startup; to enable it here instead:
--   psql -U postgres -d osint -c "CREATE EXTENSION IF NOT EXISTS postgis;"
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'osint') THEN
    CREATE ROLE osint WITH LOGIN PASSWORD 'osint';
  ELSE
    ALTER ROLE osint PASSWORD 'osint';
  END IF;
END
$$;
-- Ignore error if database already exists
CREATE DATABASE osint OWNER osint;
