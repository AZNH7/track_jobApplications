"""
Platform utilities for Job Tracker
"""

import re
from typing import Dict, List, Optional
import time

class PlatformUtils:
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def test_platform(self, platform: str, keywords: str, location: str, max_pages: int, english_only: bool = False) -> Dict:
        """Test a job platform"""
        try:
            # Initialize scraper orchestrator
            from scrapers import JobScraperOrchestrator
            
            with JobScraperOrchestrator(debug=True) as orchestrator:
                # Test the platform by searching for jobs
                try:
                    jobs_df = orchestrator.search_selected_platforms(
                        keywords=keywords,
                        location=location,
                        max_pages=max_pages,
                        selected_platforms=[platform.lower()],
                        english_only=english_only
                    )
                    
                    if not jobs_df.empty:
                        jobs_list = jobs_df.to_dict('records')
                        total_jobs = len(jobs_list)
                        sample_jobs = jobs_list[:3]  # Return only top 3 sample jobs
                        
                        return {
                            "success": True,
                            "jobs_found": total_jobs,
                            "sample_jobs": sample_jobs
                        }
                    else:
                        return {
                            "success": True,
                            "jobs_found": 0,
                            "sample_jobs": []
                        }
                        
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Error testing platform {platform}: {str(e)}",
                        "jobs_found": 0
                    }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "jobs_found": 0
            }
    
    def _is_english_job(self, job: Dict) -> bool:
        """Check if a job posting is in English"""
        # Common German words that indicate a German job posting
        german_indicators = [
            'und', 'oder', 'für', 'mit', 'bei', 'seit', 'von', 'aus',
            'nach', 'bei', 'zur', 'zum', 'der', 'die', 'das', 'den',
            'dem', 'dessen', 'deren', 'denen', 'diese', 'dieser',
            'dieses', 'jene', 'jener', 'jenes'
        ]
        
        # Combine title and description for analysis
        text = f"{job.get('title', '')} {job.get('description', '')}".lower()
        
        # Count German words
        german_word_count = sum(1 for word in german_indicators if f" {word} " in f" {text} ")
        
        # If more than 3 German indicator words are found, consider it a German posting
        return german_word_count <= 3
    
    def get_platform_stats(self) -> Dict:
        """Get platform statistics"""
        try:
            stats = {}
            
            # Get total jobs per platform
            query = """
                SELECT 
                    platform,
                    COUNT(*) as total_jobs,
                    COUNT(DISTINCT company) as unique_companies,
                    AVG(CASE WHEN salary IS NOT NULL THEN salary ELSE 0 END) as avg_salary
                FROM job_listings
                WHERE scraped_date >= NOW() - INTERVAL '30 days'
                GROUP BY platform
            """
            results = self.db_manager.execute_query(query, fetch='all')
            
            for row in results:
                stats[row['platform']] = {
                    'total_jobs': row['total_jobs'],
                    'unique_companies': row['unique_companies'],
                    'avg_salary': row['avg_salary']
                }
            
            # Get success rate (applications/offers)
            query = """
                SELECT 
                    platform,
                    COUNT(*) as total_applications,
                    COUNT(CASE WHEN status = 'offer' THEN 1 END) as offers
                FROM job_applications
                WHERE applied_date >= NOW() - INTERVAL '90 days'
                GROUP BY platform
            """
            results = self.db_manager.execute_query(query, fetch='all')
            
            for row in results:
                if row['platform'] in stats:
                    stats[row['platform']].update({
                        'applications': row['total_applications'],
                        'offers': row['offers'],
                        'success_rate': row['offers'] / row['total_applications'] if row['total_applications'] > 0 else 0
                    })
            
            return stats
            
        except Exception as e:
            print(f"Error getting platform stats: {e}")
            return {} 