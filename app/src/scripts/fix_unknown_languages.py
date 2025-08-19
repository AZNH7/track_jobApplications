#!/usr/bin/env python3
"""
Script to fix jobs with 'unknown' language labels by reprocessing them with improved detection.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from database_manager import get_db_manager
from scrapers.job_scraper_orchestrator import JobScraperOrchestrator

def fix_unknown_languages():
    """Reprocess jobs with unknown language labels"""
    
    db_manager = get_db_manager()
    orchestrator = JobScraperOrchestrator()
    
    try:
        # Get jobs with unknown language
        query = """
            SELECT id, title, description, company, url 
            FROM job_listings 
            WHERE language = 'unknown' OR language IS NULL OR language = ''
            ORDER BY scraped_date DESC
        """
        
        unknown_jobs = db_manager.execute_query(query, fetch='all')
        
        if not unknown_jobs:
            print("✅ No jobs with unknown language found!")
            return
        
        print(f"🔍 Found {len(unknown_jobs)} jobs with unknown language")
        print("🔄 Reprocessing with improved language detection...")
        
        updated_count = 0
        skipped_count = 0
        
        for job_data in unknown_jobs:
            job_id, title, description, company, url = job_data
            
            # Prepare job dict for language detection
            job = {
                'id': job_id,
                'title': title or '',
                'description': description or '',
                'company': company or '',
                'url': url or ''
            }
            
            # Use improved language detection with title prioritization
            title_text = job.get('title', '') or ''
            description_text = job.get('description', '') or ''
            
            if len(description_text.strip()) > 100:
                # Use LLM detection for full descriptions
                detected_language = orchestrator._llm_detect_language(description_text)
                method = "LLM"
            elif len(description_text.strip()) > 30 and 'linkedin.com' in job.get('url', ''):
                # Use LinkedIn-specific detection
                detected_language = orchestrator._detect_linkedin_language(description_text, title_text)
                method = "LinkedIn"
            elif len(title_text.strip()) > 0:
                # Prioritize title-based detection when description is insufficient
                if len(description_text.strip()) > 30:
                    # Use combined title + description for better accuracy
                    combined_text = f"{title_text} {description_text}".strip()
                    detected_language = orchestrator._fallback_language_detection(combined_text)
                    method = "Title + Description"
                else:
                    # Use title-only detection when description is too short
                    detected_language = orchestrator._fallback_language_detection(title_text)
                    method = "Title Only"
            else:
                # Fallback to description only if no title
                detected_language = orchestrator._fallback_language_detection(description_text)
                method = "Description Only"
            
            # Only update if we got a better result
            if detected_language and detected_language != 'unknown':
                # Update the database
                update_query = "UPDATE job_listings SET language = %s WHERE id = %s"
                db_manager.execute_query(update_query, (detected_language, job_id))
                
                print(f"   ✅ Updated job {job_id}: '{title[:50]}...' -> {detected_language} ({method})")
                updated_count += 1
            else:
                print(f"   ⚠️  Still unknown: '{title[:50]}...' (insufficient content)")
                skipped_count += 1
        
        print(f"\n📊 Results:")
        print(f"   ✅ Updated: {updated_count} jobs")
        print(f"   ⚠️  Still unknown: {skipped_count} jobs")
        print(f"   📈 Success rate: {(updated_count / len(unknown_jobs)) * 100:.1f}%")
        
    except Exception as e:
        print(f"❌ Error processing unknown languages: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_unknown_languages() 