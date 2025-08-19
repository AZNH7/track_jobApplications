"""
Job Email Matcher Service

Service for matching job applications with email applications and linking them together.
"""

import logging
from typing import Dict, List, Any, Optional
from fuzzywuzzy import fuzz
import re


class JobEmailMatcherService:
    """
    Service for matching job applications with email applications.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def find_best_matching_email(self, job: Dict[str, Any], all_emails: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Find the best matching email for a given job.
        
        Args:
            job: Job dictionary containing job details
            all_emails: List of email dictionaries from the database
            
        Returns:
            Dictionary containing matched email, score, and reason, or None if no good match
        """
        try:
            if not all_emails:
                return None
            
            job_title = job.get('title', '').lower()
            job_company = job.get('company', '').lower()
            job_location = job.get('location', '').lower()
            
            best_match = None
            best_score = 0
            best_reason = ""
            
            for email in all_emails:
                email_subject = email.get('subject', '').lower()
                email_sender = email.get('sender', '').lower()
                email_body = email.get('body', '').lower()
                
                # Calculate various matching scores
                title_score = self._calculate_title_match(job_title, email_subject, email_body)
                company_score = self._calculate_company_match(job_company, email_sender, email_subject, email_body)
                location_score = self._calculate_location_match(job_location, email_body)
                
                # Weighted combination of scores
                total_score = (title_score * 0.5) + (company_score * 0.3) + (location_score * 0.2)
                
                if total_score > best_score and total_score > 60:  # Minimum threshold
                    best_score = total_score
                    best_match = email
                    best_reason = self._generate_match_reason(title_score, company_score, location_score)
            
            if best_match:
                return {
                    'email': best_match,
                    'score': round(best_score, 1),
                    'reason': best_reason
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error finding best matching email: {e}")
            return None
    
    def link_job_to_email_application(self, db_manager, job_id: str, application_id: str) -> bool:
        """
        Link a job to an email application in the database.
        
        Args:
            db_manager: Database manager instance
            job_id: ID of the job to link
            application_id: ID of the email application to link to
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Update the job listing to link it to the application
            update_query = """
                UPDATE job_listings 
                SET application_id = %s, updated_at = NOW()
                WHERE id = %s
            """
            
            db_manager.execute_query(update_query, (application_id, job_id))
            
            self.logger.info(f"Successfully linked job {job_id} to application {application_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error linking job to email application: {e}")
            return False
    
    def _calculate_title_match(self, job_title: str, email_subject: str, email_body: str) -> float:
        """Calculate how well the job title matches the email content."""
        if not job_title:
            return 0
        
        # Extract key words from job title
        title_words = re.findall(r'\b\w+\b', job_title)
        title_words = [word for word in title_words if len(word) > 2]  # Filter out short words
        
        if not title_words:
            return 0
        
        # Check subject match
        subject_score = max(fuzz.partial_ratio(job_title, email_subject), 
                          fuzz.token_sort_ratio(job_title, email_subject))
        
        # Check body match
        body_score = max(fuzz.partial_ratio(job_title, email_body), 
                        fuzz.token_sort_ratio(job_title, email_body))
        
        # Check individual word matches
        word_matches = 0
        for word in title_words:
            if word in email_subject or word in email_body:
                word_matches += 1
        
        word_score = (word_matches / len(title_words)) * 100 if title_words else 0
        
        return max(subject_score, body_score, word_score)
    
    def _calculate_company_match(self, job_company: str, email_sender: str, email_subject: str, email_body: str) -> float:
        """Calculate how well the company name matches the email content."""
        if not job_company:
            return 0
        
        # Check sender domain match
        sender_domain = self._extract_domain(email_sender)
        company_domain = self._extract_domain(job_company)
        
        if sender_domain and company_domain and sender_domain == company_domain:
            return 100
        
        # Check exact company name match
        if job_company in email_sender or job_company in email_subject or job_company in email_body:
            return 90
        
        # Check fuzzy match
        sender_score = fuzz.partial_ratio(job_company, email_sender)
        subject_score = fuzz.partial_ratio(job_company, email_subject)
        body_score = fuzz.partial_ratio(job_company, email_body)
        
        return max(sender_score, subject_score, body_score)
    
    def _calculate_location_match(self, job_location: str, email_body: str) -> float:
        """Calculate how well the job location matches the email content."""
        if not job_location or not email_body:
            return 0
        
        # Simple location matching
        if job_location in email_body:
            return 80
        
        # Fuzzy match for location
        return fuzz.partial_ratio(job_location, email_body)
    
    def _extract_domain(self, text: str) -> Optional[str]:
        """Extract domain from email or company text."""
        if not text:
            return None
        
        # Look for email domain
        email_match = re.search(r'@([\w.-]+)', text)
        if email_match:
            return email_match.group(1).lower()
        
        # Look for website domain
        domain_match = re.search(r'(?:https?://)?(?:www\.)?([\w.-]+)', text)
        if domain_match:
            return domain_match.group(1).lower()
        
        return None
    
    def _generate_match_reason(self, title_score: float, company_score: float, location_score: float) -> str:
        """Generate a human-readable reason for the match."""
        reasons = []
        
        if title_score > 70:
            reasons.append("strong job title match")
        elif title_score > 50:
            reasons.append("moderate job title match")
        
        if company_score > 70:
            reasons.append("strong company match")
        elif company_score > 50:
            reasons.append("moderate company match")
        
        if location_score > 70:
            reasons.append("location match")
        
        if not reasons:
            reasons.append("general content similarity")
        
        return ", ".join(reasons)
