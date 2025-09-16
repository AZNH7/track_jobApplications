-- Migration script to fix decimal precision overflow issues
-- This script updates DECIMAL(3,2) columns to DECIMAL(4,2) to allow values up to 99.99

-- Fix job_listings table LLM score columns
ALTER TABLE job_listings 
ALTER COLUMN llm_quality_score TYPE DECIMAL(4,2);

ALTER TABLE job_listings 
ALTER COLUMN llm_relevance_score TYPE DECIMAL(4,2);

-- Fix job_offers table score columns
ALTER TABLE job_offers 
ALTER COLUMN benefits_score TYPE DECIMAL(4,2);

ALTER TABLE job_offers 
ALTER COLUMN work_life_balance_score TYPE DECIMAL(4,2);

ALTER TABLE job_offers 
ALTER COLUMN growth_score TYPE DECIMAL(4,2);

-- Add comment to document the change
COMMENT ON COLUMN job_listings.llm_quality_score IS 'LLM quality score (0.00-10.00)';
COMMENT ON COLUMN job_listings.llm_relevance_score IS 'LLM relevance score (0.00-10.00)';
COMMENT ON COLUMN job_offers.benefits_score IS 'Benefits score (0.00-10.00)';
COMMENT ON COLUMN job_offers.work_life_balance_score IS 'Work-life balance score (0.00-10.00)';
COMMENT ON COLUMN job_offers.growth_score IS 'Growth opportunity score (0.00-10.00)';
