-- Job Tracker Database Initialization
-- This script runs once when the PostgreSQL container first starts.
-- Tables are intentionally NOT defined here — the Python ORM (database_manager.py)
-- is the single source of truth for schema. Defining tables here as well caused
-- schema drift: SQL created minimal stubs, then Python's CREATE TABLE IF NOT EXISTS
-- silently kept the wrong schema.

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Set timezone
SET timezone = 'UTC';

-- Create schemas for better organization
CREATE SCHEMA IF NOT EXISTS job_tracker;
CREATE SCHEMA IF NOT EXISTS analytics;

-- Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA job_tracker TO jobtracker;
GRANT ALL PRIVILEGES ON SCHEMA analytics TO jobtracker;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA job_tracker TO jobtracker;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA job_tracker TO jobtracker;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA job_tracker TO jobtracker;

-- Set default schema
ALTER USER jobtracker SET search_path = job_tracker, public;

-- Create performance monitoring view
CREATE OR REPLACE VIEW analytics.database_stats AS
SELECT
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation
FROM pg_stats
WHERE schemaname = 'job_tracker';

SELECT 'Job Tracker PostgreSQL database initialized successfully!' AS message;
