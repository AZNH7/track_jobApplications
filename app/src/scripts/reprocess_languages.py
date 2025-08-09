"""
Script to reprocess job listings in the database to update their language.

This script fetches all job listings with 'unknown' language,
runs the new LLM-based language detection on them, and updates the database.
"""

import os
import sys
import time

# Add the src directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_manager import get_db_manager
from scrapers.job_scraper_orchestrator import JobScraperOrchestrator

def reprocess_job_languages():
    """
    Fetches jobs with unknown language, detects the language, and updates the database.
    """
    db_manager = None
    orchestrator = None
    updated_count = 0
    failed_count = 0

    try:
        print("Initializing database manager and job scraper orchestrator...")
        db_manager = get_db_manager(env="local")
        orchestrator = JobScraperOrchestrator()
        print("Initialization complete.")

        print("Fetching jobs with 'unknown' language from the database...")
        jobs_to_process = db_manager.execute_query(
            "SELECT id, description FROM job_listings WHERE language = 'unknown' OR language IS NULL OR language = ''",
            fetch='all'
        )

        if not jobs_to_process:
            print("No jobs with unknown language found. Nothing to do.")
            return

        print(f"Found {len(jobs_to_process)} jobs to reprocess.")
        
        for i, job in enumerate(jobs_to_process):
            job_id = job['id']
            description = job['description']
            
            print(f"Processing job {i+1}/{len(jobs_to_process)} (ID: {job_id})...")

            if not description or not description.strip():
                print(f"  -> Skipping job ID {job_id} due to empty description.")
                continue

            try:
                # Use the new, focused language detection method
                detected_language = orchestrator._llm_detect_language(description)
                
                if detected_language != 'unknown':
                    print(f"  -> Detected language: '{detected_language}'. Updating database...")
                    db_manager.execute_query(
                        "UPDATE job_listings SET language = %s WHERE id = %s",
                        params=(detected_language, job_id)
                    )
                    updated_count += 1
                    print(f"  -> Successfully updated job ID {job_id}.")
                else:
                    print(f"  -> Could not determine language for job ID {job_id}. Skipping.")
                
                # Add a small delay to avoid overwhelming the LLM service
                time.sleep(1)

            except Exception as e:
                print(f"  -> An error occurred while processing job ID {job_id}: {e}")
                failed_count += 1

    except Exception as e:
        print(f"An unexpected error occurred during the reprocessing script: {e}")
    
    finally:
        if db_manager:
            db_manager.close()
        if orchestrator:
            orchestrator.close()
        
        print("\n----- Reprocessing Summary -----")
        print(f"Successfully updated jobs: {updated_count}")
        print(f"Failed to process jobs: {failed_count}")
        print("------------------------------")


if __name__ == "__main__":
    reprocess_job_languages() 