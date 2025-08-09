"""
Enhanced Job Display Component

Displays job search results with enhanced LLM analysis including:
- Language detection (English/German) with confidence
- CV matching scores based on uploaded CV
- Full job data with description snippets
- Save job functionality for later application
- Interactive job cards with detailed information
"""

import streamlit as st
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import os
from src.scrapers.job_scraper_orchestrator import JobScraperOrchestrator

class EnhancedJobDisplay:
    """Enhanced job display with LLM analysis and save functionality"""
    
    def __init__(self, db_manager, ollama_analyzer=None):
        """
        Initialize the enhanced job display.
        
        Args:
            db_manager: Database manager instance
            ollama_analyzer: Optional Ollama job analyzer for LLM processing
        """
        self.db_manager = db_manager
        self.ollama_analyzer = ollama_analyzer
        self.cv_content = self._load_cv_content()
        self.cv_skills = self._extract_cv_skills() if self.cv_content else []
    
    def _load_cv_content(self) -> Optional[str]:
        """Load CV content if available"""
        try:
            cv_paths = ['/app/cv/resume.pdf', '/app/cv/resume.docx', '/app/cv/resume.txt']
            
            for path in cv_paths:
                if os.path.exists(path):
                    if path.endswith('.txt'):
                        with open(path, 'r', encoding='utf-8') as f:
                            return f.read()
                    elif path.endswith('.pdf'):
                        try:
                            import PyPDF2
                            with open(path, 'rb') as f:
                                reader = PyPDF2.PdfReader(f)
                                return '\n'.join([page.extract_text() for page in reader.pages])
                        except ImportError:
                            st.warning("PyPDF2 not available for PDF reading. Please install it using: pip install PyPDF2")
                    elif path.endswith('.docx'):
                        try:
                            import docx
                            doc = docx.Document(path)
                            return '\n'.join([p.text for p in doc.paragraphs])
                        except ImportError:
                            st.warning("python-docx not available for DOCX reading. Please install it using: pip install python-docx")
            return None
        except Exception as e:
            st.warning(f"Could not load CV: {e}")
            return None
    
    def _extract_cv_skills(self) -> List[str]:
        """Extract skills from CV using simple keyword matching"""
        if not self.cv_content:
            return []
        
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
        
        cv_lower = self.cv_content.lower()
        found_skills = []
        
        for skill in skills_keywords:
            if skill in cv_lower:
                found_skills.append(skill)
        
        return found_skills
    
    def enhance_jobs_with_llm(self, jobs: List[Dict]) -> List[Dict]:
        """
        Enhance jobs with LLM analysis for language detection and CV scoring.
        
        Args:
            jobs: List of job dictionaries
            
        Returns:
            List of enhanced job dictionaries with LLM analysis
        """
        if not self.ollama_analyzer or not hasattr(self.ollama_analyzer, 'available') or not self.ollama_analyzer.available:
            # Fallback to simple analysis
            return self._enhance_jobs_fallback(jobs)
        
        enhanced_jobs = []
        total_jobs = len(jobs)
        
        # Create progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, job in enumerate(jobs):
            try:
                # Update progress
                progress = (i + 1) / total_jobs
                progress_bar.progress(progress)
                status_text.text(f"🤖 Analyzing job {i+1}/{total_jobs}: {job.get('title', 'Unknown')[:50]}...")
                
                # Perform LLM analysis
                analysis = self._analyze_job_with_llm(job)
                
                # Combine original job with analysis
                enhanced_job = {**job, **analysis}
                enhanced_jobs.append(enhanced_job)
                
            except Exception as e:
                st.warning(f"Failed to analyze job {job.get('title', 'Unknown')}: {e}")
                # Include job with fallback analysis
                enhanced_jobs.append({**job, **self._fallback_job_analysis(job)})
        
        # Clear progress indicators
        progress_bar.empty()
        status_text.empty()
        
        return enhanced_jobs
    
    def _analyze_job_with_llm(self, job: Dict) -> Dict:
        """Analyze a single job with LLM for language detection and CV scoring"""
        job_title = job.get('title', '')
        job_description = job.get('description', '')
        company = job.get('company', '')
        
        # Language detection analysis
        language_analysis = {}
        if self.ollama_analyzer:
            try:
                language_analysis = self.ollama_analyzer.analyze_job_posting(
                    job_title, job_description, company
                )
            except Exception as e:
                st.warning(f"Language analysis failed: {e}")
        
        # CV scoring if CV is available
        cv_scoring = {}
        if self.cv_content and self.ollama_analyzer:
            try:
                cv_scoring = self.ollama_analyzer.score_job_against_cv(
                    job_title, job_description, self.cv_content, self.cv_skills, company
                )
            except Exception as e:
                st.warning(f"CV scoring failed: {e}")
        
        # Create language tag and confidence
        primary_language = language_analysis.get('language_analysis', {}).get('primary_language', 'unknown')
        language_confidence = language_analysis.get('language_analysis', {}).get('language_confidence', 0)
        
        # Determine language tag
        if primary_language == 'german':
            language_tag = f"🇩🇪 German ({language_confidence}%)"
        elif primary_language == 'english':
            language_tag = f"🇺🇸 English ({language_confidence}%)"
        else:
            language_tag = f"❓ Unknown ({language_confidence}%)"
        
        # CV match score and tag
        cv_match_score = cv_scoring.get('overall_match_score', 0) if cv_scoring else 0
        
        if cv_match_score >= 80:
            cv_match_tag = f"🎯 Excellent Match ({cv_match_score}%)"
            cv_match_color = "success"
        elif cv_match_score >= 60:
            cv_match_tag = f"✅ Good Match ({cv_match_score}%)"
            cv_match_color = "info"
        elif cv_match_score >= 40:
            cv_match_tag = f"🔶 Fair Match ({cv_match_score}%)"
            cv_match_color = "warning"
        else:
            cv_match_tag = f"❌ Poor Match ({cv_match_score}%)"
            cv_match_color = "error"
        
        return {
            'language_analysis': language_analysis.get('language_analysis', {}),
            'cv_scoring': cv_scoring,
            'language_tag': language_tag,
            'cv_match_tag': cv_match_tag,
            'cv_match_color': cv_match_color,
            'cv_match_score': cv_match_score,
            'primary_language': primary_language,
            'language_confidence': language_confidence,
            'llm_analysis_complete': True
        }
    
    def _enhance_jobs_fallback(self, jobs: List[Dict]) -> List[Dict]:
        """Fallback enhancement when LLM is not available"""
        enhanced_jobs = []
        
        for job in jobs:
            enhanced_job = {**job, **self._fallback_job_analysis(job)}
            enhanced_jobs.append(enhanced_job)
        
        return enhanced_jobs
    
    def _fallback_job_analysis(self, job: Dict) -> Dict:
        """Fallback analysis when LLM is not available"""
        title = str(job.get('title', '') or '').lower()
        description = str(job.get('description', '') or '').lower()
        
        # Simple language detection
        german_indicators = ['entwickler', 'ingenieur', 'mitarbeiter', 'der ', 'die ', 'das ', 'und ', 'gmbh']
        english_indicators = ['developer', 'engineer', 'the ', 'and ', 'or ', 'with ', 'company']
        
        german_score = sum(1 for indicator in german_indicators if indicator in f"{title} {description}")
        english_score = sum(1 for indicator in english_indicators if indicator in f"{title} {description}")
        
        if german_score > english_score:
            primary_language = 'german'
            language_tag = "🇩🇪 German (est.)"
            confidence = min(95, 50 + (german_score * 5))
        else:
            primary_language = 'english'
            language_tag = "🇺🇸 English (est.)"
            confidence = min(95, 50 + (english_score * 5))
        
        # Simple CV matching based on keyword overlap
        cv_match_score = 50  # Default
        if self.cv_skills:
            matching_skills = [skill for skill in self.cv_skills if skill.lower() in f"{title} {description}"]
            cv_match_score = min(100, int((len(matching_skills) / len(self.cv_skills)) * 100))
        
        cv_match_tag = f"📊 Est. Match ({cv_match_score}%)"
        cv_match_color = "info"
        
        return {
            'language_tag': language_tag,
            'cv_match_tag': cv_match_tag,
            'cv_match_color': cv_match_color,
            'cv_match_score': cv_match_score,
            'primary_language': primary_language,
            'language_confidence': confidence,
            'llm_analysis_complete': False
        }
    
    def display_enhanced_jobs(self, jobs: List[Dict], show_filters: bool = True):
        """
        Display enhanced jobs with filtering options and save functionality.
        
        Args:
            jobs: List of enhanced job dictionaries
            show_filters: Whether to show filter options
        """
        if not jobs:
            st.info("No jobs to display.")
            return
        
        st.subheader(f"🎯 Job Search Results ({len(jobs)} jobs found)")
        
        # Filters
        if show_filters:
            self._show_job_filters(jobs)
        
        # Apply filters
        filtered_jobs = self._apply_filters(jobs)
        
        if not filtered_jobs:
            st.warning("No jobs match the current filters.")
            return
        
        # Display jobs
        st.markdown(f"### 📋 Showing {len(filtered_jobs)} jobs")
        
        # Sort options
        sort_options = {
            "CV Match Score (High to Low)": lambda x: x.get('cv_match_score', 0),
            "CV Match Score (Low to High)": lambda x: -x.get('cv_match_score', 0),
            "Company A-Z": lambda x: (x.get('company', '') or '').lower(),
            "Title A-Z": lambda x: (x.get('title', '') or '').lower(),
            "Source": lambda x: (x.get('source', '') or '').lower()
        }
        
        sort_by = st.selectbox("Sort by:", list(sort_options.keys()), index=0)
        
        # Sort jobs
        if sort_by in sort_options:
            filtered_jobs = sorted(filtered_jobs, key=sort_options[sort_by], reverse=True)
        
        # Display job cards
        for i, job in enumerate(filtered_jobs):
            self._display_job_card(job, i)
    
    def _show_job_filters(self, jobs: List[Dict]):
        """Show filter options for jobs"""
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # Language filter
            languages = list(set([job.get('primary_language', 'unknown') for job in jobs]))
            selected_languages = st.multiselect(
                "Languages:",
                options=languages,
                default=languages,
                key="language_filter"
            )
        
        with col2:
            # CV match score filter
            min_cv_score = st.slider(
                "Min CV Match Score:",
                min_value=0,
                max_value=100,
                value=0,
                step=10,
                key="cv_score_filter"
            )
        
        with col3:
            # Source filter
            sources = list(set([job.get('source', job.get('platform', 'unknown')) for job in jobs]))
            selected_sources = st.multiselect(
                "Sources:",
                options=sources,
                default=sources,
                key="source_filter"
            )
        
        with col4:
            # Only high quality jobs
            high_quality_only = st.checkbox(
                "High Quality Only",
                value=False,
                help="Show only jobs with CV match score >= 70%",
                key="quality_filter"
            )
        
        # Store filter values in session state
        st.session_state.job_filters = {
            'languages': selected_languages,
            'min_cv_score': min_cv_score,
            'sources': selected_sources,
            'high_quality_only': high_quality_only
        }
    
    def _apply_filters(self, jobs: List[Dict]) -> List[Dict]:
        """Apply filters to job list"""
        if 'job_filters' not in st.session_state:
            return jobs
        
        filters = st.session_state.job_filters
        filtered_jobs = []
        
        for job in jobs:
            # Language filter
            if job.get('primary_language', 'unknown') not in filters['languages']:
                continue
            
            # CV score filter
            if job.get('cv_match_score', 0) < filters['min_cv_score']:
                continue
            
            # Source filter
            job_source = job.get('source', job.get('platform', 'unknown'))
            if job_source not in filters['sources']:
                continue
            
            # High quality filter
            if filters['high_quality_only'] and job.get('cv_match_score', 0) < 70:
                continue
            
            filtered_jobs.append(job)
        
        return filtered_jobs
    
    def _display_job_card(self, job: Dict, index: int):
        """Display an individual job card with enhanced information"""
        # Create expandable job card
        title = job.get('title', 'Unknown Title')
        company = job.get('company', 'Unknown Company')
        location = job.get('location', 'Unknown Location')
        
        # Create header with basic info and tags
        with st.expander(f"🏢 {title} at {company}", expanded=False):
            # Top row with key information
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                st.markdown(f"""
                **📍 Location:** {location}  
                **🔗 Source:** {job.get('source', job.get('platform', 'Unknown'))}  
                **📅 Found:** {job.get('scraped_date', 'Unknown')}
                """)
            
            with col2:
                # Language tag
                if 'language_tag' in job:
                    st.markdown(f"**Language:** {job['language_tag']}")
                
                # CV match tag with colored badge
                if 'cv_match_tag' in job:
                    match_score = job.get('cv_match_score', 0)
                    if match_score >= 70:
                        st.success(job['cv_match_tag'])
                    elif match_score >= 50:
                        st.info(job['cv_match_tag'])
                    elif match_score >= 30:
                        st.warning(job['cv_match_tag'])
                    else:
                        st.error(job['cv_match_tag'])
            
            with col3:
                # Action buttons
                save_key = f"save_job_{index}"
                
                if st.button("💾 Save Job", key=save_key, help="Save this job for later application"):
                    self._save_job_to_applications(job)
                
                if job.get('url'):
                    st.markdown(f"[🔗 View Job]({job['url']})")
            
            # Job description section
            if job.get('description'):
                st.markdown("**📝 Job Description:**")
                
                # Show snippet by default, full description in expander
                description = job['description']
                snippet_length = 300
                
                if len(description) > snippet_length:
                    snippet = description[:snippet_length] + "..."
                    st.markdown(f"_{snippet}_")
                    
                    with st.expander("📖 Read Full Description"):
                        st.markdown(description)
                else:
                    st.markdown(f"_{description}_")
            
            # LLM Analysis details if available
            if job.get('llm_analysis_complete'):
                self._show_llm_analysis_details(job)
            
            # Salary information
            if job.get('salary'):
                st.markdown(f"**💰 Salary:** {job['salary']}")
            
            st.markdown("---")
    
    def _show_llm_analysis_details(self, job: Dict):
        """Show detailed LLM analysis in an expander"""
        with st.expander("🤖 AI Analysis Details"):
            # Language analysis
            if 'language_analysis' in job:
                lang_analysis = job['language_analysis']
                st.markdown("**Language Analysis:**")
                st.markdown(f"- Primary Language: {lang_analysis.get('primary_language', 'Unknown')}")
                st.markdown(f"- Confidence: {lang_analysis.get('language_confidence', 0)}%")
                if lang_analysis.get('text_quality'):
                    st.markdown(f"- Text Quality: {lang_analysis.get('text_quality', 0)}/10")
            
            # CV scoring details
            if 'cv_scoring' in job and job['cv_scoring']:
                cv_scoring = job['cv_scoring']
                st.markdown("**CV Match Analysis:**")
                st.markdown(f"- Overall Match: {cv_scoring.get('overall_match_score', 0)}%")
                st.markdown(f"- Skills Match: {cv_scoring.get('skill_match_score', 0)}%")
                st.markdown(f"- Experience Match: {cv_scoring.get('experience_match_score', 0)}%")
                
                if cv_scoring.get('matching_skills'):
                    st.markdown(f"- Matching Skills: {', '.join(cv_scoring['matching_skills'][:5])}")
                
                if cv_scoring.get('missing_critical_skills'):
                    st.markdown(f"- Missing Skills: {', '.join(cv_scoring['missing_critical_skills'][:5])}")
                
                if cv_scoring.get('recommendation'):
                    st.markdown(f"- Recommendation: {cv_scoring['recommendation']}")
    
    def _save_job_to_applications(self, job: Dict):
        """Save a job to the applications table"""
        try:
            if self.db_manager is None:
                st.error("❌ Database manager not available")
                return
            
            # Apply LLM assessment if not already done
            if not job.get('llm_quality_score') and not job.get('llm_relevance_score'):
                try:
                    # Import the job orchestrator to use its LLM assessment
                    from src.scrapers.job_scraper_orchestrator import JobScraperOrchestrator
                    
                    # Create a temporary orchestrator for LLM assessment
                    temp_orchestrator = JobScraperOrchestrator(debug=False)
                    
                    # Apply LLM assessment
                    llm_assessment = temp_orchestrator._llm_job_assessment(job)
                    
                    # Add LLM assessment to job data
                    job['llm_assessment'] = llm_assessment
                    job['llm_filtered'] = llm_assessment.get('should_filter', False)
                    job['llm_quality_score'] = llm_assessment.get('quality_score', 0)
                    job['llm_relevance_score'] = llm_assessment.get('relevance_score', 0)
                    job['llm_reasoning'] = llm_assessment.get('reasoning', '')
                    
                    # Add language detection and job snippet
                    job['language'] = temp_orchestrator._llm_detect_language(job.get('description', ''))
                    job['job_snippet'] = llm_assessment.get('job_snippet', '')
                    
                    print(f"🤖 Applied LLM assessment to job: {job.get('title', 'Unknown')}")
                    print(f"   - Quality Score: {job['llm_quality_score']}/10")
                    print(f"   - Relevance Score: {job['llm_relevance_score']}/10")
                    
                except Exception as e:
                    print(f"⚠️ LLM assessment failed for job {job.get('title', 'Unknown')}: {e}")
                    # Continue with basic assessment
                    job['llm_quality_score'] = 5  # Default medium quality
                    job['llm_relevance_score'] = 7  # Default assumption of relevance
                    job['llm_reasoning'] = 'Basic assessment (LLM not available)'
            
            # Check if already exists
            existing_query = """
                SELECT id FROM job_applications 
                WHERE url = %s
            """
            existing = self.db_manager.execute_query(
                existing_query, 
                (job.get('url', ''),), 
                fetch='one'
            )
            
            if existing:
                st.warning("📋 Job already saved to applications!")
                return
            
            # Insert into job_applications table
            insert_query = """
                INSERT INTO job_applications (
                    title, company, location, salary, url, source, 
                    added_date, status, notes
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, 'saved', %s
                )
            """
            
            # Prepare notes with LLM analysis
            notes = "Auto-saved from job search"
            if job.get('cv_match_score'):
                notes += f" | CV Match: {job['cv_match_score']}%"
            if job.get('primary_language'):
                notes += f" | Language: {job['primary_language']}"
            if job.get('llm_quality_score'):
                notes += f" | Quality: {job['llm_quality_score']}/10"
            if job.get('llm_relevance_score'):
                notes += f" | Relevance: {job['llm_relevance_score']}/10"
            
            params = (
                job.get('title', ''),
                job.get('company', ''),
                job.get('location', ''),
                job.get('salary', ''),
                job.get('url', ''),
                job.get('source', job.get('platform', '')),
                datetime.now(),
                notes
            )
            
            self.db_manager.execute_query(insert_query, params)
            st.success("✅ Job saved to applications!")
            
        except Exception as e:
            st.error(f"❌ Error saving job: {e}")
    
    def get_job_statistics(self, jobs: List[Dict]) -> Dict[str, Any]:
        """Get statistics about the job search results"""
        if not jobs:
            return {}
        
        # Language breakdown
        languages = {}
        cv_scores = []
        sources = {}
        high_quality_count = 0
        
        for job in jobs:
            # Language stats
            lang = job.get('primary_language', 'unknown')
            languages[lang] = languages.get(lang, 0) + 1
            
            # CV scores
            score = job.get('cv_match_score', 0)
            cv_scores.append(score)
            if score >= 70:
                high_quality_count += 1
            
            # Source stats
            source = job.get('source', job.get('platform', 'unknown'))
            sources[source] = sources.get(source, 0) + 1
        
        avg_cv_score = sum(cv_scores) / len(cv_scores) if cv_scores else 0
        
        return {
            'total_jobs': len(jobs),
            'languages': languages,
            'sources': sources,
            'avg_cv_score': avg_cv_score,
            'high_quality_count': high_quality_count,
            'high_quality_percentage': (high_quality_count / len(jobs)) * 100
        }
    
    def show_job_statistics(self, jobs: List[Dict]):
        """Display job search statistics"""
        stats = self.get_job_statistics(jobs)
        
        if not stats:
            return
        
        st.subheader("📊 Job Search Statistics")
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Jobs", stats['total_jobs'])
        
        with col2:
            st.metric("Avg CV Match", f"{stats['avg_cv_score']:.1f}%")
        
        with col3:
            st.metric("High Quality Jobs", stats['high_quality_count'])
        
        with col4:
            st.metric("Quality Rate", f"{stats['high_quality_percentage']:.1f}%")
        
        # Breakdowns
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Languages:**")
            for lang, count in stats['languages'].items():
                percentage = (count / stats['total_jobs']) * 100
                st.markdown(f"- {lang.title()}: {count} ({percentage:.1f}%)")
        
        with col2:
            st.markdown("**Sources:**")
            for source, count in stats['sources'].items():
                percentage = (count / stats['total_jobs']) * 100
                st.markdown(f"- {source}: {count} ({percentage:.1f}%)") 