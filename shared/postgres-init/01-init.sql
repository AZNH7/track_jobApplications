-- Job Tracker Database Initialization
-- This script runs automatically when PostgreSQL container starts

-- Create database if it doesn't exist (handled by POSTGRES_DB env var)
-- Create user if it doesn't exist (handled by POSTGRES_USER env var)

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

-- Log successful initialization
-- INSERT INTO pg_stat_statements_info DEFAULT VALUES
-- ON CONFLICT DO NOTHING;

-- Success message
SELECT 'Job Tracker PostgreSQL database initialized successfully!' as message;

-- Add new tables

CREATE TABLE job_listings (
    id SERIAL PRIMARY KEY,
    title TEXT,
    company TEXT,
    location TEXT,
    salary TEXT,
    url TEXT UNIQUE,
    source TEXT,
    scraped_date TIMESTAMP,
    posted_date TEXT,
    description TEXT,
    language TEXT
);

-- Job offers table
CREATE TABLE job_offers (
    id SERIAL PRIMARY KEY,
    company TEXT NOT NULL,
    role TEXT NOT NULL,
    base_salary DECIMAL(12,2),
    bonus DECIMAL(12,2),
    benefits TEXT,
    location TEXT,
    remote_policy TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status TEXT DEFAULT 'active',
    notes TEXT,
    benefits_score DECIMAL(3,2),
    work_life_balance_score DECIMAL(3,2),
    growth_score DECIMAL(3,2)
);

-- Filtered jobs table
CREATE TABLE filtered_jobs (
    id SERIAL PRIMARY KEY,
    job_id INTEGER REFERENCES job_listings(id) ON DELETE CASCADE,
    reason TEXT NOT NULL,
    filter_type TEXT NOT NULL,  -- 'auto' or 'manual'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    notes TEXT,
    UNIQUE(job_id)
);

-- Create indexes
CREATE INDEX idx_job_offers_company ON job_offers(company);
CREATE INDEX idx_job_offers_status ON job_offers(status);
CREATE INDEX idx_filtered_jobs_type ON filtered_jobs(filter_type);
CREATE INDEX idx_filtered_jobs_created ON filtered_jobs(created_at);

-- Create trigger for updating timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_job_offers_updated_at
    BEFORE UPDATE ON job_offers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_filtered_jobs_updated_at
    BEFORE UPDATE ON filtered_jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column(); 