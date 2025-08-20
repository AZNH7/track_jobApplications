#!/usr/bin/env python3
"""
Enhanced Job Processor
Processes all searched jobs through LLM for complete analysis
"""

import requests
import json
import os
from typing import Dict, List, Optional, Any, Union, Callable
import time
from datetime import datetime
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import PyPDF2
import pdfplumber
from pathlib import Path
from utils.thread_manager import ThreadContextManager

class EnhancedJobProcessor:
    """
    Comprehensive job processor that automatically analyzes all jobs with:
    - Language detection and confidence
    - Location extraction from job descriptions
    
    - Technology stack analysis
    - Automatic job ranking
    """
    
    def __init__(self, ollama_host: str = "", ollama_model: str = ""):
        """Initialize the enhanced job processor"""
        self.logger = logging.getLogger(__name__)
        # Get configuration
        from config_manager import get_config_manager
        self.config_manager = get_config_manager()
        
        self.ollama_host = ollama_host or self.config_manager.get_value('llm.ollama_host', 'http://localhost:11434')
        self.ollama_model = ollama_model or self.config_manager.get_value('llm.ollama_model', 'llama3:8b')
        self.available = False
        
        # Thread management
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.processing_lock = threading.Lock()
        
        # Stats tracking
        self.stats: Dict[str, Any] = {
            'jobs_processed': 0,
            'processing_time': 0,
            'errors': 0,

            'high_quality_jobs': 0,
            'language_breakdown': {},
            'location_breakdown': {}
        }
        

        
        # Test Ollama availability
        self._test_ollama_connection()
    
    def _test_ollama_connection(self):
        """Test connection to Ollama server"""
        try:
            response = requests.get(f"{self.ollama_host}/api/tags", timeout=10)
            if response.status_code == 200:
                self.available = True
                self.logger.info(f"Enhanced job processor initialized with model: {self.ollama_model}")
            else:
                self.logger.warning("Could not connect to Ollama. Job processing will be disabled.")
        except Exception as e:
            self.logger.error(f"Ollama connection test failed: {e}")
    def _call_ollama(self, prompt: str, system_prompt: str = "", max_tokens: int = 1000) -> Optional[str]:
        """Make a call to Ollama API"""
        if not self.available:
            return None
            
        try:
            payload = {
                "model": self.ollama_model,
                "prompt": prompt,
                "system": system_prompt,
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "repeat_penalty": 1.1
                }
            }
            
            response = requests.post(
                f"{self.ollama_host}/api/generate",
                json=payload,
                timeout=120
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
    
    def analyze_job_comprehensive(self, job_data: Dict) -> Dict[str, Any]:
        """
        Comprehensive job analysis using LLM for ALL filtering and labeling
        """
        if not self.available:
            return self._fallback_analysis(job_data)
        
        # Safely extract job data with proper handling of NaN values
        job_title = str(job_data.get('title', '')) if job_data.get('title') is not None else ''
        job_description = str(job_data.get('description', '')) if job_data.get('description') is not None else ''
        company = str(job_data.get('company', '')) if job_data.get('company') is not None else ''
        original_location = str(job_data.get('location', '')) if job_data.get('location') is not None else ''
        salary = str(job_data.get('salary', '')) if job_data.get('salary') is not None else ''
        source = str(job_data.get('source', '')) if job_data.get('source') is not None else ''
        
        # Handle pandas NaN values that might be present
        if job_title == 'nan':
            job_title = ''
        if job_description == 'nan':
            job_description = ''
        if company == 'nan':
            company = ''
        if original_location == 'nan':
            original_location = ''
        if salary == 'nan':
            salary = ''
        if source == 'nan':
            source = ''
        
        system_prompt = """You are an expert HR analyst and job market specialist. Analyze job postings comprehensively using AI-powered analysis for ALL aspects including filtering, labeling, and classification. Always respond in valid JSON format only."""
        
        prompt = f"""
        Analyze this job posting comprehensively and provide detailed insights in JSON format. Use AI analysis for ALL aspects - do not rely on simple keyword matching or code-based rules. Analyze the full context and meaning.
        
        CRITICAL JOB TITLE RELEVANCE CHECK:
        The candidate is specifically searching for IT/System Administration roles. You MUST filter out jobs that are not directly related to:
        - System Administration (any type or seniority)
        - IT Infrastructure (any type or seniority)
        - Systems Engineering (any type or seniority)
        - IT Integration (any type or seniority)
        - Technical/IT Management (only if hands-on technical)
        - IT Support (any type or seniority)
        - IT Operations (any type or seniority)
        - IT Systems (any type or seniority)
        - IT system engineering (any type or seniority)
        - IT system integration (any type or seniority)
        - IT system administration (any type or seniority)
        - IT system support (any type or seniority)
        - IT system operations (any type or seniority)
        
        IMMEDIATELY REJECT jobs with titles like:
        - Sales (any type)
        - Marketing 
        - Customer Support/Service
        - Design (UI/UX, Graphic)
        - General Project Management (non-technical)
        - HR/Finance/Administrative roles
        - Healthcare/Education/Retail
        
        ONLY ACCEPT jobs that are clearly IT/technical with system administration focus:

        {{
            "filtering_decision": {{
                "should_include": true/false,
                "rejection_reason": "reason if rejected or null",
                "quality_assessment": "high/medium/low/spam",
                "relevance_score": 0-100,
                "is_legitimate_job": true/false,
                "spam_indicators": ["indicator1", "indicator2"] or []
            }},
            "language_analysis": {{
                "primary_language": "german/english/mixed/other",
                "language_confidence": 0-100,
                "secondary_languages": ["language1", "language2"],
                "text_quality": 0-10,
                "is_spam": true/false,
                "professional_tone": 0-10,
                "content_completeness": 0-10,
                "language_reasoning": "explanation of language detection"
            }},
            "location_analysis": {{
                "extracted_location": "actual location from content analysis",
                "location_confidence": 0-100,
                "is_remote": true/false,
                "is_hybrid": true/false,
                "location_type": "remote/hybrid/onsite/flexible",
                "country": "detected country",
                "region": "detected region/state",
                "city": "detected city",
                "work_arrangement_details": "detailed work arrangement description",
                "location_reasoning": "explanation of location extraction"
            }},
            "job_classification": {{
                "category": "Software Development/Data Science/DevOps/Product Management/Design/Marketing/Sales/Other",
                "subcategory": "Frontend/Backend/Full-Stack/Mobile/ML Engineer/etc",
                "seniority": "Intern/Junior/Mid/Senior/Lead/Principal/Director/Executive",
                "experience_required": 0-20,
                "technologies": ["tech1", "tech2", "tech3"],
                "programming_languages": ["language1", "language2"],
                "frameworks": ["framework1", "framework2"],
                "industry": "FinTech/E-commerce/Healthcare/Education/Gaming/etc",
                "company_size": "Startup/Small/Medium/Large/Enterprise",
                "contract_type": "Full-time/Part-time/Contract/Freelance/Internship",
                "salary_mentioned": true/false,
                "salary_range": "extracted range or null",
                "benefits_mentioned": ["benefit1", "benefit2"],
                "classification_reasoning": "explanation of job classification"
            }},

            "job_quality": {{
                "overall_quality": 0-10,
                "description_completeness": 0-10,
                "salary_transparency": 0-10,
                "benefits_mentioned": 0-10,
                "growth_potential": 0-10,
                "work_life_balance_indicators": 0-10,
                "company_reputation_indicators": 0-10,
                "red_flags": ["flag1", "flag2"],
                "green_flags": ["flag1", "flag2"],
                "urgency_level": "low/medium/high",
                "quality_reasoning": "explanation of quality assessment"
            }},
            "content_analysis": {{
                "key_responsibilities": ["responsibility1", "responsibility2"],
                "required_qualifications": ["qualification1", "qualification2"],
                "preferred_qualifications": ["qualification1", "qualification2"],
                "company_culture_indicators": ["indicator1", "indicator2"],
                "growth_opportunities": ["opportunity1", "opportunity2"],
                "work_environment": "description of work environment",
                "team_structure": "description of team structure",
                "content_reasoning": "explanation of content analysis"
            }}
        }}
        
        IMPORTANT: Use comprehensive AI analysis for ALL aspects. Do not use simple keyword matching. Analyze context, meaning, and nuance. Provide detailed reasoning for each decision.
        
        Job Title: {job_title}
        Company: {company}
        Source Platform: {source}
        Original Location: {original_location}
        Salary: {salary if salary else "Not specified"}
        Description: {job_description[:3000]}

        """
        
        response = self._call_ollama(prompt, system_prompt, max_tokens=2000)
        
        if response:
            try:
                analysis = json.loads(response)
                
                # Validate and enrich the analysis
                if analysis and isinstance(analysis, dict):
                    return self._enrich_analysis(analysis, job_data)
                else:
                    self.logger.warning("Invalid analysis format from LLM")
                    return self._fallback_analysis(job_data)
                    
            except json.JSONDecodeError as e:
                self.logger.warning(f"JSON decode error: {e}")
                # Try to extract JSON from response
                try:
                    start = response.find('{')
                    end = response.rfind('}') + 1
                    if start != -1 and end != 0:
                        json_str = response[start:end]
                        analysis = json.loads(json_str)
                        if analysis and isinstance(analysis, dict):
                            return self._enrich_analysis(analysis, job_data)
                except Exception as e2:
                    self.logger.error(f"Failed to extract JSON: {e2}")
        
        # Fallback to rule-based analysis
        self.logger.warning("LLM analysis failed, using fallback")
        return self._fallback_analysis(job_data)
    
    def filter_jobs_by_llm(self, jobs_data: List[Dict]) -> List[Dict]:
        """
        Filter jobs using LLM-based analysis instead of code-based rules
        """
        if not self.available:
            self.logger.warning("LLM not available, skipping filtering")
            return jobs_data
        
        filtered_jobs = []
        rejected_jobs = []
        
        for job in jobs_data:
            try:
                # Get comprehensive analysis
                analysis = self.analyze_job_comprehensive(job)
                
                # Check filtering decision from LLM
                filtering_decision = analysis.get('filtering_decision', {})
                should_include = filtering_decision.get('should_include', True)
                rejection_reason = filtering_decision.get('rejection_reason', '')
                
                if should_include:
                    # Add analysis to job data
                    job.update(analysis)
                    filtered_jobs.append(job)
                else:
                    # Track rejected job
                    job['rejection_reason'] = rejection_reason
                    rejected_jobs.append(job)
                    self.logger.info(f"LLM rejected job: {job.get('title', 'Unknown')} - {rejection_reason}")
                
            except Exception as e:
                self.logger.error(f"Error in LLM filtering for job {job.get('title', 'Unknown')}: {e}")
                # Include job with fallback analysis on error
                job.update(self._fallback_analysis(job))
                filtered_jobs.append(job)
        
        # Log filtering results
        total_jobs = len(jobs_data)
        kept_jobs = len(filtered_jobs)
        rejected_count = len(rejected_jobs)
        
        self.logger.info(f"LLM Filtering Results: {kept_jobs}/{total_jobs} jobs kept, {rejected_count} rejected")
        
        # Update stats
        with self.processing_lock:
            self.stats['jobs_processed'] += total_jobs
            
        return filtered_jobs
    
    def label_jobs_with_llm(self, jobs_data: List[Dict]) -> List[Dict]:
        """
        Add comprehensive LLM-based labels to jobs
        """
        if not self.available:
            self.logger.warning("LLM not available, using fallback labeling")
            return self._fallback_labeling(jobs_data)
        
        labeled_jobs = []
        
        for job in jobs_data:
            try:
                # Get or use existing analysis
                if not any(key in job for key in ['language_analysis', 'location_analysis', 'job_classification']):
                    analysis = self.analyze_job_comprehensive(job)
                    job.update(analysis)
                
                # Add derived labels for easy filtering
                self._add_derived_labels(job)
                labeled_jobs.append(job)
                
            except Exception as e:
                self.logger.error(f"Error in LLM labeling for job {job.get('title', 'Unknown')}: {e}")
                # Add fallback labels
                job.update(self._fallback_analysis(job))
                self._add_derived_labels(job)
                labeled_jobs.append(job)
        
        return labeled_jobs
    
    def _add_derived_labels(self, job: Dict):
        """Add derived labels for easy filtering and display"""
        try:
            # Language label
            lang_analysis = job.get('language_analysis', {})
            job['language'] = lang_analysis.get('primary_language', 'unknown').title()
            
            # Work arrangement label with emoji
            location_analysis = job.get('location_analysis', {})
            if location_analysis.get('is_remote', False):
                job['work_arrangement'] = '🏠 Remote'
                job['work_arrangement_type'] = 'remote'
            elif location_analysis.get('is_hybrid', False):
                job['work_arrangement'] = '🏢 Hybrid'
                job['work_arrangement_type'] = 'hybrid'
            elif location_analysis.get('location_type') == 'flexible':
                job['work_arrangement'] = '🔄 Flexible'
                job['work_arrangement_type'] = 'flexible'
            else:
                job['work_arrangement'] = '🏛️ On-site'
                job['work_arrangement_type'] = 'onsite'
            
            # Priority label (based on job quality)
            job_quality = job.get('job_quality', {})
            quality_score = job_quality.get('overall_quality', 5)
            if quality_score >= 8:
                job['application_priority_display'] = '🔥 Very High'
            elif quality_score >= 6:
                job['application_priority_display'] = '⭐ High'
            elif quality_score >= 4:
                job['application_priority_display'] = '📋 Medium'
            else:
                job['application_priority_display'] = '📝 Low'
            
            # Quality label
            job_quality = job.get('job_quality', {})
            quality_score = job_quality.get('overall_quality', 5)
            if quality_score >= 8:
                job['quality_label'] = '💎 Excellent'
            elif quality_score >= 6:
                job['quality_label'] = '✨ Good'
            elif quality_score >= 4:
                job['quality_label'] = '📊 Average'
            else:
                job['quality_label'] = '⚠️ Below Average'
            
            # Experience match label (default to well-matched)
            job['experience_match_display'] = '✅ Well-matched'
            
        except Exception as e:
            self.logger.error(f"Error adding derived labels: {e}")
    
    def _fallback_labeling(self, jobs_data: List[Dict]) -> List[Dict]:
        """Fallback labeling when LLM is not available"""
        for job in jobs_data:
            # Simple language detection
            title = str(job.get('title', '') or '').lower()
            description = str(job.get('description', '') or '').lower()
            
            # Basic language detection
            german_indicators = ['entwickler', 'ingenieur', 'mitarbeiter', 'der ', 'die ', 'das ', 'und ']
            english_indicators = ['developer', 'engineer', 'the ', 'and ', 'or ', 'with ']
            
            german_score = sum(1 for indicator in german_indicators if indicator in f"{title} {description}")
            english_score = sum(1 for indicator in english_indicators if indicator in f"{title} {description}")
            
            job['language'] = 'German' if german_score > english_score else 'English'
            job['work_arrangement'] = '🏛️ On-site'  # Default
            job['work_arrangement_type'] = 'onsite'
            job['application_priority_display'] = '📋 Medium'
            job['quality_label'] = '📊 Average'
            job['experience_match_display'] = '✅ Well-matched'
        
        return jobs_data
    
    def _enrich_analysis(self, analysis: Dict, job_data: Dict) -> Dict[str, Any]:
        """Enrich analysis with additional metadata and apply LLM-extracted data to core fields"""
        # Start with original job data
        enriched = {**job_data}
        
        # Apply LLM-extracted location data to core location field
        location_analysis = analysis.get('location_analysis', {})
        extracted_location = location_analysis.get('extracted_location', '')
        if extracted_location and extracted_location.strip():
            # Update the core location field with LLM-extracted data
            enriched['location'] = extracted_location.strip()
            if self.logger:
                self.logger.info(f"Updated location from '{job_data.get('location', '')}' to '{extracted_location}' for job '{job_data.get('title', '')[:30]}...'")
        
        # Apply LLM-extracted language data to core language field
        language_analysis = analysis.get('language_analysis', {})
        primary_language = language_analysis.get('primary_language', '')
        if primary_language and primary_language != 'unknown':
            enriched['language'] = primary_language
        
        # Apply LLM-extracted job classification data
        job_classification = analysis.get('job_classification', {})
        if job_classification:
            # Update core job fields with LLM insights
            if job_classification.get('category'):
                enriched['job_category'] = job_classification['category']
            if job_classification.get('seniority'):
                enriched['seniority'] = job_classification['seniority']
            if job_classification.get('experience_required') is not None:
                enriched['experience_required'] = job_classification['experience_required']
            if job_classification.get('technologies'):
                enriched['technologies'] = job_classification['technologies']
            if job_classification.get('programming_languages'):
                enriched['programming_languages'] = job_classification['programming_languages']
            if job_classification.get('frameworks'):
                enriched['frameworks'] = job_classification['frameworks']
            if job_classification.get('industry'):
                enriched['industry'] = job_classification['industry']
            if job_classification.get('contract_type'):
                enriched['contract_type'] = job_classification['contract_type']
        
        # Add all LLM analysis data
        enriched.update(analysis)
        
        # Add processing metadata
        enriched['processing_metadata'] = {
            'processed_at': datetime.now().isoformat(),
            'model_used': self.ollama_model,
            'processing_version': '3.1',
            'llm_extraction_applied': True
        }
        
        # Calculate composite scores
        job_quality = analysis.get('job_quality', {})
        
        enriched['composite_scores'] = {
            'total_score': self._calculate_total_score(analysis),
            'application_urgency': self._calculate_urgency(analysis),
            'job_attractiveness': job_quality.get('overall_quality', 0) * 10
        }
        
        return enriched
    
    def _calculate_total_score(self, analysis: Dict) -> int:
        """Calculate a total score for job ranking"""
        job_quality = analysis.get('job_quality', {}).get('overall_quality', 0) * 10
        language_bonus = 10 if analysis.get('language_analysis', {}).get('primary_language') in ['english', 'german'] else 0
        
        return min(100, int((job_quality * 0.7) + (language_bonus * 0.3)))
    
    def _calculate_urgency(self, analysis: Dict) -> str:
        """Calculate application urgency level"""
        job_quality = analysis.get('job_quality', {}).get('overall_quality', 0)
        
        if job_quality >= 8:
            return 'immediate'
        elif job_quality >= 6:
            return 'high'
        elif job_quality >= 4:
            return 'medium'
        else:
            return 'low'
    
    @ThreadContextManager.wrap_callback
    def process_all_jobs(self, jobs_df) -> List[Dict]:
        """
        Process all jobs from search results with comprehensive analysis
        """
        if not self.available or jobs_df.empty:
            return []
        
        # Clean the dataframe first to handle NaN values
        jobs_df_clean = jobs_df.copy()
        jobs_df_clean = jobs_df_clean.fillna('')  # Replace NaN with empty strings
        
        jobs_list = jobs_df_clean.to_dict('records')
        processed_jobs = []
        
        self.logger.info(f"Starting comprehensive analysis of {len(jobs_list)} jobs...")
        
        # Process jobs in parallel batches
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_job = {
                executor.submit(self._analyze_with_context, self._safe_analyze_job, job): job 
                for job in jobs_list
            }
            
            for future in as_completed(future_to_job):
                try:
                    analyzed_job = future.result(timeout=self.config_manager.get_value('llm.ollama_timeout', 300))
                    if analyzed_job:
                        processed_jobs.append(analyzed_job)
                        
                        # Update stats
                        self._update_stats(analyzed_job)
                        
                        # Log progress
                        total_score = analyzed_job.get('composite_scores', {}).get('total_score', 0)
                        
                        self.logger.info(f"Processed: {analyzed_job.get('title', 'Unknown')[:40]} "
                                       f"(Total: {total_score}%)")
                    
                except Exception as e:
                    original_job = future_to_job[future]
                    job_title = str(original_job.get('title', 'Unknown')) if original_job.get('title') is not None else 'Unknown'
                    self.logger.error(f"Error processing job {job_title}: {e}")
                    # Add job with fallback analysis
                    try:
                        fallback_job = self._fallback_analysis(original_job)
                        processed_jobs.append(fallback_job)
                    except Exception as fallback_error:
                        self.logger.error(f"Fallback analysis also failed for {job_title}: {fallback_error}")
                        continue
        
        # Sort by total score (highest first)
        processed_jobs.sort(key=lambda x: x.get('composite_scores', {}).get('total_score', 0), reverse=True)
        
        self.logger.info(f"Completed analysis of {len(processed_jobs)} jobs")
        return processed_jobs
    
    def filter_and_rank_jobs(self, processed_jobs: List[Dict], criteria: Dict = None) -> List[Dict]:
        """
        Filter and rank processed jobs based on criteria
        """
        if not criteria:
            criteria = {
                'min_quality': 5,
                'languages': ['german', 'english'],
                'exclude_spam': True,
                'max_results': 50
            }
        
        filtered_jobs = []
        
        for job in processed_jobs:
            # Language filter
            lang = job.get('language_analysis', {}).get('primary_language', 'unknown')
            if criteria.get('languages') and lang not in criteria['languages']:
                continue
            

            
            # Quality filter
            quality = job.get('job_quality', {}).get('overall_quality', 0)
            if quality < criteria.get('min_quality', 0):
                continue
            
            # Spam filter
            is_spam = job.get('language_analysis', {}).get('is_spam', False)
            if criteria.get('exclude_spam', True) and is_spam:
                continue
            
            filtered_jobs.append(job)
        
        # Limit results
        max_results = criteria.get('max_results', 50)
        return filtered_jobs[:max_results]
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get comprehensive processing statistics"""
        return {
            **self.stats,
            'model_name': self.ollama_model,
            'available': self.available
        }
    
    def _update_stats(self, analysis: Dict):
        """Update processing statistics"""
        with self.processing_lock:
            self.stats['jobs_processed'] += 1
            
            # Quality stats
            quality = analysis.get('job_quality', {}).get('overall_quality', 0)
            if quality >= 7:
                self.stats['high_quality_jobs'] += 1
            
            # Language breakdown
            lang = analysis.get('language_analysis', {}).get('primary_language', 'unknown')
            self.stats['language_breakdown'][lang] = self.stats['language_breakdown'].get(lang, 0) + 1
            
            # Location breakdown
            location = analysis.get('location_analysis', {}).get('extracted_location', 'unknown')
            self.stats['location_breakdown'][location] = self.stats['location_breakdown'].get(location, 0) + 1
    
    def _fallback_analysis(self, job_data: Dict) -> Dict[str, Any]:
        """Fallback analysis when LLM is not available"""
        # Create safe job data
        safe_job_data = {}
        for key, value in job_data.items():
            if value is None or (isinstance(value, float) and str(value) == 'nan'):
                safe_job_data[key] = ''
            else:
                safe_job_data[key] = str(value) if isinstance(value, (int, float)) else value
        
        return {
            **safe_job_data,
            'language_analysis': {
                'primary_language': 'unknown',
                'language_confidence': 50,
                'text_quality': 5,
                'is_spam': False,
                'professional_tone': 5
            },
            'location_analysis': {
                'extracted_location': job_data.get('location', 'unknown'),
                'location_confidence': 50,
                'is_remote': False,
                'is_hybrid': False,
                'location_type': 'onsite',
                'country': 'unknown',
                'region': 'unknown'
            },
            'job_classification': {
                'category': 'Other',
                'subcategory': 'General',
                'seniority': 'Mid',
                'experience_required': 3,
                'technologies': [],
                'programming_languages': [],
                'frameworks': [],
                'industry': 'Technology',
                'company_size': 'Medium',
                'contract_type': 'Full-time'
            },

            'job_quality': {
                'overall_quality': 5,
                'description_completeness': 5,
                'salary_transparency': 5,
                'benefits_mentioned': 5,
                'growth_potential': 5,
                'work_life_balance_indicators': 5,
                'red_flags': [],
                'green_flags': []
            },
            'composite_scores': {
                'total_score': 50,
                'application_urgency': 'medium',
                'job_attractiveness': 50
            },
            'processing_metadata': {
                'processed_at': datetime.now().isoformat(),
                'model_used': 'fallback',
                'processing_version': '2.0'
            }
        }

    def _analyze_with_context(self, func: Callable, *args, **kwargs) -> Any:
        """Wrapper to ensure analysis functions run with proper thread context"""
        with ThreadContextManager.use_context():
            return func(*args, **kwargs)

    def _safe_analyze_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Safely analyze a job with error handling"""
        try:
            # Basic validation
            if not isinstance(job, dict):
                raise ValueError("Job must be a dictionary")
            
            # Required fields
            title = job.get('title', '')
            company = job.get('company', '')
            description = job.get('description', '')
            
            if not title or not company or not description:
                raise ValueError("Missing required job fields")
            
            # Process job
            analysis_result = self._analyze_job(job)
            if not analysis_result:
                raise ValueError("Job analysis failed")
            
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"Error analyzing job: {str(e)}")
            self.stats['errors'] += 1
            return {
                'error': str(e),
                'job': job,
                'language_analysis': {},
                'location_analysis': {},
                'job_quality': {},

                'composite_scores': {}
            }

    def _analyze_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a single job posting"""
        try:
            # Basic job analysis
            analysis = {
                'title': job.get('title', ''),
                'company': job.get('company', ''),
                'location': job.get('location', ''),
                'description': job.get('description', ''),
                'language_analysis': self._analyze_language(job),
                'location_analysis': self._analyze_location(job),
                'job_quality': self._analyze_job_quality(job),

            }
            
            # Calculate composite scores
            analysis['composite_scores'] = self._calculate_composite_scores(analysis)
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error in job analysis: {str(e)}")
            return {
                'error': str(e),
                'job': job
            }