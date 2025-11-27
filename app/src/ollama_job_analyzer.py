import requests
import json
from typing import Dict, List, Optional, Any
import time
from datetime import datetime
import logging
import os
import sys
sys.path.append('/app/src')
from config_manager import get_config_manager
from concurrent.futures import ThreadPoolExecutor, as_completed

class OllamaJobAnalyzer:
    """
    Ollama-based job analyzer for intelligent job classification and tagging
    """
    
    def __init__(self, ollama_host: str = None, model_name: str = None):
        # Get configuration
        self.config_manager = get_config_manager()
        
        # Use provided host or get from environment/config
        if ollama_host:
            self.ollama_host = ollama_host.rstrip('/')
        else:
            # Try environment variable first, then config
            env_host = os.getenv('OLLAMA_HOST')
            if env_host:
                self.ollama_host = env_host.rstrip('/')
            else:
                self.ollama_host = self.config_manager.get_value('llm.ollama_host', 'http://localhost:11434').rstrip('/')
        
        # Use provided model or get from config
        if model_name:
            self.model_name = model_name
        else:
            self.model_name = self.config_manager.get_value('llm.ollama_model', 'gemma3:1b')
        
        self.logger = logging.getLogger(__name__)
        
        # Test connection
        if not self.test_connection():
            self.logger.warning("Could not connect to Ollama. LLM features will be disabled.")
            self.available = False
        else:
            self.available = True
            
    def test_connection(self) -> bool:
        """Test connection to Ollama server"""
        try:
            response = requests.get(f"{self.ollama_host}/api/tags", timeout=10)
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Ollama connection test failed: {e}")
            return False
    
    def _call_ollama(self, prompt: str, system_prompt: str = "", max_tokens: int = 500) -> Optional[str]:
        """Make a call to Ollama API with retry logic"""
        if not self.available:
            return None
            
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                payload = {
                    "model": self.model_name,
                    "prompt": prompt,
                    "system": system_prompt,
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": 0.1  # Lower temperature for more consistent results
                    }
                }
                
                response = requests.post(
                    f"{self.ollama_host}/api/generate",
                    json=payload,
                    timeout=self.config_manager.get_value('llm.ollama_timeout', 300)  # Use config timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get('response', '').strip()
                else:
                    self.logger.error(f"Ollama API error: {response.status_code}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    return None
                    
            except requests.exceptions.Timeout:
                self.logger.warning(f"Ollama request timed out (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    self.logger.error("All Ollama requests timed out")
                    return None
            except Exception as e:
                self.logger.error(f"Error calling Ollama (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return None
        
        return None
    
    def analyze_job_posting(self, job_title: str, job_description: str, company: str = "", salary: str = "") -> Dict[str, Any]:
        """
        Analyze a job posting to extract key information and generate tags
        """
        if not self.available:
            return self._fallback_analysis(job_title, job_description)
        
        system_prompt = """You are an expert job market analyst. Analyze job postings and provide structured insights.
        Always respond in valid JSON format only, no additional text."""
        
        prompt = f"""
        Analyze this job posting and provide a JSON response with the following structure:
        {{
            "job_category": "primary category (e.g., Software Development, Data Science, DevOps, etc.)",
            "experience_level": "Junior/Mid/Senior/Lead/Executive",
            "required_skills": ["skill1", "skill2", "skill3"],
            "preferred_skills": ["skill1", "skill2"],
            "tech_stack": ["technology1", "technology2"],
            "remote_friendly": true/false,
            "salary_range_mentioned": true/false,
            "urgency_level": "Low/Medium/High",
            "company_size_estimate": "Startup/Small/Medium/Large/Enterprise",
            "key_responsibilities": ["responsibility1", "responsibility2"],
            "red_flags": ["flag1", "flag2"] or [],
            "positive_indicators": ["indicator1", "indicator2"],
            "overall_quality_score": 0-10,
            "tags": ["tag1", "tag2", "tag3"]
        }}
        
        Job Title: {job_title}
        Company: {company}
        Salary: {salary if salary else "Not specified"}
        Job Description: {job_description[:2000]}
        """
        
        response = self._call_ollama(prompt, system_prompt, max_tokens=800)
        
        if response:
            try:
                # Try to parse JSON response
                analysis = json.loads(response)
                return analysis if analysis else self._fallback_analysis(job_title, job_description)
            except json.JSONDecodeError:
                # If JSON parsing fails, try to extract JSON from response
                try:
                    # Look for JSON block in response
                    start = response.find('{')
                    end = response.rfind('}') + 1
                    if start != -1 and end != 0:
                        json_str = response[start:end]
                        analysis = json.loads(json_str)
                        return analysis if analysis else self._fallback_analysis(job_title, job_description)
                except:
                    pass
        
        # Fallback to rule-based analysis
        return self._fallback_analysis(job_title, job_description)
    

    

    
    def _fallback_analysis(self, job_title: str, job_description: str) -> Dict[str, Any]:
        """Fallback rule-based job analysis when LLM is not available"""
        title_lower = job_title.lower()
        desc_lower = job_description.lower()
        
        # Simple category detection
        categories = {
            'Software Development': ['developer', 'programmer', 'software', 'engineer', 'coding'],
            'Data Science': ['data scientist', 'machine learning', 'ai', 'analytics'],
            'DevOps': ['devops', 'infrastructure', 'cloud', 'deployment'],
            'Management': ['manager', 'lead', 'director', 'head'],
            'Design': ['designer', 'ui', 'ux', 'creative'],
        }
        
        job_category = 'Other'
        for category, keywords in categories.items():
            if any(keyword in title_lower or keyword in desc_lower for keyword in keywords):
                job_category = category
                break
        
        # Experience level detection
        experience_level = 'Mid'
        if any(word in title_lower for word in ['senior', 'sr', 'lead', 'principal']):
            experience_level = 'Senior'
        elif any(word in title_lower for word in ['junior', 'jr', 'entry', 'intern']):
            experience_level = 'Junior'
        
        return {
            'job_category': job_category,
            'experience_level': experience_level,
            'required_skills': [],
            'preferred_skills': [],
            'tech_stack': [],
            'remote_friendly': 'remote' in desc_lower,
            'salary_range_mentioned': any(word in desc_lower for word in ['salary', '$', '€', 'compensation']),
            'urgency_level': 'Medium',
            'company_size_estimate': 'Medium',
            'key_responsibilities': [],
            'red_flags': [],
            'positive_indicators': [],
            'overall_quality_score': 5,
            'tags': [job_category.lower().replace(' ', '_')]
        }
    

    

    
    def batch_analyze_jobs(self, jobs: List[Dict]) -> List[Dict]:
        """
        Analyze multiple jobs in batch for efficiency
        """
        analyzed_jobs = []
        
        for job in jobs:
            try:
                # Basic job analysis
                job_analysis = self.analyze_job_posting(
                    job.get('title', ''),
                    job.get('description', ''),
                    job.get('company', '')
                )
                
                # Combine original job data with analysis
                analyzed_job = {
                    **job,
                    'llm_analysis': job_analysis,
                    'analysis_timestamp': datetime.now().isoformat()
                }
                
                analyzed_jobs.append(analyzed_job)
                
                # Small delay to avoid overwhelming the LLM
                time.sleep(0.5)
                
            except Exception as e:
                self.logger.error(f"Error analyzing job {job.get('title', 'Unknown')}: {e}")
                # Include job with error info
                analyzed_jobs.append({
                    **job,
                    'llm_analysis': self._fallback_analysis(job.get('title', ''), job.get('description', '')),
                    'analysis_error': str(e)
                })
        
        return analyzed_jobs 

    def batch_analyze_jobs_optimized(self, jobs: List[Dict], max_workers: int = 4, skip_analysis: bool = False) -> List[Dict]:
        """
        Optimized batch job analysis with parallel processing and optional skipping
        """
        if skip_analysis:
            # Skip analysis for speed - just add basic metadata
            analyzed_jobs = []
            for job in jobs:
                analyzed_job = {
                    **job,
                    'llm_analysis': self._fallback_analysis(job.get('title', ''), job.get('description', '')),
                    'analysis_skipped': True,
                    'analysis_timestamp': datetime.now().isoformat()
                }
                analyzed_jobs.append(analyzed_job)
            return analyzed_jobs
            
        analyzed_jobs = []
        
        # Process jobs in parallel for better performance
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_job = {
                executor.submit(self._analyze_single_job, job): job 
                for job in jobs
            }
            
            for future in as_completed(future_to_job):
                try:
                    analyzed_job = future.result(timeout=self.config_manager.get_value('llm.ollama_timeout', 300))  # Use config timeout
                    analyzed_jobs.append(analyzed_job)
                except Exception as e:
                    original_job = future_to_job[future]
                    self.logger.error(f"Error analyzing job {original_job.get('title', 'Unknown')}: {e}")
                    # Add job with fallback analysis
                    analyzed_jobs.append({
                        **original_job,
                        'llm_analysis': self._fallback_analysis(original_job.get('title', ''), original_job.get('description', '')),
                        'analysis_error': str(e),
                        'analysis_timestamp': datetime.now().isoformat()
                    })
        
        return analyzed_jobs
    
    def _analyze_single_job(self, job: Dict) -> Dict:
        """Analyze a single job with error handling"""
        try:
            # Basic job analysis
            job_analysis = self.analyze_job_posting(
                job.get('title', ''),
                job.get('description', ''),
                job.get('company', '')
            )
            
            # Combine original job data with analysis
            analyzed_job = {
                **job,
                'llm_analysis': job_analysis,
                'analysis_timestamp': datetime.now().isoformat()
            }
            
            return analyzed_job
            
        except Exception as e:
            self.logger.error(f"Error in single job analysis: {e}")
            # Return job with fallback analysis
            return {
                **job,
                'llm_analysis': self._fallback_analysis(job.get('title', ''), job.get('description', '')),
                'analysis_error': str(e),
                'analysis_timestamp': datetime.now().isoformat()
            }
    
    def analyze_jobs_async(self, jobs: List[Dict]) -> List[Dict]:
        """
        Asynchronous job analysis that can be run separately from search
        """
        if not self.available:
            self.logger.warning("LLM not available, using fallback analysis")
            return self.batch_analyze_jobs_optimized(jobs, skip_analysis=True)
        
        return self.batch_analyze_jobs_optimized(jobs, max_workers=4) 