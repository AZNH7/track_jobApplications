#!/usr/bin/env python3
"""
AI Career Agent - Intelligent Career Advisory Assistant
Provides insights on job search and email analysis
"""

import streamlit as st
import requests
import json
import pandas as pd
from typing import Dict, List, Optional, Any
import time
from datetime import datetime, timedelta
import os
import PyPDF2
import pdfplumber
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go

class AICareerAgent:
    """
    Intelligent career advisory agent powered by qwen2.5:14b
    Provides comprehensive insights and recommendations
    """
    
    def __init__(self, ollama_host: str = None, model_name: str = None):
        # Get configuration
        from config_manager import get_config_manager
        config_manager = get_config_manager()
        
        self.ollama_host = (ollama_host or config_manager.get_value('llm.ollama_host', 'http://localhost:11434')).rstrip('/')
        self.model_name = model_name or config_manager.get_value('llm.ollama_model', 'llama3:8b')
        
        # Test connection
        self.available = self.test_connection()
        

    
    def test_connection(self) -> bool:
        """Test connection to Ollama server"""
        try:
            response = requests.get(f"{self.ollama_host}/api/tags", timeout=10)
            return response.status_code == 200
        except:
            return False
    

    

    
    def _call_ollama(self, prompt: str, system_prompt: str = "", max_tokens: int = 2000) -> Optional[str]:
        """Make a call to Ollama API"""
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
                    "temperature": 0.3,
                    "top_p": 0.9,
                    "repeat_penalty": 1.1
                }
            }
            
            response = requests.post(
                f"{self.ollama_host}/api/generate",
                json=payload,
                timeout=config_manager.get_value('llm.ollama_timeout', 60)
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '').strip()
            else:
                return None
                
        except Exception as e:
            st.error(f"Error calling AI agent: {e}")
            return None
    

    
    def analyze_job_market_trends(self, job_data: List[Dict]) -> str:
        """Analyze job market trends from search results"""
        if not self.available or not job_data:
            return "AI agent not available or no job data provided."
        
        # Prepare job market summary
        total_jobs = len(job_data)
        companies = [job.get('company', 'Unknown') for job in job_data]
        locations = [job.get('location', 'Unknown') for job in job_data]
        titles = [job.get('title', 'Unknown') for job in job_data]
        
        # Get top companies and locations
        company_counts = pd.Series(companies).value_counts().head(10).to_dict()
        location_counts = pd.Series(locations).value_counts().head(10).to_dict()
        
        system_prompt = """You are an expert job market analyst. Provide insightful analysis of job market trends and opportunities."""
        
        prompt = f"""
        Analyze this job market data and provide comprehensive insights:
        
        Total Jobs Found: {total_jobs}
        
        Top Companies Hiring:
        {json.dumps(company_counts, indent=2)}
        
        Top Locations:
        {json.dumps(location_counts, indent=2)}
        
        Sample Job Titles:
        {titles[:20]}
        
        Please provide:
        1. Market trends analysis
        2. Opportunities and threats
        3. Salary expectations
        4. Skills in demand
        5. Geographic insights
        6. Industry patterns
        7. Recommendations for job seekers
        
        Format as a comprehensive market report.
        """
        
        return self._call_ollama(prompt, system_prompt, max_tokens=2000) or "Analysis not available."
    
    def analyze_email_patterns(self, email_data: List[Dict]) -> str:
        """Analyze email patterns and application insights"""
        if not self.available or not email_data:
            return "AI agent not available or no email data provided."
        
        # Prepare email summary
        total_emails = len(email_data)
        companies = [email.get('company', 'Unknown') for email in email_data]
        statuses = [email.get('status', 'Unknown') for email in email_data]
        
        system_prompt = """You are an expert in job application analysis and career strategy."""
        
        prompt = f"""
        Analyze these job application email patterns and provide insights:
        
        Total Application Emails: {total_emails}
        Companies: {list(set(companies))[:20]}
        Application Statuses: {list(set(statuses))}
        
        Sample Email Data:
        {json.dumps(email_data[:10], indent=2)}
        
        Please analyze:
        1. Application success patterns
        2. Response rates by company type
        3. Timeline patterns
        4. Common rejection reasons
        5. Successful application characteristics
        6. Follow-up strategies
        7. Optimization recommendations
        
        Provide actionable insights for improving application success.
        """
        
        return self._call_ollama(prompt, system_prompt, max_tokens=2000) or "Analysis not available."
    
    def get_personalized_advice(self, query: str, context: Dict = None) -> str:
        """Get personalized career advice"""
        if not self.available:
            return "AI agent not available."
        

        
        context_info = ""
        if context:
            context_info = f"\nAdditional Context: {json.dumps(context, indent=2)}"
        
        system_prompt = """You are an expert career advisor with deep knowledge of the job market, career development, and professional growth strategies."""
        
        prompt = f"""
        Question: {query}
        {context_info}
        
        Provide personalized, actionable career advice based on the candidate's profile and current market conditions.
        Be specific, practical, and encouraging.
        """
        
        return self._call_ollama(prompt, system_prompt, max_tokens=1500) or "Advice not available."
    
    def generate_job_search_strategy(self, preferences: Dict) -> str:
        """Generate personalized job search strategy"""
        if not self.available:
            return "AI agent not available."
        

        
        system_prompt = """You are an expert career strategist specializing in job search optimization."""
        
        prompt = f"""
        Generate a comprehensive job search strategy based on:
        
        Preferences: {json.dumps(preferences, indent=2)}
        
        Create a detailed strategy covering:
        1. Target role positioning
        2. Application timeline
        3. Platform strategy
        4. Networking approach
        5. Skill development priorities
        6. Interview preparation
        7. Salary negotiation
        8. Success metrics
        
        Make it actionable and specific to the candidate's profile.
        """
        
        return self._call_ollama(prompt, system_prompt, max_tokens=2000) or "Strategy not available."
    
    def analyze_application_performance(self, application_data: List[Dict]) -> Dict[str, Any]:
        """Analyze application performance and success patterns"""
        if not application_data:
            return {}
        
        # Calculate metrics
        total_applications = len(application_data)
        responses = len([app for app in application_data if app.get('status') not in ['No Response', 'Pending']])
        interviews = len([app for app in application_data if 'Interview' in str(app.get('status', ''))])
        offers = len([app for app in application_data if 'Offer' in str(app.get('status', ''))])
        
        response_rate = (responses / total_applications * 100) if total_applications > 0 else 0
        interview_rate = (interviews / total_applications * 100) if total_applications > 0 else 0
        offer_rate = (offers / total_applications * 100) if total_applications > 0 else 0
        
        return {
            'total_applications': total_applications,
            'response_rate': response_rate,
            'interview_rate': interview_rate,
            'offer_rate': offer_rate,
            'responses': responses,
            'interviews': interviews,
            'offers': offers
        } 