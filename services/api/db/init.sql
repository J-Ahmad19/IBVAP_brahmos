-- Initialization script for PostgreSQL + TimescaleDB
-- Tables are managed via Alembic migrations.

-- 1. Create the TimescaleDB extension if it doesn't exist
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
