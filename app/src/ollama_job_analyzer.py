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
    Ollama-based job analyzer for intelligent job classification, tagging, and CV matching
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
            self.model_name = self.config_manager.get_value('llm.ollama_model', 'llama3:8b')
        
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
    
    def score_job_against_cv(self, job_title: str, job_description: str, cv_text: str, 
                           cv_skills: List[str], company: str = "", salary: str = "") -> Dict[str, Any]:
        """
        Score a job posting against a CV using LLM analysis
        """
        if not self.available:
            return self._fallback_cv_scoring(job_title, job_description, cv_text, cv_skills)
        
        system_prompt = """You are an expert career counselor and recruiter. Analyze how well a candidate's CV matches a job posting.
        Always respond in valid JSON format only, no additional text."""
        
        # Truncate CV text to avoid token limits
        cv_summary = cv_text[:1500] if len(cv_text) > 1500 else cv_text
        
        prompt = f"""
        Analyze how well this candidate matches the job posting and provide a JSON response:
        {{
            "overall_match_score": 0-100,
            "skill_match_score": 0-100,
            "experience_match_score": 0-100,
            "culture_fit_score": 0-100,
            "missing_critical_skills": ["skill1", "skill2"],
            "matching_skills": ["skill1", "skill2"],
            "experience_gap_years": 0-10,
            "strengths": ["strength1", "strength2"],
            "improvement_areas": ["area1", "area2"],
            "recommendation": "Strong Match/Good Match/Partial Match/Poor Match",
            "likelihood_of_interview": "High/Medium/Low",
            "salary_negotiation_position": "Strong/Moderate/Weak",
            "application_priority": "High/Medium/Low",
            "cover_letter_focus": ["point1", "point2", "point3"]
        }}
        
        Job Title: {job_title}
        Company: {company}
        Salary: {salary if salary else "Not specified"}
        Job Description: {job_description[:1500]}
        
        Candidate CV Summary: {cv_summary}
        Candidate Skills: {', '.join(cv_skills[:20])}
        """
        
        response = self._call_ollama(prompt, system_prompt, max_tokens=1000)
        
        if response:
            try:
                analysis = json.loads(response)
                return analysis if analysis else self._fallback_cv_scoring(job_title, job_description, cv_text, cv_skills)
            except json.JSONDecodeError:
                try:
                    start = response.find('{')
                    end = response.rfind('}') + 1
                    if start != -1 and end != 0:
                        json_str = response[start:end]
                        analysis = json.loads(json_str)
                        return analysis if analysis else self._fallback_cv_scoring(job_title, job_description, cv_text, cv_skills)
                except:
                    pass
        
        return self._fallback_cv_scoring(job_title, job_description, cv_text, cv_skills)
    
    def generate_application_insights(self, job_analysis: Dict, cv_scoring: Dict, 
                                    job_title: str, company: str) -> Dict[str, Any]:
        """
        Generate personalized application insights and recommendations
        """
        if not self.available:
            return self._fallback_insights(job_analysis, cv_scoring)
        
        system_prompt = """You are a career coach providing personalized job application advice.
        Always respond in valid JSON format only, no additional text."""
        
        prompt = f"""
        Based on the job analysis and CV scoring, provide application insights in JSON format:
        {{
            "application_strategy": "strategy description",
            "cover_letter_key_points": ["point1", "point2", "point3"],
            "interview_preparation_focus": ["area1", "area2", "area3"],
            "questions_to_ask_interviewer": ["question1", "question2"],
            "salary_negotiation_tips": ["tip1", "tip2"],
            "timeline_recommendation": "Apply immediately/Within 1 week/Within 2 weeks/Skip",
            "networking_opportunities": ["opportunity1", "opportunity2"],
            "skill_development_priorities": ["skill1", "skill2"],
            "confidence_boosters": ["booster1", "booster2"],
            "potential_concerns": ["concern1", "concern2"]
        }}
        
        Job: {job_title} at {company}
        Job Quality Score: {job_analysis.get('overall_quality_score', 'N/A')}
        Match Score: {cv_scoring.get('overall_match_score', 'N/A')}
        Recommendation: {cv_scoring.get('recommendation', 'N/A')}
        Missing Skills: {', '.join(cv_scoring.get('missing_critical_skills', []))}
        Strengths: {', '.join(cv_scoring.get('strengths', []))}
        """
        
        response = self._call_ollama(prompt, system_prompt, max_tokens=800)
        
        if response:
            try:
                insights = json.loads(response)
                return insights if insights else self._fallback_insights(job_analysis, cv_scoring)
            except json.JSONDecodeError:
                try:
                    start = response.find('{')
                    end = response.rfind('}') + 1
                    if start != -1 and end != 0:
                        json_str = response[start:end]
                        insights = json.loads(json_str)
                        return insights if insights else self._fallback_insights(job_analysis, cv_scoring)
                except:
                    pass
        
        return self._fallback_insights(job_analysis, cv_scoring)
    
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
    
    def _fallback_cv_scoring(self, job_title: str, job_description: str, 
                           cv_text: str, cv_skills: List[str]) -> Dict[str, Any]:
        """Fallback CV scoring when LLM is not available"""
        # Simple keyword matching
        desc_lower = job_description.lower()
        cv_lower = cv_text.lower()
        
        matching_skills = [skill for skill in cv_skills if skill.lower() in desc_lower]
        skill_match_percentage = (len(matching_skills) / max(len(cv_skills), 1)) * 100
        
        return {
            'overall_match_score': min(skill_match_percentage, 100),
            'skill_match_score': skill_match_percentage,
            'experience_match_score': 70,  # Default assumption
            'culture_fit_score': 60,
            'missing_critical_skills': [],
            'matching_skills': matching_skills,
            'experience_gap_years': 0,
            'strengths': ['Relevant skills'],
            'improvement_areas': ['Skill development'],
            'recommendation': 'Good Match' if skill_match_percentage > 50 else 'Partial Match',
            'likelihood_of_interview': 'Medium',
            'salary_negotiation_position': 'Moderate',
            'application_priority': 'Medium',
            'cover_letter_focus': ['Highlight relevant experience']
        }
    
    def _fallback_insights(self, job_analysis: Dict, cv_scoring: Dict) -> Dict[str, Any]:
        """Fallback insights when LLM is not available"""
        return {
            'application_strategy': 'Focus on highlighting relevant skills and experience',
            'cover_letter_key_points': ['Match your skills to job requirements', 'Show enthusiasm for the role'],
            'interview_preparation_focus': ['Technical skills', 'Company research'],
            'questions_to_ask_interviewer': ['What does success look like in this role?'],
            'salary_negotiation_tips': ['Research market rates', 'Highlight unique value'],
            'timeline_recommendation': 'Within 1 week',
            'networking_opportunities': ['LinkedIn connections', 'Industry events'],
            'skill_development_priorities': ['Core technical skills'],
            'confidence_boosters': ['Relevant experience', 'Transferable skills'],
            'potential_concerns': ['Competition', 'Skill gaps']
        }
    
    def batch_analyze_jobs(self, jobs: List[Dict], cv_text: str = "", cv_skills: List[str] = None) -> List[Dict]:
        """
        Analyze multiple jobs in batch for efficiency
        """
        if cv_skills is None:
            cv_skills = []
            
        analyzed_jobs = []
        
        for job in jobs:
            try:
                # Basic job analysis
                job_analysis = self.analyze_job_posting(
                    job.get('title', ''),
                    job.get('description', ''),
                    job.get('company', '')
                )
                
                # CV scoring if CV is provided
                cv_scoring = {}
                if cv_text:
                    cv_scoring = self.score_job_against_cv(
                        job.get('title', ''),
                        job.get('description', ''),
                        cv_text,
                        cv_skills,
                        job.get('company', '')
                    )
                
                # Combine original job data with analysis
                analyzed_job = {
                    **job,
                    'llm_analysis': job_analysis,
                    'cv_scoring': cv_scoring,
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
                    'cv_scoring': {},
                    'analysis_error': str(e)
                })
        
        return analyzed_jobs 

    def batch_analyze_jobs_optimized(self, jobs: List[Dict], cv_text: str = "", cv_skills: List[str] = None, 
                                    max_workers: int = 4, skip_analysis: bool = False) -> List[Dict]:
        """
        Optimized batch job analysis with parallel processing and optional skipping
        """
        if cv_skills is None:
            cv_skills = []
            
        if skip_analysis:
            # Skip analysis for speed - just add basic metadata
            analyzed_jobs = []
            for job in jobs:
                analyzed_job = {
                    **job,
                    'llm_analysis': self._fallback_analysis(job.get('title', ''), job.get('description', '')),
                    'cv_scoring': {},
                    'analysis_skipped': True,
                    'analysis_timestamp': datetime.now().isoformat()
                }
                analyzed_jobs.append(analyzed_job)
            return analyzed_jobs
            
        analyzed_jobs = []
        
        # Process jobs in parallel for better performance
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_job = {
                executor.submit(self._analyze_single_job, job, cv_text, cv_skills): job 
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
                        'cv_scoring': {},
                        'analysis_error': str(e),
                        'analysis_timestamp': datetime.now().isoformat()
                    })
        
        return analyzed_jobs
    
    def _analyze_single_job(self, job: Dict, cv_text: str, cv_skills: List[str]) -> Dict:
        """Analyze a single job with error handling"""
        try:
            # Basic job analysis
            job_analysis = self.analyze_job_posting(
                job.get('title', ''),
                job.get('description', ''),
                job.get('company', '')
            )
            
            # CV scoring if CV is provided
            cv_scoring = {}
            if cv_text:
                cv_scoring = self.score_job_against_cv(
                    job.get('title', ''),
                    job.get('description', ''),
                    cv_text,
                    cv_skills,
                    job.get('company', '')
                )
            
            # Combine original job data with analysis
            analyzed_job = {
                **job,
                'llm_analysis': job_analysis,
                'cv_scoring': cv_scoring,
                'analysis_timestamp': datetime.now().isoformat()
            }
            
            return analyzed_job
            
        except Exception as e:
            self.logger.error(f"Error in single job analysis: {e}")
            # Return job with fallback analysis
            return {
                **job,
                'llm_analysis': self._fallback_analysis(job.get('title', ''), job.get('description', '')),
                'cv_scoring': {},
                'analysis_error': str(e),
                'analysis_timestamp': datetime.now().isoformat()
            }
    
    def analyze_jobs_async(self, jobs: List[Dict], cv_text: str = "", cv_skills: List[str] = None) -> List[Dict]:
        """
        Asynchronous job analysis that can be run separately from search
        """
        if not self.available:
            self.logger.warning("LLM not available, using fallback analysis")
            return self.batch_analyze_jobs_optimized(jobs, cv_text, cv_skills, skip_analysis=True)
        
        return self.batch_analyze_jobs_optimized(jobs, cv_text, cv_skills, max_workers=4) 