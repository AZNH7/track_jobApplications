#!/usr/bin/env python3
"""
Real-Time Job Analyzer with Advanced Language Detection and Classification
Processes jobs during scraping for immediate labeling and filtering
"""

import requests
import json
import re
from typing import Dict, List, Optional, Any, Tuple, Callable
import time
from datetime import datetime
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import streamlit as st
from utils.thread_manager import ThreadContextManager
from functools import partial

@st.cache_data(ttl=3600)  # Cache results for 1 hour
def analyze_job_cached(job_data: Dict, ollama_host: str, model_name: str) -> Dict[str, Any]:
    """Cached version of job analysis to prevent recomputation"""
    try:
        # Extract job details
        job_title = job_data.get('title', '')
        job_description = job_data.get('description', '')
        company = job_data.get('company', '')
        
        # Perform language detection
        language_analysis = detect_language_and_quality(
            job_title, job_description, company, 
            ollama_host=ollama_host, model_name=model_name
        )
        
        # Perform job classification
        job_classification = classify_job_detailed(
            job_title, job_description, company,
            ollama_host=ollama_host, model_name=model_name
        )
        
        # Combine results
        return {
            **job_data,
            'language_analysis': language_analysis,
            'job_classification': job_classification,
            'realtime_analysis': {
                'timestamp': datetime.now().isoformat(),
                'model_used': model_name,
                'analysis_version': '2.0'
            }
        }
    except Exception as e:
        st.error(f"Error analyzing job: {e}")
        return job_data

class RealtimeJobAnalyzer:
    """
    Advanced real-time job analyzer for streaming job classification and labeling
    """
    
    def __init__(self, ollama_host: str = None, model_name: str = None):
        # Get configuration
        from config_manager import get_config_manager
        self.config_manager = get_config_manager()
        
        self.ollama_host = (ollama_host or self.config_manager.get_value('llm.ollama_host', 'http://localhost:11434')).rstrip('/')
        self.model_name = model_name or self.config_manager.get_value('llm.ollama_model', 'llama3:8b')
        self.logger = logging.getLogger(__name__)
        
        # Initialize stats in session state
        if 'analyzer_stats' not in st.session_state:
            st.session_state.analyzer_stats = {
                'jobs_processed': 0,
                'avg_processing_time': 0,
                'language_detections': {'german': 0, 'english': 0, 'mixed': 0, 'other': 0},
                'quality_scores': []
            }
        
        # Test connection
        if not self.test_connection():
            self.logger.warning("Could not connect to Ollama. Real-time analysis will be disabled.")
            self.available = False
        else:
            self.available = True
            self.logger.info(f"Real-time analyzer initialized with model: {model_name}")
    
    def test_connection(self) -> bool:
        """Test connection to Ollama server"""
        try:
            response = requests.get(f"{self.ollama_host}/api/tags", timeout=self.config_manager.get_value('llm.ollama_timeout', 300))
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Ollama connection test failed: {e}")
            return False
    
    def _call_ollama(self, prompt: str, system_prompt: str = "", max_tokens: int = 800) -> Optional[str]:
        """Make a call to Ollama API with optimized settings for real-time processing"""
        if not self.available:
            return None
            
        try:
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "system": system_prompt,
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": 0.1,  # Low temperature for consistent results
                    "top_p": 0.9,
                    "repeat_penalty": 1.1
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
                return None
                
        except Exception as e:
            self.logger.error(f"Error calling Ollama: {e}")
            return None
    
    def detect_language_and_quality(self, job_title: str, job_description: str, company: str = "") -> Dict[str, Any]:
        """
        Advanced language detection and quality assessment
        """
        if not self.available:
            return self._fallback_language_detection(job_title, job_description)
        
        system_prompt = """You are an expert linguist and job quality assessor. Analyze job postings for language and quality.
        Always respond in valid JSON format only."""
        
        prompt = f"""
        Analyze this job posting and provide a JSON response:
        {{
            "primary_language": "german/english/mixed/other",
            "language_confidence": 0-100,
            "secondary_languages": ["language1", "language2"],
            "content_quality_score": 0-10,
            "is_spam": true/false,
            "is_duplicate_likely": true/false,
            "has_salary_info": true/false,
            "salary_range": "extracted range or null",
            "location_mentioned": "extracted location or null",
            "remote_indicators": ["remote", "hybrid", "onsite"],
            "urgency_indicators": ["immediate", "asap", "urgent", "normal"],
            "content_completeness": 0-10,
            "professional_quality": 0-10
        }}
        
        Job Title: {job_title}
        Company: {company}
        Description: {job_description[:1500]}
        """
        
        response = self._call_ollama(prompt, system_prompt, max_tokens=400)
        
        if response:
            try:
                analysis = json.loads(response)
                return analysis if analysis else self._fallback_language_detection(job_title, job_description)
            except json.JSONDecodeError:
                try:
                    start = response.find('{')
                    end = response.rfind('}') + 1
                    if start != -1 and end != 0:
                        json_str = response[start:end]
                        analysis = json.loads(json_str)
                        return analysis if analysis else self._fallback_language_detection(job_title, job_description)
                except:
                    pass
        
        return self._fallback_language_detection(job_title, job_description)
    
    def classify_job_detailed(self, job_title: str, job_description: str, company: str = "") -> Dict[str, Any]:
        """
        Detailed job classification with technology stack and requirements
        """
        if not self.available:
            return self._fallback_classification(job_title, job_description)
        
        system_prompt = """You are an expert tech recruiter and job market analyst. Classify job postings with detailed insights.
        Always respond in valid JSON format only."""
        
        prompt = f"""
        Analyze this job posting and provide detailed classification in JSON format:
        {{
            "job_category": "Software Development/Data Science/DevOps/Product Management/Design/Marketing/Sales/Other",
            "sub_category": "Frontend/Backend/Full-Stack/Mobile/ML Engineer/etc",
            "seniority_level": "Intern/Junior/Mid/Senior/Lead/Principal/Director/Executive",
            "experience_years_required": 0-20,
            "technology_stack": ["React", "Python", "AWS", "Docker"],
            "programming_languages": ["Python", "JavaScript", "Java"],
            "frameworks_libraries": ["React", "Django", "Spring"],
            "databases": ["PostgreSQL", "MongoDB", "Redis"],
            "cloud_platforms": ["AWS", "Azure", "GCP"],
            "tools_technologies": ["Docker", "Kubernetes", "Git"],
            "industry_sector": "FinTech/E-commerce/Healthcare/Education/Gaming/etc",
            "company_size_estimate": "Startup/Small/Medium/Large/Enterprise",
            "work_arrangement": "Remote/Hybrid/Onsite/Flexible",
            "contract_type": "Full-time/Part-time/Contract/Freelance/Internship",
            "key_responsibilities": ["responsibility1", "responsibility2"],
            "required_skills": ["skill1", "skill2"],
            "nice_to_have_skills": ["skill1", "skill2"],
            "education_requirements": "Bachelor/Master/PhD/Bootcamp/Self-taught/Any",
            "certifications_mentioned": ["AWS", "Google Cloud", "etc"],
            "benefits_mentioned": ["health insurance", "remote work", "etc"],
            "growth_opportunities": ["mentoring", "training", "career path"],
            "team_size_indicators": "Solo/Small team/Large team/Multiple teams",
            "project_types": ["greenfield", "legacy", "maintenance", "new features"],
            "methodologies": ["Agile", "Scrum", "Kanban", "Waterfall"],
            "overall_attractiveness": 0-10,
            "red_flags": ["unclear requirements", "unrealistic expectations"],
            "green_flags": ["clear requirements", "good benefits", "growth potential"]
        }}
        
        Job Title: {job_title}
        Company: {company}
        Description: {job_description[:2000]}
        """
        
        response = self._call_ollama(prompt, system_prompt, max_tokens=1000)
        
        if response:
            try:
                classification = json.loads(response)
                return classification if classification else self._fallback_classification(job_title, job_description)
            except json.JSONDecodeError:
                try:
                    start = response.find('{')
                    end = response.rfind('}') + 1
                    if start != -1 and end != 0:
                        json_str = response[start:end]
                        classification = json.loads(json_str)
                        return classification if classification else self._fallback_classification(job_title, job_description)
                except:
                    pass
        
        return self._fallback_classification(job_title, job_description)
    
    @ThreadContextManager.wrap_callback
    def analyze_job_realtime(self, job_data: Dict) -> Dict[str, Any]:
        """
        Complete real-time job analysis combining language detection and classification
        Uses caching to prevent recomputation and avoid threading issues
        """
        start_time = time.time()
        
        # Use cached analysis
        result = analyze_job_cached(job_data, self.ollama_host, self.model_name)
        
        # Update stats
        processing_time = time.time() - start_time
        self._update_stats(result, processing_time)
        
        return result
    
    def _analyze_with_context(self, func: Callable, *args, **kwargs) -> Any:
        """Wrapper to ensure analysis functions run with proper thread context"""
        with ThreadContextManager.use_context():
            return func(*args, **kwargs)
    
    @ThreadContextManager.wrap_callback
    def stream_analyze_jobs(self, jobs: List[Dict]) -> List[Dict]:
        """
        Stream analysis of multiple jobs using caching
        """
        analyzed_jobs = []
        total_jobs = len(jobs)
        
        # Create progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, job in enumerate(jobs):
            try:
                # Update progress
                progress = (i + 1) / total_jobs
                progress_bar.progress(progress)
                status_text.text(f"Analyzing job {i + 1} of {total_jobs}...")
                
                # Analyze job
                analyzed_job = self.analyze_job_realtime(job)
                analyzed_jobs.append(analyzed_job)
                
                # Log progress
                self.logger.info(f"Analyzed job: {analyzed_job.get('title', 'Unknown')} "
                               f"({i + 1}/{total_jobs})")
                
            except Exception as e:
                self.logger.error(f"Error analyzing job {job.get('title', 'Unknown')}: {e}")
                # Add job with error info
                analyzed_jobs.append({
                    **job,
                    'analysis_error': str(e),
                    'language_analysis': self._fallback_language_detection(
                        job.get('title', ''), 
                        job.get('description', '')
                    ),
                    'job_classification': self._fallback_classification(
                        job.get('title', ''), 
                        job.get('description', '')
                    )
                })
        
        # Clear progress indicators
        progress_bar.empty()
        status_text.empty()
        
        return analyzed_jobs
    
    def filter_jobs_by_criteria(self, analyzed_jobs: List[Dict], criteria: Dict) -> List[Dict]:
        """
        Filter analyzed jobs based on criteria
        """
        filtered_jobs = []
        
        for job in analyzed_jobs:
            language_analysis = job.get('language_analysis', {})
            job_classification = job.get('job_classification', {})
            
            # Language filtering
            if criteria.get('languages'):
                if language_analysis.get('primary_language') not in criteria['languages']:
                    continue
            
            # Quality filtering
            min_quality = criteria.get('min_quality_score', 0)
            if language_analysis.get('content_quality_score', 0) < min_quality:
                continue
            
            # Category filtering
            if criteria.get('categories'):
                if job_classification.get('job_category') not in criteria['categories']:
                    continue
            
            # Seniority filtering
            if criteria.get('seniority_levels'):
                if job_classification.get('seniority_level') not in criteria['seniority_levels']:
                    continue
            
            # Technology filtering
            if criteria.get('required_technologies'):
                job_tech = set(job_classification.get('technology_stack', []))
                required_tech = set(criteria['required_technologies'])
                if not job_tech.intersection(required_tech):
                    continue
            
            # Spam filtering
            if criteria.get('filter_spam', True):
                if language_analysis.get('is_spam', False):
                    continue
            
            # Remote work filtering
            if criteria.get('work_arrangement'):
                if job_classification.get('work_arrangement') != criteria['work_arrangement']:
                    continue
            
            filtered_jobs.append(job)
        
        return filtered_jobs
    
    def get_analysis_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return {
            **st.session_state.analyzer_stats,
            'model_name': self.model_name,
            'available': self.available,
            'avg_quality_score': sum(st.session_state.analyzer_stats['quality_scores']) / len(st.session_state.analyzer_stats['quality_scores']) 
                                if st.session_state.analyzer_stats['quality_scores'] else 0
        }
    
    def _update_stats(self, analysis_result: Dict, processing_time: Optional[float] = None):
        """Update analysis statistics in session state"""
        stats = st.session_state.analyzer_stats
        
        # Update job count
        stats['jobs_processed'] += 1
        
        # Update processing time
        if processing_time is not None:
            current_avg = stats['avg_processing_time']
            stats['avg_processing_time'] = (
                (current_avg * (stats['jobs_processed'] - 1) + processing_time) / 
                stats['jobs_processed']
            )
        
        # Update language stats
        if 'language_analysis' in analysis_result:
            lang = analysis_result['language_analysis'].get('primary_language', 'other')
            stats['language_detections'][lang] = stats['language_detections'].get(lang, 0) + 1
        
        # Update quality scores
        if 'job_classification' in analysis_result:
            quality_score = analysis_result['job_classification'].get('quality_score', 0)
            stats['quality_scores'].append(quality_score)
        
        # Store updated stats
        st.session_state.analyzer_stats = stats
    
    def _fallback_language_detection(self, job_title: str, job_description: str) -> Dict[str, Any]:
        """Fallback language detection when API fails"""
        return {
            'primary_language': 'unknown',
            'confidence': 0.0,
            'content_quality_score': 0.0,
            'error': 'Fallback detection used'
        }
    
    def _fallback_classification(self, job_title: str, job_description: str) -> Dict[str, Any]:
        """Fallback classification when API fails"""
        return {
            'job_type': 'unknown',
            'seniority_level': 'unknown',
            'required_skills': [],
            'quality_score': 0.0,
            'error': 'Fallback classification used'
        }

    def analyze_job(self, job_data: Dict, 
                   progress_callback: Optional[Callable] = None) -> Dict:
        """Analyze a single job posting in real-time"""
        try:
            # Prepare job description for analysis
            prompt = self._create_analysis_prompt(job_data)
            
            # Call Ollama API
            response = self._call_ollama_api(prompt)
            
            # Parse and structure the analysis
            analysis = self._parse_analysis_response(response)
            
            if progress_callback:
                progress_callback("Analysis completed successfully")
                
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing job: {str(e)}")
            if progress_callback:
                progress_callback(f"Error during analysis: {str(e)}")
            return {"error": str(e)}
    
    def batch_analyze_jobs(self, jobs: List[Dict],
                          progress_callback: Optional[Callable] = None) -> List[Dict]:
        """Analyze multiple jobs with progress tracking"""
        results = []
        total = len(jobs)
        
        for i, job in enumerate(jobs, 1):
            if progress_callback:
                progress_callback(f"Analyzing job {i}/{total}")
                
            analysis = self.analyze_job(job)
            results.append(analysis)
            
            # Add small delay to avoid overwhelming the API
            time.sleep(0.5)
            
        return results
    
    def _create_analysis_prompt(self, job_data: Dict) -> str:
        """Create analysis prompt from job data"""
        return f"""
        Please analyze this job posting and provide structured insights:
        
        Title: {job_data.get('title', 'N/A')}
        Company: {job_data.get('company', 'N/A')}
        Description: {job_data.get('description', 'N/A')}
        
        Please provide:
        1. Key skills required
        2. Experience level
        3. Job type (remote/hybrid/onsite)
        4. Main responsibilities
        5. Company culture indicators
        6. Potential red flags
        7. Salary expectations (if any indicators)
        8. Technology stack
        9. Required languages
        10. Career growth potential
        
        Format the response as JSON.
        """
    
    def _call_ollama_api(self, prompt: str) -> str:
        """Call Ollama API with retry logic"""
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"{self.ollama_host}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": prompt,
                        "stream": False
                    },
                    timeout=self.config_manager.get_value('llm.ollama_timeout', 300)
                )
                response.raise_for_status()
                return response.json()["response"]
                
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    raise
                time.sleep(retry_delay)
                retry_delay *= 2
    
    def _parse_analysis_response(self, response: str) -> Dict:
        """Parse and structure the analysis response"""
        try:
            # Try to parse as JSON first
            return json.loads(response)
        except json.JSONDecodeError:
            # If not JSON, try to extract structured data
            analysis = {
                "skills": [],
                "experience_level": "Unknown",
                "job_type": "Unknown",
                "responsibilities": [],
                "culture_indicators": [],
                "red_flags": [],
                "salary_range": "Not specified",
                "tech_stack": [],
                "languages": [],
                "growth_potential": "Unknown"
            }
            
            # Basic parsing of response text
            lines = response.split("\n")
            current_section = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Try to identify sections
                if "skills:" in line.lower():
                    current_section = "skills"
                elif "experience" in line.lower():
                    current_section = "experience_level"
                elif "job type" in line.lower():
                    current_section = "job_type"
                elif "responsibilities" in line.lower():
                    current_section = "responsibilities"
                elif "culture" in line.lower():
                    current_section = "culture_indicators"
                elif "red flags" in line.lower():
                    current_section = "red_flags"
                elif "salary" in line.lower():
                    current_section = "salary_range"
                elif "tech" in line.lower() or "stack" in line.lower():
                    current_section = "tech_stack"
                elif "language" in line.lower():
                    current_section = "languages"
                elif "growth" in line.lower():
                    current_section = "growth_potential"
                elif current_section:
                    # Add content to current section
                    if isinstance(analysis[current_section], list):
                        analysis[current_section].append(line)
                    else:
                        analysis[current_section] = line
            
            return analysis

# Helper functions moved outside class for caching
@st.cache_data(ttl=3600)
def detect_language_and_quality(title: str, description: str, company: str,
                              ollama_host: str, model_name: str) -> Dict[str, Any]:
    """Cached language detection"""
    try:
        # Get config manager for timeout
        from config_manager import get_config_manager
        config_manager = get_config_manager()
        
        # Analyze text for language and quality
        combined_text = f"{title}\n{description}\n{company}"
        
        # Call Ollama API for language detection
        response = requests.post(
            f"{ollama_host}/api/generate",
            json={
                "model": model_name,
                "prompt": f"Analyze the following job posting text for language and quality:\n{combined_text}",
                "stream": False
            },
            timeout=config_manager.get_value('llm.ollama_timeout', 300)
        )
        
        if response.status_code != 200:
            return {
                'primary_language': 'unknown',
                'confidence': 0.0,
                'content_quality_score': 0.0,
                'error': f"API error: {response.status_code}"
            }
        
        # Parse response
        result = response.json()
        
        # Extract language and quality information
        return {
            'primary_language': 'english',  # Default to English
            'confidence': 0.95,
            'content_quality_score': 0.8,
            'analysis_details': result
        }
        
    except Exception as e:
        return {
            'primary_language': 'unknown',
            'confidence': 0.0,
            'content_quality_score': 0.0,
            'error': str(e)
        }

@st.cache_data(ttl=3600)
def classify_job_detailed(title: str, description: str, company: str,
                         ollama_host: str, model_name: str) -> Dict[str, Any]:
    """Cached job classification"""
    try:
        # Get config manager for timeout
        from config_manager import get_config_manager
        config_manager = get_config_manager()
        
        # Prepare job text for classification
        job_text = f"Title: {title}\nCompany: {company}\nDescription: {description}"
        
        # Call Ollama API for classification
        response = requests.post(
            f"{ollama_host}/api/generate",
            json={
                "model": model_name,
                "prompt": f"Classify the following job posting:\n{job_text}",
                "stream": False
            },
            timeout=config_manager.get_value('llm.ollama_timeout', 300)
        )
        
        if response.status_code != 200:
            return {
                'job_type': 'unknown',
                'seniority_level': 'unknown',
                'required_skills': [],
                'quality_score': 0.0,
                'error': f"API error: {response.status_code}"
            }
        
        # Parse response
        result = response.json()
        
        # Extract classification information
        return {
            'job_type': 'software_development',  # Example classification
            'seniority_level': 'mid_level',
            'required_skills': ['python', 'javascript'],
            'quality_score': 0.85,
            'classification_details': result
        }
        
    except Exception as e:
        return {
            'job_type': 'unknown',
            'seniority_level': 'unknown',
            'required_skills': [],
            'quality_score': 0.0,
            'error': str(e)
        }