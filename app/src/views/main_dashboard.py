"""
Main dashboard view for Job Tracker
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import re
import numpy as np

from core.base_tracker import BaseJobTracker
from utils.ui_components import UIComponents
from utils.data_loader import DataLoader
from components.enhanced_insights import EnhancedInsights

class MainDashboardView(BaseJobTracker):
    def __init__(self):
        super().__init__()
        self.ui = UIComponents()
        self.data_loader = DataLoader(self.db_manager)
        self.enhanced_insights = EnhancedInsights(self.db_manager)
        
    def _parse_salary(self, salary_str):
        """Parse salary string to extract numeric value"""
        if pd.isna(salary_str):
            return None
            
        # Extract numeric values (including decimals)
        numbers = re.findall(r'[\d.,]+', str(salary_str))
        if not numbers:
            return None
            
        # Take the first number found
        salary_num = numbers[0].replace('.', '').replace(',', '.')
        try:
            return float(salary_num)
        except ValueError:
            return None
    
    def _calculate_application_metrics(self, applications_df):
        """Calculate application success metrics"""
        if applications_df.empty:
            return {}
            
        total_applications = len(applications_df)
        
        # Status distribution
        status_counts = applications_df['status'].value_counts()
        
        # Success rate (interviews + offers)
        success_statuses = ['interview', 'offer', 'accepted']
        successful = len(applications_df[applications_df['status'].isin(success_statuses)])
        success_rate = (successful / total_applications * 100) if total_applications > 0 else 0
        
        # Response rate (any response beyond saved)
        response_statuses = ['applied', 'interview', 'offer', 'accepted', 'rejected']
        responses = len(applications_df[applications_df['status'].isin(response_statuses)])
        response_rate = (responses / total_applications * 100) if total_applications > 0 else 0
        
        # Average time to response (if we have dates)
        avg_days_to_response = None
        if ('applied_date' in applications_df.columns and 
            'status_date' in applications_df.columns):
            try:
                applications_df['applied_date'] = pd.to_datetime(applications_df['applied_date'], errors='coerce')
                applications_df['status_date'] = pd.to_datetime(applications_df['status_date'], errors='coerce')
                
                # Calculate days to first response
                applications_df['days_to_response'] = (
                    applications_df['status_date'] - applications_df['applied_date']
                ).dt.days
                
                avg_days_to_response = applications_df['days_to_response'].mean()
            except Exception:
                avg_days_to_response = None
            
        return {
            'total_applications': total_applications,
            'status_counts': status_counts,
            'success_rate': success_rate,
            'response_rate': response_rate,
            'avg_days_to_response': avg_days_to_response
        }
    
    def _analyze_salary_trends(self, df):
        """Analyze salary trends over time"""
        if df.empty or 'parsed_salary' not in df.columns:
            return None
            
        # Remove outliers (top and bottom 5%)
        salary_data = df[df['parsed_salary'].notna()]['parsed_salary']
        if len(salary_data) < 10:
            return None
            
        q05 = salary_data.quantile(0.05)
        q95 = salary_data.quantile(0.95)
        filtered_salary = salary_data[(salary_data >= q05) & (salary_data <= q95)]
        
        # Group by month and calculate statistics
        df['month'] = df['scraped_date'].dt.to_period('M')
        monthly_stats = df[df['parsed_salary'].notna()].groupby('month').agg({
            'parsed_salary': ['mean', 'median', 'count']
        }).reset_index()
        
        monthly_stats.columns = ['month', 'avg_salary', 'median_salary', 'job_count']
        monthly_stats['month'] = monthly_stats['month'].astype(str)
        
        return monthly_stats
    
    def _analyze_company_insights(self, df):
        """Analyze company-related insights"""
        if df.empty:
            return None
            
        # Company frequency analysis
        company_counts = df['company'].value_counts()
        
        # Companies with highest average salary
        company_salary = df[df['parsed_salary'].notna()].groupby('company').agg({
            'parsed_salary': ['mean', 'count']
        }).reset_index()
        company_salary.columns = ['company', 'avg_salary', 'job_count']
        company_salary = company_salary[company_salary['job_count'] >= 2]  # At least 2 jobs
        top_paying_companies = company_salary.nlargest(10, 'avg_salary')
        
        # Company size analysis (based on job posting frequency)
        company_size_categories = pd.cut(
            company_counts.values, 
            bins=[0, 1, 5, 20, float('inf')], 
            labels=['Small (1 job)', 'Medium (2-5 jobs)', 'Large (6-20 jobs)', 'Very Large (20+ jobs)']
        )
        company_size_dist = pd.Series(company_size_categories).value_counts()
        
        return {
            'top_companies': company_counts.head(10),
            'top_paying_companies': top_paying_companies,
            'company_size_distribution': company_size_dist
        }
    
    def _analyze_location_insights(self, df):
        """Analyze location-related insights"""
        if df.empty:
            return None
            
        # Location frequency
        location_counts = df['location'].value_counts()
        
        # Salary by location
        location_salary = df[df['parsed_salary'].notna()].groupby('location').agg({
            'parsed_salary': ['mean', 'count']
        }).reset_index()
        location_salary.columns = ['location', 'avg_salary', 'job_count']
        location_salary = location_salary[location_salary['job_count'] >= 3]  # At least 3 jobs
        top_paying_locations = location_salary.nlargest(10, 'avg_salary')
        
        # Remote work analysis (simplified without regex)
        remote_keywords = ['remote', 'home', 'hybrid', 'flexible']
        try:
            df['is_remote'] = df['description'].str.lower().str.contains('|'.join(remote_keywords), na=False)
            remote_stats = df['is_remote'].value_counts()
        except Exception:
            # Fallback: check each keyword separately
            df['is_remote'] = False
            for keyword in remote_keywords:
                try:
                    df['is_remote'] = df['is_remote'] | df['description'].str.lower().str.contains(keyword, na=False)
                except Exception:
                    continue
            remote_stats = df['is_remote'].value_counts()
        
        return {
            'top_locations': location_counts.head(10),
            'top_paying_locations': top_paying_locations,
            'remote_work_stats': remote_stats
        }
    
    def _analyze_skill_trends(self, df):
        """Analyze skill and technology trends"""
        if df.empty:
            return None
            
        # Common skills/technologies (simplified without regex)
        skill_keywords = [
            'python', 'java', 'javascript', 'react', 'angular', 'vue', 'node.js', 'sql',
            'aws', 'azure', 'docker', 'kubernetes', 'machine learning', 'ai', 'data science',
            'agile', 'scrum', 'git', 'jenkins', 'microservices', 'api', 'rest'
        ]
        
        skill_counts = {}
        for skill in skill_keywords:
            try:
                count = df['description'].str.lower().str.contains(skill, na=False).sum()
                if count > 0:
                    skill_counts[skill.title()] = count
            except Exception:
                continue
        
        # Sort by frequency
        skill_counts = dict(sorted(skill_counts.items(), key=lambda x: x[1], reverse=True))
        
        return skill_counts
    
    def show(self):
        """Show main dashboard with analytics"""
        self.ui.show_header("Job Tracker Dashboard")
        
        # Add dashboard mode selector
        st.markdown("### 🎛️ Dashboard Mode")
        dashboard_mode = st.selectbox(
            "Choose Dashboard View",
            ["📊 Standard Dashboard", "🔍 Analytics", "📈 Comprehensive Insights"],
            help="Select the level of detail for your dashboard"
        )
        
        # Get data date range
        try:
            date_info = self.data_loader.get_data_date_range()
        except Exception:
            date_info = None
        
        # Date range selector
        st.markdown("### 📅 Data Filter")
        
        # Get available date range from data
        earliest_date = None
        latest_date = None
        
        if date_info:
            all_dates = []
            
            if 'email_range' in date_info:
                email_range = date_info['email_range']
                if email_range['earliest']:
                    all_dates.append(pd.to_datetime(email_range['earliest']).replace(tzinfo=None))
                if email_range['latest']:
                    all_dates.append(pd.to_datetime(email_range['latest']).replace(tzinfo=None))
                    
            if 'job_range' in date_info:
                job_range = date_info['job_range']
                if job_range['earliest']:
                    all_dates.append(pd.to_datetime(job_range['earliest']).replace(tzinfo=None))
                if job_range['latest']:
                    all_dates.append(pd.to_datetime(job_range['latest']).replace(tzinfo=None))
            
            if all_dates:
                earliest_date = min(all_dates)
                latest_date = max(all_dates)
        
        # Default to last 30 days if no data range
        if not earliest_date:
            earliest_date = datetime.now() - timedelta(days=30)
        if not latest_date:
            latest_date = datetime.now()
            
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "Start Date",
                value=earliest_date.date(),
                min_value=earliest_date.date(),
                max_value=latest_date.date()
            )
        with col2:
            end_date = st.date_input(
                "End Date",
                value=latest_date.date(),
                min_value=earliest_date.date(),
                max_value=latest_date.date()
            )
            
        # Load and filter data
        df = self.data_loader.load_job_data()
        applications_df = self.data_loader.load_applications_data()
        
        if not df.empty:
            # Convert dates
            df['scraped_date'] = pd.to_datetime(df['scraped_date'])
            
            # Parse salaries
            df['parsed_salary'] = df['salary'].apply(self._parse_salary)
            
            # Filter by date range
            mask = (df['scraped_date'].dt.date >= start_date) & (df['scraped_date'].dt.date <= end_date)
            filtered_df = df[mask]
            
            # Show different dashboard modes
            if dashboard_mode == "📊 Standard Dashboard":
                self._show_standard_dashboard(filtered_df, applications_df)
            elif dashboard_mode == "🔍 Analytics":
                self._show_enhanced_dashboard(filtered_df, applications_df)
            else:  # Comprehensive Insights
                self._show_comprehensive_dashboard(filtered_df, applications_df)
        else:
            st.info("No job data available for the selected date range.")
    
    def _show_standard_dashboard(self, filtered_df, applications_df):
        """Show standard dashboard view"""
        # Show metrics
        st.markdown("### 📊 Key Metrics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_jobs = len(filtered_df)
            self.ui.show_metric_card("Total Jobs Found", total_jobs)
            
        with col2:
            unique_companies = filtered_df['company'].nunique()
            self.ui.show_metric_card("Unique Companies", unique_companies)
            
        with col3:
            if not applications_df.empty:
                active = len(applications_df[applications_df['status'].isin(['saved', 'applied', 'interview'])])
                self.ui.show_metric_card("Active Applications", active)
            
        with col4:
            avg_salary = filtered_df['parsed_salary'].mean()
            if pd.notna(avg_salary):
                self.ui.show_metric_card("Average Salary", f"€{avg_salary:,.0f}")
        
        # Application Success Insights
        if not applications_df.empty:
            st.markdown("### 🎯 Application Success Insights")
            
            app_metrics = self._calculate_application_metrics(applications_df)
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                self.ui.show_metric_card("Total Applications", app_metrics['total_applications'])
                
            with col2:
                self.ui.show_metric_card("Success Rate", f"{app_metrics['success_rate']:.1f}%")
                
            with col3:
                self.ui.show_metric_card("Response Rate", f"{app_metrics['response_rate']:.1f}%")
                
            with col4:
                if app_metrics['avg_days_to_response']:
                    self.ui.show_metric_card("Avg Days to Response", f"{app_metrics['avg_days_to_response']:.1f}")
            
            # Application status distribution
            if not app_metrics['status_counts'].empty:
                fig = px.pie(
                    values=app_metrics['status_counts'].values,
                    names=app_metrics['status_counts'].index,
                    title="Application Status Distribution"
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # Basic visualizations
        st.markdown("### 📈 Basic Trends")
        
        # Jobs over time
        jobs_over_time = filtered_df.groupby(filtered_df['scraped_date'].dt.date).size().reset_index()
        jobs_over_time.columns = ['date', 'count']
        
        fig = px.line(
            jobs_over_time,
            x='date',
            y='count',
            title='Jobs Posted Over Time'
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Top companies
        top_companies = filtered_df['company'].value_counts().head(10)
        fig = px.bar(
            x=top_companies.values,
            y=top_companies.index,
            title='Top Companies',
            orientation='h'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    def _show_enhanced_dashboard(self, filtered_df, applications_df):
        """Show enhanced dashboard view"""
        # Show standard metrics first
        self._show_standard_dashboard(filtered_df, applications_df)
        
        # Enhanced insights
        st.markdown("### 🔍 Insights")
        
        # Market Intelligence
        self.enhanced_insights.show_market_intelligence(filtered_df, applications_df)
        
        # Salary Benchmarking
        self.enhanced_insights.show_salary_benchmarking(filtered_df)
        
        # Competitive Analysis
        self.enhanced_insights.show_competitive_analysis(filtered_df)
        
        # Skill Demand Analysis
        self.enhanced_insights.show_skill_demand_analysis(filtered_df)
        
        # Application Performance (if available)
        if applications_df is not None and not applications_df.empty:
            self.enhanced_insights.show_application_performance_insights(applications_df)
    
    def _show_comprehensive_dashboard(self, filtered_df, applications_df):
        """Show comprehensive dashboard view"""
        # Use the comprehensive dashboard from EnhancedInsights
        self.enhanced_insights.show_comprehensive_dashboard(filtered_df, applications_df) 