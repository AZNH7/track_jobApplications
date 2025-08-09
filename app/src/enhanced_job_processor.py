#!/usr/bin/env python3
"""
Enhanced Job Processor with Automatic CV Scoring
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
    - CV matching and scoring
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
            'cv_matches_found': 0,
            'high_quality_jobs': 0,
            'language_breakdown': {},
            'location_breakdown': {}
        }
        
        # CV data
        self.cv_content: Optional[str] = None
        self.cv_skills: List[str] = []
        self.cv_experience_years: int = 0
        self.cv_job_experience: List[Dict[str, Any]] = []
        self.cv_education: List[Dict[str, Any]] = []
        self.cv_summary: str = ""
        
        # Initialize CV data if available
        self._load_cv_data()
        
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
    
    def _load_cv_data(self):
        """Load and parse CV content for matching"""
        cv_paths = [
            "/app/shared/cv/resume.pdf",
            "/app/cv/resume.pdf", 
            "shared/cv/resume.pdf",
            "cv/resume.pdf"
        ]
        
        print("🔍 DEBUG: Enhanced Job Processor CV Loading...")
        print(f"🔍 DEBUG: Current working directory: {os.getcwd()}")
        print(f"🔍 DEBUG: Checking CV paths: {cv_paths}")
        
        for cv_path in cv_paths:
            print(f"🔍 DEBUG: Checking path: {cv_path}")
            if os.path.exists(cv_path):
                print(f"✅ DEBUG: CV file found at: {cv_path}")
                file_size = os.path.getsize(cv_path)
                print(f"📊 DEBUG: CV file size: {file_size} bytes")
                try:
                    self.cv_content = self.extract_pdf_content(cv_path)
                    if self.cv_content:
                        print(f"✅ DEBUG: CV content extracted successfully, length: {len(self.cv_content)} characters")
                        self.cv_skills = self.extract_cv_skills(self.cv_content)
                        self.cv_experience_years = self.extract_experience_years(self.cv_content)
                        self.cv_job_experience = self.extract_job_experience(self.cv_content)
                        self.cv_education = self.extract_education(self.cv_content)
                        self.cv_summary = self.create_cv_summary()
                        self.logger.info(f"CV loaded successfully from {cv_path}")
                        self.logger.info(f"Extracted {len(self.cv_skills)} skills, {self.cv_experience_years} years experience, {len(self.cv_job_experience)} job positions")
                        print(f"✅ DEBUG: CV processing complete - Enhanced Job Processor ready!")
                        return
                    else:
                        print(f"❌ DEBUG: CV content extraction failed - empty content")
                except Exception as e:
                    print(f"❌ DEBUG: Error loading CV from {cv_path}: {e}")
                    self.logger.error(f"Error loading CV from {cv_path}: {e}")
            else:
                print(f"❌ DEBUG: CV file not found at: {cv_path}")
        
        print("❌ DEBUG: No CV found in any path - CV scoring will be disabled")
        self.logger.warning("No CV found. CV scoring will be disabled.")
    
    def is_cv_available(self) -> bool:
        """Check if CV content is available for matching"""
        return self.cv_content is not None and len(self.cv_content.strip()) > 0
    
    def extract_pdf_content(self, pdf_path: str) -> str:
        """Extract text content from PDF"""
        try:
            # Try pdfplumber first (better for complex layouts)
            with pdfplumber.open(pdf_path) as pdf:
                text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                return text.strip()
        except:
            try:
                # Fallback to PyPDF2
                with open(pdf_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    text = ""
                    for page in pdf_reader.pages:
                        text += page.extract_text() + "\n"
                    return text.strip()
            except Exception as e:
                self.logger.error(f"Error extracting PDF content: {e}")
                return ""
    
    def extract_cv_skills(self, cv_text: str) -> List[str]:
        """Extract skills from CV using simple keyword matching"""
        # Common tech skills to look for
        skills_keywords = [
            'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'php', 'ruby', 'go', 'rust',
            'react', 'angular', 'vue', 'django', 'flask', 'spring', 'express', 'laravel',
            'postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch',
            'docker', 'kubernetes', 'aws', 'azure', 'gcp', 'jenkins', 'gitlab', 'github',
            'linux', 'windows', 'macos', 'bash', 'powershell',
            'machine learning', 'deep learning', 'tensorflow', 'pytorch', 'scikit-learn',
            'agile', 'scrum', 'kanban', 'devops', 'ci/cd'
        ]
        
        cv_lower = cv_text.lower()
        found_skills = []
        
        for skill in skills_keywords:
            if skill in cv_lower:
                found_skills.append(skill)
        
        return found_skills
    
    def extract_job_experience(self, cv_text: str) -> List[Dict]:
        """Extract detailed job experience from CV"""
        import re
        from dateutil import parser as date_parser
        from datetime import datetime
        job_experience = []

        # Common job section patterns
        patterns = [
            r'(?:work experience|experience|work\s+history|employment|career).*?(?=education|skills|certifications|projects|$)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, cv_text, re.IGNORECASE | re.DOTALL)
            if matches:
                experience_section = matches[0]
                print(f"DEBUG: Found experience section with pattern: {pattern}")
                print(f"DEBUG: Experience section length: {len(experience_section)}")
                break
        else:
            # If no specific section found, use the whole CV
            experience_section = cv_text
            print(f"DEBUG: No specific experience section found, using whole CV")
            print(f"DEBUG: CV length: {len(cv_text)}")

        # Process line by line to find job entries
        lines = experience_section.split('\n')
        # Patterns for various job entry formats
        job_patterns = [
            # e.g. SENIOR SYSTEM ENGINEER | SEATGEEK INC | 09-2024 TO 03-2025 | BERLIN
            r'^([A-Z][A-Z\s]+)\s*\|\s*([A-Z][A-Z\s]+)\s*\|\s*(\d{2}-\d{4})\s+TO\s+(\d{2}-\d{4}|PRESENT|CURRENT)\s*\|\s*([A-Z][A-Z\s]+)$',
            # e.g. SENIOR SYSTEM ENGINEER | SEATGEEK INC | 09-2024 TO PRESENT | BERLIN
            r'^([A-Z][A-Z\s]+)\s*\|\s*([A-Z][A-Z\s]+)\s*\|\s*(\d{2}-\d{4})\s+TO\s+(PRESENT|CURRENT)\s*\|\s*([A-Z][A-Z\s]+)$',
            # e.g. IT Manager | VIVY GMBH | 02-2019 TO 11-2020 | BERLIN GERMANY
            r'^([A-Z][A-Za-z\s]+)\s*\|\s*([A-Z][A-Za-z\s]+)\s*\|\s*(\d{2}-\d{4})\s+TO\s+(\d{2}-\d{4}|PRESENT|CURRENT)\s*\|\s*([A-Z][A-Za-z\s]+)$',
            # e.g. HEAD OF IT | FLINK SE | 05-2024 – 09-2024 | BERLIN GERMANY (with en dash)
            r'^([A-Z][A-Za-z\s]+)\s*\|\s*([A-Z][A-Za-z\s]+)\s*\|\s*(\d{2}-\d{4})\s*[–—]\s*(\d{2}-\d{4})\s*\|\s*([A-Z][A-Za-z\s]+)$',
            # e.g. CORPORATE IT MANAGER | TRADEREPUBLIC BANK GMBH | 12-2020 TO 05-2022 | BERLIN GERMANY
            r'^([A-Z][A-Za-z\s]+)\s*\|\s*([A-Z][A-Za-z\s]+)\s*\|\s*(\d{2}-\d{4})\s+TO\s+(\d{2}-\d{4})\s*\|\s*([A-Z][A-Za-z\s]+)$',
            # e.g. CUSTOMER ENGINEER | Microsoft | 10-2013 TO 09- 2014 | NRW GERMANY (with space in date)
            r'^([A-Z][A-Za-z\s]+)\s*\|\s*([A-Z][A-Za-z\s]+)\s*\|\s*(\d{2}-\d{4})\s+TO\s+(\d{2}-\s*\d{4})\s*\|\s*([A-Z][A-Za-z\s]+)$',
            # Jobs without location (e.g. SENIOR SYSTEM ENGINEER| CONTENTFUL GMBH | 06-2022 TO 04-2024 |)
            r'^([A-Z][A-Za-z\s]+)\s*\|\s*([A-Z][A-Za-z\s]+)\s*\|\s*(\d{2}-\d{4})\s+TO\s+(\d{2}-\d{4})\s*\|$',
            # Jobs without location (e.g. CORPORATE IT MANAGER | TRADEREPUBLIC BANK GMBH | 12-2020 TO 05-2022 |)
            r'^([A-Z][A-Za-z\s]+)\s*\|\s*([A-Z][A-Za-z\s]+)\s*\|\s*(\d{2}-\d{4})\s+TO\s+(\d{2}-\d{4})\s*\|$',
            # e.g. SENIOR TECHOPS ENGINEER | N26 GMBH | 03-2017 TO 01-2019 | BERLIN
            r'^([A-Z][A-Za-z\s]+)\s*\|\s*([A-Z][A-Za-z\s]+)\s*\|\s*(\d{2}-\d{4})\s+TO\s+(\d{2}-\d{4})\s*\|\s*([A-Z][A-Za-z\s]+)$',
            # More flexible pattern for jobs with special characters
            r'^([A-Z][A-Za-z\s]+)\s*\|\s*([A-Z][A-Za-z\s]+)\s*\|\s*(\d{2}-\d{4})\s+TO\s+(\d{2}-\d{4})\s*\|\s*([A-Z][A-Za-z\s]+)$',
            # Specific pattern for TECHOPS jobs
            r'^([A-Z][A-Za-z\s]+)\s*\|\s*([A-Z][A-Za-z\s]+)\s*\|\s*(\d{2}-\d{4})\s+TO\s+(\d{2}-\d{4})\s*\|\s*([A-Z][A-Za-z\s]+)$',
            # e.g. SENIOR SALES AND SERVICES REPRESENTATIVE IN RETAIL BANKING GROUP | SAMBA FINANCIAL GROUP | 09-2002 TO 09-2005 | RIYADH, SAUDI ARABIA
            r'^([A-Z][A-Za-z\s]+)\s*\|\s*([A-Z][A-Za-z\s]+)\s*\|\s*(\d{2}-\d{4})\s+TO\s+(\d{2}-\d{4})\s*\|\s*([A-Z][A-Za-z\s,]+)$',
            # fallback: Job Title | Company | YYYY-YYYY
            r'^([A-Z][A-Za-z\s]+?)\s*\|\s*([A-Z][A-Za-z\s&.,]+?)\s*\|\s*(\d{4})-(\w+)$',
        ]

        seen_jobs = set()  # Track unique jobs to avoid duplicates
        
        # First pass: handle multi-line jobs (like SENIOR SALES split across lines)
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            # Check if this line ends with | and next line starts with company name
            if line.endswith('|') and i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line and '|' in next_line and any(word in next_line.upper() for word in ['GROUP', 'GMBH', 'INC', 'BANK']):
                    # This is a split job entry
                    job_title = line[:-1].strip()  # Remove the trailing |
                    # Parse the next line for company, dates, location
                    parts = next_line.split('|')
                    if len(parts) >= 3:
                        company = parts[0].strip()
                        dates = parts[1].strip()
                        location = parts[2].strip() if len(parts) > 2 else ''
                        
                        # Parse dates
                        if 'TO' in dates:
                            start, end = dates.split('TO')
                            start = start.strip()
                            end = end.strip()
                            
                            # Create unique job identifier
                            job_id = f"{job_title}_{company}_{start}_{end}"
                            if job_id not in seen_jobs:
                                seen_jobs.add(job_id)
                                # Parse dates for experience calculation
                                try:
                                    if '-' in start:
                                        month, year = start.split('-')
                                        start_date = datetime(int(year), int(month), 1)
                                    else:
                                        start_date = None
                                except:
                                    start_date = None
                                    
                                try:
                                    if '-' in end:
                                        month, year = end.split('-')
                                        end_date = datetime(int(year), int(month), 1)
                                    else:
                                        end_date = None
                                except:
                                    end_date = None
                                
                                job_tasks = self.extract_job_tasks(experience_section, company, job_title)
                                job_experience.append({
                                    'company': company,
                                    'title': job_title,
                                    'start': start,
                                    'end': end,
                                    'location': location,
                                    'start_date': start_date,
                                    'end_date': end_date,
                                    'tasks': job_tasks
                                })
                                break  # Skip the next line since we processed it
        
        # Second pass: handle single-line jobs
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Special handling for TECHOPS job that might not match regex
            if 'SENIOR TECHOPS ENGINEER' in line and 'N26' in line:
                parts = line.split('|')
                if len(parts) >= 4:
                    title = parts[0].strip()
                    company = parts[1].strip()
                    dates = parts[2].strip()
                    location = parts[3].strip()
                    
                    if 'TO' in dates:
                        start, end = dates.split('TO')
                        start = start.strip()
                        end = end.strip()
                        
                        job_id = f"{title}_{company}_{start}_{end}"
                        if job_id not in seen_jobs:
                            seen_jobs.add(job_id)
                            # Parse dates for experience calculation
                            try:
                                if '-' in start:
                                    month, year = start.split('-')
                                    start_date = datetime(int(year), int(month), 1)
                                else:
                                    start_date = None
                            except:
                                start_date = None
                                
                            try:
                                if '-' in end:
                                    month, year = end.split('-')
                                    end_date = datetime(int(year), int(month), 1)
                                else:
                                    end_date = None
                            except:
                                end_date = None
                            
                            job_tasks = self.extract_job_tasks(experience_section, company, title)
                            job_experience.append({
                                'company': company,
                                'title': title,
                                'start': start,
                                'end': end,
                                'location': location,
                                'start_date': start_date,
                                'end_date': end_date,
                                'tasks': job_tasks
                            })
                            continue  # Skip regex processing for this line
            
            for pattern in job_patterns:
                matches = re.findall(pattern, line, re.IGNORECASE)
                for match in matches:
                    # Try to parse dates and calculate duration
                    try:
                        if len(match) == 5:
                            title, company, start, end, location = match
                            # Parse start and end dates (MM-YYYY format)
                            try:
                                if '-' in start:
                                    month, year = start.split('-')
                                    start_date = datetime(int(year), int(month), 1)
                                else:
                                    start_date = date_parser.parse(start, fuzzy=True, default=datetime(1900, 1, 1))
                            except Exception:
                                start_date = None
                            try:
                                if end.lower() in ["present", "current"]:
                                    end_date = datetime.now()
                                elif '-' in end:
                                    month, year = end.split('-')
                                    end_date = datetime(int(year), int(month), 1)
                                else:
                                    end_date = date_parser.parse(end, fuzzy=True, default=datetime(1900, 1, 1))
                            except Exception:
                                end_date = None
                        elif len(match) == 4:
                            title, company, start, end = match
                            location = ''
                            try:
                                if '-' in start:
                                    month, year = start.split('-')
                                    start_date = datetime(int(year), int(month), 1)
                                else:
                                    start_date = date_parser.parse(start, fuzzy=True, default=datetime(1900, 1, 1))
                            except Exception:
                                start_date = None
                            try:
                                if end.lower() in ["present", "current"]:
                                    end_date = datetime.now()
                                elif '-' in end:
                                    month, year = end.split('-')
                                    end_date = datetime(int(year), int(month), 1)
                                else:
                                    end_date = date_parser.parse(end, fuzzy=True, default=datetime(1900, 1, 1))
                            except Exception:
                                end_date = None
                        else:
                            continue
                        # Create unique job identifier to avoid duplicates
                        job_id = f"{title.strip()}_{company.strip()}_{start.strip()}_{end.strip()}"
                        if job_id in seen_jobs:
                            continue
                        seen_jobs.add(job_id)
                        
                        # Extract responsibilities/tasks for this job
                        job_tasks = self.extract_job_tasks(experience_section, company, title)
                        job_experience.append({
                            'company': company.strip(),
                            'title': title.strip(),
                            'start': start.strip(),
                            'end': end.strip(),
                            'location': location.strip(),
                            'start_date': start_date,
                            'end_date': end_date,
                            'tasks': job_tasks
                        })
                    except Exception as e:
                        print(f"DEBUG: Error parsing job entry: {e}")
                        continue
        return job_experience

    def extract_experience_years(self, cv_text: str) -> int:
        """Extract years of experience from CV by summing job durations if possible, else fallback to regex."""
        import re
        from datetime import datetime
        job_experience = self.extract_job_experience(cv_text)
        total_months = 0
        for job in job_experience:
            start_date = job.get('start_date')
            end_date = job.get('end_date')
            if start_date and end_date:
                months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
                if months > 0:
                    total_months += months
        if total_months > 0:
            return round(total_months / 12)
        # fallback to regex
        patterns = [
            r'(\d+)\+?\s*years?\s*(?:of\s*)?experience',
            r'(\d+)\+?\s*years?\s*in',
            r'experience.*?(\d+)\+?\s*years?',
        ]
        cv_lower = cv_text.lower()
        years = []
        for pattern in patterns:
            matches = re.findall(pattern, cv_lower)
            for match in matches:
                try:
                    years.append(int(match))
                except:
                    continue
        return max(years) if years else 0

    def extract_job_tasks(self, cv_text: str, company: str, title: str) -> List[str]:
        """Extract tasks and responsibilities for a specific job"""
        import re
        
        tasks = []
        
        # Look for bullet points or descriptions after the job entry
        # Common patterns: •, -, *, →, etc.
        bullet_patterns = [
            r'[•\-\*→▶]\s*([^•\-\*→▶\n]+)',
            r'[•\-\*→▶]\s*([^•\-\*→▶\n]+(?:\n[^•\-\*→▶\n]+)*)',
        ]
        
        # Find the section after the job entry
        # Try different patterns to match the job entry
        job_patterns = [
            f"{re.escape(company)}.*?{re.escape(title)}",
            f"{re.escape(title)}.*?{re.escape(company)}",
            f"{re.escape(title)}.*?\\|.*?{re.escape(company)}",
            f"{re.escape(company)}.*?\\|.*?{re.escape(title)}"
        ]
        
        job_match = None
        for pattern in job_patterns:
            job_match = re.search(pattern, cv_text, re.IGNORECASE)
            if job_match:
                break
        
        if job_match:
            # Get text after the job entry
            after_job = cv_text[job_match.end():]
            
            # Look for bullet points in the next few lines
            lines = after_job.split('\n')[:20]  # Check next 20 lines
            for line in lines:
                for pattern in bullet_patterns:
                    matches = re.findall(pattern, line)
                    for match in matches:
                        task = match.strip()
                        if len(task) > 10:  # Only include substantial tasks
                            tasks.append(task)
        
        return tasks[:10]  # Limit to 10 tasks
    
    def extract_education(self, cv_text: str) -> List[Dict]:
        """Extract education information from CV"""
        import re
        education = []
        
        # Look for education section first
        education_patterns = [
            r'(?:education|academic|qualifications).*?(?=experience|skills|certifications|projects|$)',
        ]
        
        education_section = ""
        for pattern in education_patterns:
            matches = re.findall(pattern, cv_text, re.IGNORECASE | re.DOTALL)
            if matches:
                education_section = matches[0]
                break
        
        if not education_section:
            return education
            
        # Look for lines with degree keywords in the education section
        degree_keywords = [
            'bachelor', 'master', 'phd', 'msc', 'bsc', 'ba', 'ma', 'university', 'college', 'institute', 'academy', 'school', 'diploma', 'degree'
        ]
        
        lines = education_section.split('\n')
        for line in lines:
            line = line.strip()
            if not line or line.startswith('·') or line.startswith('-'):
                continue
                
            l = line.lower()
            if any(k in l for k in degree_keywords):
                # Try to extract degree and field
                degree_match = re.search(r'([A-Za-z\s]+) in ([A-Za-z\s]+)', line)
                if degree_match:
                    degree = degree_match.group(1).strip()
                    field = degree_match.group(2).strip()
                else:
                    degree = line.strip()
                    field = ''
                education.append({'degree': degree, 'field': field})
        return education
    
    def create_cv_summary(self) -> str:
        """Create a comprehensive CV summary for LLM analysis"""
        if not self.cv_content:
            return ""
        
        summary_parts = []
        
        # Basic info
        summary_parts.append(f"EXPERIENCE: {self.cv_experience_years} years")
        
        # Skills
        if self.cv_skills:
            summary_parts.append(f"SKILLS: {', '.join(self.cv_skills)}")
        
        # Job experience
        if self.cv_job_experience:
            summary_parts.append("JOB EXPERIENCE:")
            for job in self.cv_job_experience:
                summary_parts.append(f"  - {job['title']} at {job['company']} ({job['start']}-{job['end']})")
                if job['tasks']:
                    for task in job['tasks'][:3]:  # Top 3 tasks per job
                        summary_parts.append(f"    • {task}")
        
        # Education
        if self.cv_education:
            summary_parts.append("EDUCATION:")
            for edu in self.cv_education:
                summary_parts.append(f"  - {edu['degree']} in {edu['field']}")
        
        # Full CV content (truncated for LLM context)
        full_content = self.cv_content[:2000]  # Increased from 800 to 2000 characters
        
        summary_parts.append(f"FULL CV CONTENT:\n{full_content}")
        
        return "\n".join(summary_parts)
    
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
        
        # Prepare CV information for matching
        cv_info = ""
        if self.cv_summary:
            cv_info = f"""
            
            CANDIDATE CV SUMMARY:
            {self.cv_summary}
            """
        elif self.cv_content:
            cv_info = f"""
            
            CANDIDATE CV SUMMARY:
            Skills: {', '.join(self.cv_skills[:15])}
            Experience: {self.cv_experience_years} years
            CV Excerpt: {self.cv_content[:800]}
            """
        
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
            "cv_matching": {{
                "overall_match_score": 0-100,
                "skills_match_percentage": 0-100,
                "experience_match": "under-qualified/qualified/over-qualified",
                "matching_skills": ["skill1", "skill2"],
                "missing_skills": ["skill1", "skill2"],
                "interview_likelihood": 0-100,
                "application_priority": "low/medium/high/very-high",
                "match_reasoning": "detailed explanation of match quality",
                "career_growth_potential": 0-10,
                "skill_development_opportunities": ["opportunity1", "opportunity2"],
                "job_title_relevance": 0-100,
                "experience_level_match": 0-100,
                "previous_role_relevance": ["relevant_role1", "relevant_role2"],
                "task_alignment": 0-100,
                "matching_tasks": ["task1", "task2"],
                "career_progression": "lateral/step-up/step-down",
                "industry_experience": "same-industry/related-industry/new-industry",
                "technology_stack_overlap": 0-100,
                "matching_technologies": ["tech1", "tech2"],
                "missing_technologies": ["tech1", "tech2"],
                "education_requirements_met": true/false,
                "certification_relevance": ["cert1", "cert2"],
                "soft_skills_match": 0-100,
                "leadership_experience_match": 0-100,
                "project_management_match": 0-100,
                "team_size_experience": "individual/team-lead/manager/director",
                "remote_work_experience": true/false,
                "international_experience": true/false,
                "language_requirements_met": true/false,
                "salary_expectations_alignment": "below-target/at-target/above-target",
                "work_culture_fit": 0-100,
                "long_term_career_fit": 0-100
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
        {cv_info}
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
            
            # Priority label
            cv_matching = job.get('cv_matching', {})
            priority = cv_matching.get('application_priority', 'medium')
            priority_emojis = {
                'very-high': '🔥 Very High',
                'high': '⭐ High',
                'medium': '📋 Medium',
                'low': '📝 Low'
            }
            job['application_priority_display'] = priority_emojis.get(priority, '📋 Medium')
            
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
            
            # Experience match label
            experience_match = cv_matching.get('experience_match', 'qualified')
            match_emojis = {
                'over-qualified': '🎯 Over-qualified',
                'qualified': '✅ Well-matched',
                'under-qualified': '📚 Stretch Role'
            }
            job['experience_match_display'] = match_emojis.get(experience_match, '✅ Well-matched')
            
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
            'cv_available': self.cv_content is not None,
            'processing_version': '3.1',
            'llm_extraction_applied': True
        }
        
        # Calculate composite scores
        cv_match = analysis.get('cv_matching', {})
        job_quality = analysis.get('job_quality', {})
        
        enriched['composite_scores'] = {
            'total_score': self._calculate_total_score(analysis),
            'application_urgency': self._calculate_urgency(analysis),
            'career_fit': cv_match.get('overall_match_score', 0),
            'job_attractiveness': job_quality.get('overall_quality', 0) * 10
        }
        
        return enriched
    
    def _calculate_total_score(self, analysis: Dict) -> int:
        """Calculate a total score for job ranking"""
        cv_match = analysis.get('cv_matching', {}).get('overall_match_score', 0)
        job_quality = analysis.get('job_quality', {}).get('overall_quality', 0) * 10
        language_bonus = 10 if analysis.get('language_analysis', {}).get('primary_language') in ['english', 'german'] else 0
        
        return min(100, int((cv_match * 0.5) + (job_quality * 0.3) + (language_bonus * 0.2)))
    
    def _calculate_urgency(self, analysis: Dict) -> str:
        """Calculate application urgency level"""
        match_score = analysis.get('cv_matching', {}).get('overall_match_score', 0)
        priority = analysis.get('cv_matching', {}).get('application_priority', 'low')
        
        if match_score >= 80 and priority in ['high', 'very-high']:
            return 'immediate'
        elif match_score >= 60 and priority in ['medium', 'high']:
            return 'high'
        elif match_score >= 40:
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
                        cv_score = analyzed_job.get('cv_matching', {}).get('overall_match_score', 0)
                        total_score = analyzed_job.get('composite_scores', {}).get('total_score', 0)
                        
                        self.logger.info(f"Processed: {analyzed_job.get('title', 'Unknown')[:40]} "
                                       f"(CV: {cv_score}%, Total: {total_score}%)")
                    
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
                'min_cv_match': 30,
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
            
            # CV match filter
            cv_match = job.get('cv_matching', {}).get('overall_match_score', 0)
            if cv_match < criteria.get('min_cv_match', 0):
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
            'available': self.available,
            'cv_loaded': self.cv_content is not None,
            'cv_skills_count': len(self.cv_skills),
            'cv_experience_years': self.cv_experience_years
        }
    
    def _update_stats(self, analysis: Dict):
        """Update processing statistics"""
        with self.processing_lock:
            self.stats['jobs_processed'] += 1
            
            # CV match stats
            cv_match = analysis.get('cv_matching', {}).get('overall_match_score', 0)
            if cv_match >= 70:
                self.stats['cv_matches_found'] += 1
            
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
            'cv_matching': {
                'overall_match_score': 50,
                'skills_match_percentage': 50,
                'experience_match': 'qualified',
                'matching_skills': [],
                'missing_skills': [],
                'interview_likelihood': 50,
                'application_priority': 'medium',
                'match_reasoning': 'Fallback analysis - LLM not available'
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
                'career_fit': 50,
                'job_attractiveness': 50
            },
            'processing_metadata': {
                'processed_at': datetime.now().isoformat(),
                'model_used': 'fallback',
                'cv_available': False,
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
                'cv_matching': None,
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
                'cv_matching': self._analyze_cv_match(job) if self.cv_content else None
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