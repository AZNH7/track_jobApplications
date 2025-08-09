"""
Enhanced Job Grouping Service using Ollama LLM
Groups jobs by company and position while handling multiple cities intelligently
"""

import pandas as pd
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
import re
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from ollama_client import ollama_client

@dataclass
class JobGroup:
    """Represents a group of similar jobs"""
    company: str
    title: str
    normalized_title: str
    cities: List[str]
    jobs: List[Dict[str, Any]]
    avg_salary: Optional[str] = None
    platforms: Optional[List[str]] = None
    total_positions: int = 0
    
    def __post_init__(self):
        if self.platforms is None:
            self.platforms = list(set([job.get('platform', job.get('source', 'Unknown')) for job in self.jobs if job]))
        self.total_positions = len(self.jobs)

class JobGroupingService:
    """
    Advanced job grouping service using Ollama LLM for intelligent grouping
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.ollama_available = ollama_client.available
        
        # Salary patterns for extraction and normalization
        self.salary_patterns = [
            r'(\d+[,.]?\d*)[k]?\s*[-–]\s*(\d+[,.]?\d*)[k]?.*(?:€|EUR|euro)',
            r'€\s*(\d+[,.]?\d*)(?:[.,]\d+)?[k]?\s*[-–]\s*€?\s*(\d+[,.]?\d*)(?:[.,]\d+)?[k]?',
            r'(\d+[,.]?\d*)\s*[-–]\s*(\d+[,.]?\d*)\s*(?:€|EUR|euro)',
            r'up to\s*€?\s*(\d+[,.]?\d*)(?:[.,]\d+)?[k]?',
            r'starting from\s*€?\s*(\d+[,.]?\d*)(?:[.,]\d+)?[k]?'
        ]
        
        if not self.ollama_available:
            self.logger.warning("Ollama LLM not available. Using basic grouping fallback.")
    
    def _normalize_job_dict(self, job: dict) -> dict:
        """Ensure all relevant job fields are strings and not None."""
        job = dict(job)  # Make a copy
        for key in ['title', 'company', 'location', 'salary']:
            value = job.get(key, '')
            if value is None:
                job[key] = ''
            elif not isinstance(value, str):
                job[key] = str(value)
        return job

    def group_jobs_by_similarity(self, jobs_df: pd.DataFrame) -> Dict[str, JobGroup]:
        """
        Group jobs by company and position using LLM for intelligent matching
        
        Args:
            jobs_df: DataFrame containing job listings
            
        Returns:
            Dictionary mapping group_id to JobGroup objects
        """
        if jobs_df.empty:
            return {}
        
        self.logger.info(f"Starting job grouping for {len(jobs_df)} jobs")
        
        # Convert DataFrame to list of dictionaries
        jobs_list = [self._normalize_job_dict(job) for job in jobs_df.to_dict('records')]
        
        if self.ollama_available:
            return self._group_jobs_with_llm(jobs_list)
        else:
            return self._group_jobs_basic(jobs_list)
    
    def group_jobs_optimized(self, jobs_df: pd.DataFrame, skip_llm: bool = False) -> Dict[str, JobGroup]:
        """
        Optimized job grouping with option to skip LLM processing for speed
        
        Args:
            jobs_df: DataFrame containing job listings
            skip_llm: Skip LLM processing for faster grouping
            
        Returns:
            Dictionary mapping group_id to JobGroup objects
        """
        if jobs_df.empty:
            return {}
        
        self.logger.info(f"Starting optimized job grouping for {len(jobs_df)} jobs (skip_llm={skip_llm})")
        
        # Convert DataFrame to list of dictionaries
        jobs_list = [self._normalize_job_dict(job) for job in jobs_df.to_dict('records')]
        
        if skip_llm or not self.ollama_available:
            return self._group_jobs_fast(jobs_list)
        else:
            return self._group_jobs_with_llm(jobs_list)
    
    def _group_jobs_with_llm(self, jobs_list: List[Dict]) -> Dict[str, JobGroup]:
        """
        Group jobs using LLM for intelligent similarity detection
        """
        grouped_jobs = {}
        processed_jobs = set()
        
        for i, job in enumerate(jobs_list):
            if i in processed_jobs:
                continue
                
            # Find similar jobs using LLM
            similar_jobs = [job]
            similar_indices = {i}
            
            for j, other_job in enumerate(jobs_list[i+1:], i+1):
                if j in processed_jobs:
                    continue
                    
                if self._are_jobs_similar_llm(job, other_job):
                    similar_jobs.append(other_job)
                    similar_indices.add(j)
            
            # Mark all similar jobs as processed
            processed_jobs.update(similar_indices)
            
            # Create job group
            group = self._create_job_group(similar_jobs)
            group_id = f"{group.company}_{group.normalized_title}".replace(" ", "_").lower()
            grouped_jobs[group_id] = group
            
            self.logger.info(f"Created group '{group_id}' with {len(similar_jobs)} jobs in cities: {group.cities}")
        
        return grouped_jobs
    
    def _are_jobs_similar_llm(self, job1: Dict, job2: Dict) -> bool:
        """
        Use LLM to determine if two jobs are similar (same company and position type)
        """
        try:
            # Extract key information for comparison
            company1 = job1.get('company', '')
            company2 = job2.get('company', '')
            title1 = job1.get('title', '')
            title2 = job2.get('title', '')
            
            company1 = company1.strip() if company1 else ''
            company2 = company2.strip() if company2 else ''
            title1 = title1.strip() if title1 else ''
            title2 = title2.strip() if title2 else ''
            
            # Quick company name check first
            if not self._companies_similar(company1, company2):
                return False
            
            # Use LLM to check if job titles are similar
            system_prompt = """You are an expert at comparing job titles. Determine if two job titles represent the same type of position, even if worded differently.

Consider these as SIMILAR:
- "Software Engineer" and "Software Developer" 
- "Frontend Developer" and "Front-end Engineer"
- "Data Scientist" and "Data Science Specialist"
- "Marketing Manager" and "Marketing Lead"
- "DevOps Engineer" and "DevOps Specialist"

Consider these as DIFFERENT:
- "Software Engineer" and "Data Scientist"
- "Frontend Developer" and "Backend Developer" 
- "Marketing Manager" and "Sales Manager"
- "Junior Developer" and "Senior Developer" (different seniority levels)

Respond with only "YES" if they are similar positions, or "NO" if they are different."""

            prompt = f"""Compare these two job titles:

Title 1: "{title1}"
Title 2: "{title2}"

Are these similar positions?"""

            response = ollama_client.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=10,
                temperature=0.1
            )
            
            if response and response.strip():
                return response.strip().upper() == "YES"
                
        except Exception as e:
            self.logger.error(f"Error in LLM job comparison: {e}")
        
        # Fallback to basic comparison
        return self._are_jobs_similar_basic(job1, job2)
    
    def _companies_similar(self, company1: str, company2: str) -> bool:
        """
        Check if two company names are similar using LLM
        """
        if not company1 or not company2:
            return False
            
        # Exact match
        if company1.lower() == company2.lower():
            return True
            
        # Use LLM for company name comparison
        try:
            system_prompt = """You are an expert at comparing company names. Determine if two company names refer to the same company, accounting for:
- Different legal suffixes (GmbH, Ltd, Inc, etc.)
- Abbreviations vs full names
- Minor spelling differences

Respond with only "YES" if they are the same company, or "NO" if they are different companies."""

            prompt = f"""Are these the same company?

Company 1: "{company1}"
Company 2: "{company2}"

Are they the same company?"""

            response = ollama_client.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=10,
                temperature=0.1
            )
            
            if response and response.strip() and response.strip().upper() == "YES":
                return True
                
        except Exception as e:
            self.logger.error(f"Error in LLM company comparison: {e}")
        
        # Fallback to basic string similarity
        return self._basic_company_similarity(company1, company2)
    
    def _basic_company_similarity(self, company1: str, company2: str) -> bool:
        """
        Basic company name similarity check
        """
        # Normalize company names
        def normalize_company(name):
            if not name:
                return ''
            name = name.lower().strip()
            # Remove common suffixes
            suffixes = ['gmbh', 'ltd', 'inc', 'corp', 'ag', 'se', 'plc', 'llc', '&', 'und', 'and']
            for suffix in suffixes:
                name = re.sub(rf'\b{suffix}\b', '', name).strip()
            return name
        
        norm1 = normalize_company(company1)
        norm2 = normalize_company(company2)
        
        # Check if one is contained in the other
        if norm1 in norm2 or norm2 in norm1:
            return True
            
        # Check Levenshtein distance for small differences
        from difflib import SequenceMatcher
        similarity = SequenceMatcher(None, norm1, norm2).ratio()
        return similarity >= 0.8
    
    def _group_jobs_basic(self, jobs_list: List[Dict]) -> Dict[str, JobGroup]:
        """
        Fallback basic job grouping when LLM is not available
        """
        groups = defaultdict(list)
        
        for job in jobs_list:
            company = job.get('company', '')
            title = job.get('title', '')
            
            company = company.strip().lower() if company else ''
            title = title.strip().lower() if title else ''
            
            # Create a basic grouping key
            group_key = f"{company}_{title}".replace(" ", "_")
            groups[group_key].append(job)
        
        # Convert to JobGroup objects
        job_groups = {}
        for group_key, job_list in groups.items():
            if len(job_list) > 0:
                group = self._create_job_group(job_list)
                job_groups[group_key] = group
        
        return job_groups
    
    def _are_jobs_similar_basic(self, job1: Dict, job2: Dict) -> bool:
        """
        Basic job similarity check without LLM
        """
        company1 = job1.get('company', '')
        company2 = job2.get('company', '')
        title1 = job1.get('title', '')
        title2 = job2.get('title', '')
        
        company1 = company1.strip().lower() if company1 else ''
        company2 = company2.strip().lower() if company2 else ''
        title1 = title1.strip().lower() if title1 else ''
        title2 = title2.strip().lower() if title2 else ''
        
        # Simple string matching
        company_match = company1 == company2 or company1 in company2 or company2 in company1
        title_match = title1 == title2 or title1 in title2 or title2 in title1
        
        return company_match and title_match
    
    def _group_jobs_fast(self, jobs_list: List[Dict]) -> Dict[str, JobGroup]:
        """
        Fast job grouping without LLM processing
        """
        grouped_jobs = {}
        processed_jobs = set()
        
        for i, job in enumerate(jobs_list):
            if i in processed_jobs:
                continue
                
            # Find similar jobs using basic comparison
            similar_jobs = [job]
            similar_indices = {i}
            
            for j, other_job in enumerate(jobs_list[i+1:], i+1):
                if j in processed_jobs:
                    continue
                    
                if self._are_jobs_similar_fast(job, other_job):
                    similar_jobs.append(other_job)
                    similar_indices.add(j)
            
            # Mark all similar jobs as processed
            processed_jobs.update(similar_indices)
            
            # Create job group
            group = self._create_job_group(similar_jobs)
            group_id = f"{group.company}_{group.normalized_title}".replace(" ", "_").lower()
            grouped_jobs[group_id] = group
            
            self.logger.info(f"Created fast group '{group_id}' with {len(similar_jobs)} jobs")
        
        return grouped_jobs
    
    def _are_jobs_similar_fast(self, job1: Dict, job2: Dict) -> bool:
        """
        Fast similarity check without LLM
        """
        # Company similarity (exact match or similar names)
        company1 = job1.get('company', '')
        company2 = job2.get('company', '')
        company1 = company1.strip().lower() if company1 else ''
        company2 = company2.strip().lower() if company2 else ''
        
        if not self._companies_similar_fast(company1, company2):
            return False
        
        # Title similarity using basic keyword matching
        title1 = job1.get('title', '')
        title2 = job2.get('title', '')
        title1 = title1.strip().lower() if title1 else ''
        title2 = title2.strip().lower() if title2 else ''
        
        return self._titles_similar_fast(title1, title2)
    
    def _companies_similar_fast(self, company1: str, company2: str) -> bool:
        """
        Fast company similarity check
        """
        if company1 == company2:
            return True
        
        # Check for common variations
        variations = [
            (company1.replace(' gmbh', ''), company2.replace(' gmbh', '')),
            (company1.replace(' ag', ''), company2.replace(' ag', '')),
            (company1.replace(' ltd', ''), company2.replace(' ltd', '')),
            (company1.replace(' inc', ''), company2.replace(' inc', '')),
        ]
        
        for var1, var2 in variations:
            if var1 == var2 and var1:
                return True
        
        # Check if one is contained in the other (for subsidiaries)
        if company1 in company2 or company2 in company1:
            return True
        
        return False
    
    def _titles_similar_fast(self, title1: str, title2: str) -> bool:
        """
        Fast title similarity check using keyword matching
        """
        if title1 == title2:
            return True
        
        # Extract key words from titles
        words1 = set(title1.split())
        words2 = set(title2.split())
        
        # Check for significant overlap
        common_words = words1.intersection(words2)
        if len(common_words) >= 2:  # At least 2 common words
            return True
        
        # Check for role variations
        role_variations = {
            'developer': ['engineer', 'programmer', 'coder'],
            'engineer': ['developer', 'programmer'],
            'manager': ['lead', 'director', 'head'],
            'lead': ['manager', 'senior'],
            'senior': ['lead', 'principal'],
            'junior': ['entry', 'associate'],
        }
        
        for role, variations in role_variations.items():
            if role in title1 and any(var in title2 for var in variations):
                return True
            if role in title2 and any(var in title1 for var in variations):
                return True
        
        return False
    
    def _create_job_group(self, jobs: List[Dict]) -> JobGroup:
        """
        Create a JobGroup object from a list of similar jobs
        """
        if not jobs:
            raise ValueError("Cannot create job group from empty job list")
        
        # Extract common information
        company = jobs[0].get('company', 'Unknown Company')
        title = jobs[0].get('title', 'Unknown Position')
        
        # Normalize title for grouping
        normalized_title = self._normalize_job_title(title)
        
        # Extract all cities
        cities = []
        for job in jobs:
            location = job.get('location', '')
            if location and location.strip() and location.strip() not in cities:
                cities.append(location.strip())
        
        # Calculate average salary if available
        avg_salary = self._calculate_average_salary(jobs)
        
        return JobGroup(
            company=company,
            title=title,
            normalized_title=normalized_title,
            cities=cities,
            jobs=jobs,
            avg_salary=avg_salary
        )
    
    def _normalize_job_title(self, title: str) -> str:
        """
        Normalize job title for grouping purposes
        """
        if not title or title is None:
            return "unknown"
        
        # Convert to lowercase and remove extra spaces
        normalized = re.sub(r'\s+', ' ', title.lower().strip())
        
        # Remove common prefixes/suffixes that don't affect the core role
        normalized = re.sub(r'\b(junior|senior|lead|principal|staff)\b', '', normalized)
        normalized = re.sub(r'\b(m/f/d|m/w/d|male/female/diverse)\b', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    def _calculate_average_salary(self, jobs: List[Dict]) -> Optional[str]:
        """
        Calculate average salary from job listings
        """
        salaries = []
        
        for job in jobs:
            salary_text = job.get('salary', '')
            if salary_text:
                salary_range = self._extract_salary_range(salary_text)
                if salary_range:
                    salaries.append(salary_range)
        
        if not salaries:
            return None
        
        # Calculate average of salary ranges
        total_min = sum(s[0] for s in salaries)
        total_max = sum(s[1] for s in salaries)
        count = len(salaries)
        
        avg_min = int(total_min / count)
        avg_max = int(total_max / count)
        
        return f"€{avg_min:,} - €{avg_max:,}"
    
    def _extract_salary_range(self, salary_text: str) -> Optional[Tuple[float, float]]:
        """
        Extract salary range from text
        """
        if not salary_text:
            return None
            
        for pattern in self.salary_patterns:
            match = re.search(pattern, salary_text.lower())
            if match:
                try:
                    groups = match.groups()
                    if len(groups) >= 2:
                        min_sal = float(groups[0].replace(',', '').replace('.', ''))
                        max_sal = float(groups[1].replace(',', '').replace('.', ''))
                        
                        # Handle 'k' suffix
                        if 'k' in salary_text.lower():
                            min_sal *= 1000
                            max_sal *= 1000
                            
                        return (min_sal, max_sal)
                    elif len(groups) == 1:
                        sal = float(groups[0].replace(',', '').replace('.', ''))
                        if 'k' in salary_text.lower():
                            sal *= 1000
                        return (sal, sal)
                except ValueError:
                    continue
        
        return None
    
    def get_group_summary(self, job_groups: Dict[str, JobGroup]) -> Dict[str, Any]:
        """
        Get summary statistics for job groups
        """
        if not job_groups:
            return {
                'total_groups': 0,
                'total_jobs': 0,
                'avg_jobs_per_group': 0,
                'top_companies': [],
                'top_cities': []
            }
        
        total_jobs = sum(group.total_positions for group in job_groups.values())
        avg_jobs_per_group = total_jobs / len(job_groups)
        
        # Count companies and cities
        company_counts = defaultdict(int)
        city_counts = defaultdict(int)
        
        for group in job_groups.values():
            company_counts[group.company] += group.total_positions
            for city in group.cities:
                city_counts[city] += group.total_positions
        
        # Get top companies and cities
        top_companies = sorted(company_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        top_cities = sorted(city_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            'total_groups': len(job_groups),
            'total_jobs': total_jobs,
            'avg_jobs_per_group': round(avg_jobs_per_group, 1),
            'top_companies': top_companies,
            'top_cities': top_cities
        } 