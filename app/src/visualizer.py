import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from datetime import datetime, timedelta
import numpy as np
from typing import Dict, List
from wordcloud import WordCloud
import streamlit as st
from database_manager import get_db_manager

class JobTrackerVisualizer:
    """Creates comprehensive visualizations for job tracking data"""
    
    def __init__(self):
        self.db_manager = get_db_manager()
        self.email_data = self.get_email_data()
        self.job_data = self.get_job_data()
        self.applications_data = self.get_applications_data()
        
    def get_applications_data(self):
        """Fetch job applications data from PostgreSQL"""
        try:
            # Fetch all relevant columns for visualizations
            query = "SELECT status, added_date, applied_date, company FROM job_applications"
            result = self.db_manager.execute_query(query, fetch='all')
            
            if result:
                return pd.DataFrame(result, columns=['status', 'added_date', 'applied_date', 'company'])
            else:
                return pd.DataFrame(columns=['status', 'added_date', 'applied_date', 'company'])
        except Exception as e:
            st.error(f"Error loading applications data: {e}")
            return pd.DataFrame(columns=['status', 'added_date', 'applied_date', 'company'])
    
    def get_email_data(self):
        """Fetch email analysis data from PostgreSQL"""
        try:
            query = """
                SELECT date, category, company, subject 
                FROM email_analysis 
                ORDER BY date DESC
            """
            result = self.db_manager.execute_query(query, fetch='all')
            
            if result:
                return pd.DataFrame(result, columns=['date', 'category', 'company', 'subject'])
            else:
                return pd.DataFrame(columns=['date', 'category', 'company', 'subject'])
        except Exception as e:
            st.error(f"Error loading email data: {e}")
            return pd.DataFrame(columns=['date', 'category', 'company', 'subject'])
    
    def get_job_data(self):
        """Fetch job listings data from PostgreSQL"""
        try:
            query = """
                SELECT title, company, location, salary, source, scraped_date 
                FROM job_listings 
                ORDER BY scraped_date DESC
            """
            result = self.db_manager.execute_query(query, fetch='all')
            
            if result:
                return pd.DataFrame(result, columns=['title', 'company', 'location', 'salary', 'source', 'scraped_date'])
            else:
                return pd.DataFrame(columns=['title', 'company', 'location', 'salary', 'source', 'scraped_date'])
        except Exception as e:
            st.error(f"Error loading job data: {e}")
            return pd.DataFrame(columns=['title', 'company', 'location', 'salary', 'source', 'scraped_date'])
    
    def get_llm_email_grouper(self):
        """Return the best available LLM-powered email grouping function."""
        try:
            from gmail_analyzer import OptimizedGmailJobAnalyzer
            analyzer = OptimizedGmailJobAnalyzer(auth_only=True)
            if hasattr(analyzer, 'group_emails_by_application_llm'):
                return analyzer.group_emails_by_application_llm
        except Exception as e:
            print(f"Could not use Gmail LLM analyzer: {e}")
        try:
            from ai_email_analyzer import AIEmailAnalyzer
            analyzer = AIEmailAnalyzer()
            if hasattr(analyzer, 'group_emails_by_application'):
                return analyzer.group_emails_by_application
        except Exception as e:
            print(f"Could not use AIEmailAnalyzer: {e}")
        return None

    def create_applications_timeline(self) -> go.Figure:
        """Create timeline visualization of job applications from email analysis using LLM grouping"""
        if self.email_data.empty:
            return go.Figure().add_annotation(text="No email data available for timeline", 
                                            xref="paper", yref="paper", x=0.5, y=0.5)
        
        # Use LLM grouping if available
        llm_grouper = self.get_llm_email_grouper()
        if llm_grouper:
            grouped_applications = llm_grouper(self.email_data)
            # Create timeline data from grouped applications
            timeline_data = []
            for app_id, app_emails in grouped_applications.items():
                if isinstance(app_emails, list):
                    app_df = pd.DataFrame(app_emails)
                else:
                    app_df = app_emails
                if not app_df.empty:
                    app_df['date'] = pd.to_datetime(app_df['date'])
                    # Group by week and category for this application
                    if app_df['date'].dt.tz is not None:
                        app_df['week'] = app_df['date'].dt.tz_localize(None).dt.to_period('W')
                    else:
                        app_df['week'] = app_df['date'].dt.to_period('W')
                    weekly_counts = app_df.groupby(['week', 'category']).size().unstack(fill_value=0)
                    for week in weekly_counts.index:
                        for category in weekly_counts.columns:
                            if weekly_counts.loc[week, category] > 0:
                                timeline_data.append({
                                    'week': week,
                                    'category': category,
                                    'count': weekly_counts.loc[week, category],
                                    'application_id': app_id
                                })
            
            if timeline_data:
                timeline_df = pd.DataFrame(timeline_data)
                weekly_counts = timeline_df.groupby(['week', 'category'])['count'].sum().unstack(fill_value=0)
            else:
                # Fallback to original method
                emails_df = self.email_data.copy()
                emails_df['date'] = pd.to_datetime(emails_df['date'])
                if emails_df['date'].dt.tz is not None:
                    emails_df['week'] = emails_df['date'].dt.tz_localize(None).dt.to_period('W')
                else:
                    emails_df['week'] = emails_df['date'].dt.to_period('W')
                weekly_counts = emails_df.groupby(['week', 'category']).size().unstack(fill_value=0)
        else:
            # Fallback to original method
            emails_df = self.email_data.copy()
            emails_df['date'] = pd.to_datetime(emails_df['date'])
            if emails_df['date'].dt.tz is not None:
                emails_df['week'] = emails_df['date'].dt.tz_localize(None).dt.to_period('W')
            else:
                emails_df['week'] = emails_df['date'].dt.to_period('W')
            weekly_counts = emails_df.groupby(['week', 'category']).size().unstack(fill_value=0)
        
        fig = go.Figure()
        
        colors = {
            'application_confirmation': '#1f77b4',
            'interview_invitation': '#2ca02c', 
            'rejection': '#d62728',
            'job_offer': '#ff7f0e',
            'job_alert': '#9467bd',
            'other': '#8c564b'
        }
        
        for category in weekly_counts.columns:
            fig.add_trace(go.Scatter(
                x=weekly_counts.index.astype(str),
                y=weekly_counts[category],
                mode='lines+markers',
                name=category.replace('_', ' ').title(),
                line=dict(color=colors.get(category, '#7f7f7f'), width=3),
                marker=dict(size=8),
                stackgroup='one'
            ))
        
        title = "Job Application Activity Timeline (LLM-Grouped)" if llm_grouper else "Job Application Activity Timeline (from Email Analysis)"
        fig.update_layout(
            title=title,
            xaxis_title="Week",
            yaxis_title="Number of Emails",
            hovermode='x unified',
            template='plotly_white',
            height=500,
            legend_title_text='Email Category'
        )
        
        return fig
    
    def create_application_funnel(self) -> go.Figure:
        """Create funnel chart showing application conversion rates from email analysis using LLM grouping"""
        if self.email_data.empty:
            return go.Figure().add_annotation(text="No email data available", 
                                            xref="paper", yref="paper", x=0.5, y=0.5)
        
        # Use LLM grouping if available
        llm_grouper = self.get_llm_email_grouper()
        if llm_grouper:
            grouped_applications = llm_grouper(self.email_data)
            # Count applications, interviews, rejections, and offers from grouped data
            applications = 0
            interviews = 0
            rejections = 0
            offers = 0
            
            for app_id, app_emails in grouped_applications.items():
                if isinstance(app_emails, list):
                    app_df = pd.DataFrame(app_emails)
                else:
                    app_df = app_emails
                if not app_df.empty:
                    categories = app_df['category'].value_counts()
                    if 'application_confirmation' in categories:
                        applications += 1
                    if 'interview_invitation' in categories:
                        interviews += 1
                    if 'rejection' in categories:
                        rejections += 1
                    if 'job_offer' in categories:
                        offers += 1
                    # Check for offers in 'other' category
                    other_emails = app_df[app_df['category'] == 'other']
                    if not other_emails.empty:
                        job_offer_keywords = ['offer', 'congratulations', 'pleased to offer', 'job offer', 'offer letter']
                        offer_mask = other_emails['subject'].str.contains('|'.join(job_offer_keywords), case=False, na=False)
                        if offer_mask.any():
                            offers += 1
        else:
            # Fallback to original method
            category_counts = self.email_data['category'].value_counts()
            applications = category_counts.get('application_confirmation', 0)
            interviews = category_counts.get('interview_invitation', 0)
            rejections = category_counts.get('rejection', 0)
            direct_offers = len(self.email_data[self.email_data['category'] == 'job_offer'])
            other_emails = self.email_data[self.email_data['category'] == 'other']
            job_offer_keywords = ['offer', 'congratulations', 'pleased to offer', 'job offer', 'offer letter']
            keyword_offers = 0
            if not other_emails.empty:
                offer_mask = other_emails['subject'].str.contains('|'.join(job_offer_keywords), case=False, na=False)
                offer_emails = other_emails[offer_mask]
                if not offer_emails.empty:
                    keyword_offers = offer_emails['company'].nunique()
            offers = direct_offers + keyword_offers
        
        if applications == 0:
            return go.Figure().add_annotation(text="No application confirmations found to build a funnel", 
                                            xref="paper", yref="paper", x=0.5, y=0.5)
        
        title = "Job Application Funnel (LLM-Grouped)" if llm_grouper else "Job Application Funnel (from Email Analysis)"
        fig = go.Figure(go.Funnel(
            y=["Applications Sent", "Interviews Scheduled", "Rejections Received", "Job Offers Received"],
            x=[applications, interviews, rejections, offers],
            textinfo="value+percent initial",
            marker=dict(color=["#1f77b4", "#2ca02c", "#d62728", "#ff7f0e"])
        ))
        
        fig.update_layout(
            title=title,
            height=500,
            template='plotly_white'
        )
        
        return fig
    
    def create_company_analysis(self) -> go.Figure:
        """Create analysis of companies applied to using LLM grouping"""
        if self.email_data.empty:
            return go.Figure().add_annotation(text="No email data available", 
                                            xref="paper", yref="paper", x=0.5, y=0.5)
        
        # Use LLM grouping if available
        llm_grouper = self.get_llm_email_grouper()
        if llm_grouper:
            grouped_applications = llm_grouper(self.email_data)
            # Count applications per company from grouped data
            company_counts = {}
            for app_id, app_emails in grouped_applications.items():
                if isinstance(app_emails, list):
                    app_df = pd.DataFrame(app_emails)
                else:
                    app_df = app_emails
                if not app_df.empty:
                    company = app_df.iloc[0].get('company', app_id)
                    if company not in company_counts:
                        company_counts[company] = 0
                    company_counts[company] += 1
            
            if company_counts:
                company_counts = pd.Series(company_counts).sort_values(ascending=False).head(15)
            else:
                company_counts = pd.Series()
        else:
            # Fallback to original method
            company_counts = self.email_data['company'].value_counts().head(15)
        
        if company_counts.empty:
            return go.Figure().add_annotation(text="No company data found", 
                                            xref="paper", yref="paper", x=0.5, y=0.5)
        
        title = "Top Companies by Application Count (LLM-Grouped)" if llm_grouper else "Top Companies by Application Count"
        fig = go.Figure(data=[
            go.Bar(x=company_counts.values, y=company_counts.index, orientation='h',
                  marker_color='#3498DB')
        ])
        
        fig.update_layout(
            title=title,
            xaxis_title="Number of Applications",
            yaxis_title="Company",
            height=600,
            template='plotly_white'
        )
        
        return fig
    
    def create_monthly_summary(self) -> go.Figure:
        """Create monthly summary dashboard"""
        if self.email_data.empty:
            return go.Figure().add_annotation(text="No email data available", 
                                            xref="paper", yref="paper", x=0.5, y=0.5)
        
        # Group by month
        # Convert to timezone-naive before creating periods to avoid warnings
        email_data_clean = self.email_data.copy()
        if email_data_clean['date'].dt.tz is not None:
            email_data_clean['date'] = email_data_clean['date'].dt.tz_localize(None)
        monthly_data = email_data_clean.groupby([
            email_data_clean['date'].dt.to_period('M'), 
            'category'
        ]).size().unstack(fill_value=0)
        
        if monthly_data.empty:
            return go.Figure().add_annotation(text="No monthly data available", 
                                            xref="paper", yref="paper", x=0.5, y=0.5)
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Applications by Month', 'Category Distribution', 
                          'Success Rate', 'Response Time'),
            specs=[[{"type": "scatter"}, {"type": "pie"}],
                   [{"type": "bar"}, {"type": "scatter"}]]
        )
        
        # Applications by month
        if 'application_confirmation' in monthly_data.columns:
            fig.add_trace(
                go.Scatter(x=monthly_data.index.astype(str), 
                          y=monthly_data['application_confirmation'],
                          mode='lines+markers', name='Applications'),
                row=1, col=1
            )
        
        # Category distribution
        category_counts = self.email_data['category'].value_counts()
        fig.add_trace(
            go.Pie(labels=category_counts.index, values=category_counts.values,
                  name="Categories"),
            row=1, col=2
        )
        
        # Success rate calculation
        if len(monthly_data.columns) > 0:
            success_rate = []
            months = []
            
            job_offer_keywords = [
                'offer', 'congratulations', 'pleased to offer', 'job offer', 'offer letter', 
                'we are pleased', 'happy to offer', 'welcome to', 'join us', 'orientation',
                'start date', 'onboarding', 'welcome aboard', 'you got the job', 'hired',
                'your offer', 'offer accepted', 'contract'
            ]
            
            for month in monthly_data.index:
                apps = monthly_data.loc[month, 'application_confirmation'] if 'application_confirmation' in monthly_data.columns else 0
                
                # Count direct job offers
                direct_offers = monthly_data.loc[month, 'job_offer'] if 'job_offer' in monthly_data.columns else 0
                
                # Count keyword-based offers from 'other' category emails for this month
                keyword_offers = 0
                if 'other' in monthly_data.columns and monthly_data.loc[month, 'other'] > 0:
                    # Get 'other' category emails for this month
                    month_emails = email_data_clean[
                        (email_data_clean['date'].dt.to_period('M') == month) & 
                        (email_data_clean['category'] == 'other')
                    ]
                    
                    if not month_emails.empty:
                        # Find emails that match offer keywords
                        offer_mask = month_emails['subject'].str.contains('|'.join(job_offer_keywords), case=False, na=False)
                        offer_emails = month_emails[offer_mask]
                        
                        # Filter out emails from your own domain (replies) and non-offer companies
                        if not offer_emails.empty:
                            excluded_patterns = 'aznh7|gmail|yahoo|hotmail|outlook|docusign|eumail'
                            company_offers = offer_emails[~offer_emails['company'].str.contains(excluded_patterns, case=False, na=False)]
                            
                            # Normalize company names and count unique offers
                            if not company_offers.empty:
                                def normalize_company_name(company_name):
                                    if pd.isna(company_name):
                                        return company_name
                                    if 'flink' in company_name.lower():
                                        return 'Flink'
                                    if 'trade' in company_name.lower() and 'republic' in company_name.lower():
                                        return 'Trade Republic'
                                    import re
                                    normalized = re.sub(r'^(your\s+offer\s+to\s+join\s+the\s+|congratulations\s+on\s+joining\s+the\s+)', '', company_name, flags=re.IGNORECASE)
                                    normalized = re.sub(r'\s+(team|group|company)$', '', normalized, flags=re.IGNORECASE)
                                    return normalized.strip().title()
                                
                                company_offers = company_offers.copy()
                                company_offers['normalized_company'] = company_offers['company'].apply(normalize_company_name)
                                keyword_offers = company_offers['normalized_company'].nunique()
                
                total_offers = direct_offers + keyword_offers
                rate = (total_offers / apps * 100) if apps > 0 else 0
                success_rate.append(rate)
                months.append(str(month))
            
            fig.add_trace(
                go.Bar(x=months, y=success_rate, name='Success Rate %'),
                row=2, col=1
            )
        
        fig.update_layout(height=800, title_text="Monthly Job Application Summary")
        
        return fig
    
    def create_job_market_analysis(self) -> go.Figure:
        """Analyze available job market"""
        if self.job_data.empty:
            return go.Figure().add_annotation(text="No job market data available", 
                                            xref="paper", yref="paper", x=0.5, y=0.5)
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Jobs by Source', 'Top Companies Hiring', 
                          'Location Distribution', 'Jobs Over Time'),
            specs=[[{"type": "pie"}, {"type": "bar"}],
                   [{"type": "bar"}, {"type": "scatter"}]]
        )
        
        # Jobs by source
        source_counts = self.job_data['source'].value_counts()
        fig.add_trace(
            go.Pie(labels=source_counts.index, values=source_counts.values,
                  name="Job Sources"),
            row=1, col=1
        )
        
        # Top companies hiring
        company_counts = self.job_data['company'].value_counts().head(10)
        fig.add_trace(
            go.Bar(x=company_counts.index, y=company_counts.values,
                  name="Companies"),
            row=1, col=2
        )
        
        # Location distribution
        location_counts = self.job_data['location'].value_counts().head(10)
        fig.add_trace(
            go.Bar(x=location_counts.index, y=location_counts.values,
                  name="Locations"),
            row=2, col=1
        )
        
        # Jobs over time
        daily_jobs = self.job_data.groupby(self.job_data['scraped_date'].dt.date).size()
        fig.add_trace(
            go.Scatter(x=daily_jobs.index, y=daily_jobs.values,
                      mode='lines+markers', name='Jobs Found'),
            row=2, col=2
        )
        
        fig.update_layout(height=800, title_text="Job Market Analysis")
        
        return fig
    
    def create_skills_wordcloud(self) -> None:
        """Create word cloud from job descriptions"""
        if self.job_data.empty or 'title' not in self.job_data.columns:
            return None
        
        # Combine all job titles and descriptions
        text = ' '.join(self.job_data['title'].fillna(''))
        
        if not text.strip():
            return None
        
        # Generate word cloud
        wordcloud = WordCloud(
            width=800, height=400, 
            background_color='white',
            colormap='viridis'
        ).generate(text)
        
        # Save to file
        plt.figure(figsize=(10, 5))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off')
        plt.title('Job Market Skills & Keywords')
        plt.tight_layout()
        plt.savefig('visualizations/skills_wordcloud.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def generate_summary_stats(self) -> Dict:
        """Generate summary statistics"""
        stats = {}
        
        if not self.email_data.empty:
            stats['total_applications'] = len(self.email_data[self.email_data['category'] == 'application_confirmation'])
            stats['interviews'] = len(self.email_data[self.email_data['category'] == 'interview_invitation'])
            stats['rejections'] = len(self.email_data[self.email_data['category'] == 'rejection'])
            
            # Look for job offers in both 'job_offer' category and 'other' category with offer keywords
            direct_offers_data = self.email_data[self.email_data['category'] == 'job_offer']
            
            # Check 'other' category emails for job offer keywords
            other_emails = self.email_data[self.email_data['category'] == 'other']
            job_offer_keywords = [
                'offer', 'congratulations', 'pleased to offer', 'job offer', 'offer letter', 
                'we are pleased', 'happy to offer', 'welcome to', 'join us', 'orientation',
                'start date', 'onboarding', 'welcome aboard', 'you got the job', 'hired',
                'your offer', 'offer accepted', 'contract'
            ]
            
            offer_emails = pd.DataFrame()
            if not other_emails.empty:
                # Find emails that match offer keywords
                offer_mask = other_emails['subject'].str.contains('|'.join(job_offer_keywords), case=False, na=False)
                offer_emails = other_emails[offer_mask]
            
            # Combine both sources
            all_offers = pd.concat([direct_offers_data, offer_emails]).drop_duplicates()
            
            # Filter out emails from your own domain (replies) and non-offer companies
            excluded_patterns = 'aznh7|gmail|yahoo|hotmail|outlook|docusign|eumail'
            company_offers = all_offers[~all_offers['company'].str.contains(excluded_patterns, case=False, na=False)]
            
            # Normalize company names for better grouping
            def normalize_company_name(company_name):
                if pd.isna(company_name):
                    return company_name
                
                # Normalize Flink variations
                if 'flink' in company_name.lower():
                    return 'Flink'
                
                # Normalize Trade Republic variations  
                if 'trade' in company_name.lower() and 'republic' in company_name.lower():
                    return 'Trade Republic'
                    
                # Remove common prefixes/suffixes that don't affect company identity
                import re
                normalized = re.sub(r'^(your\s+offer\s+to\s+join\s+the\s+|congratulations\s+on\s+joining\s+the\s+)', '', company_name, flags=re.IGNORECASE)
                normalized = re.sub(r'\s+(team|group|company)$', '', normalized, flags=re.IGNORECASE)
                
                return normalized.strip().title()
            
            if not company_offers.empty:
                company_offers = company_offers.copy()
                company_offers['normalized_company'] = company_offers['company'].apply(normalize_company_name)
                stats['offers'] = company_offers['normalized_company'].nunique()
            else:
                stats['offers'] = 0
            
            # Calculate rates
            total_apps = max(stats['total_applications'], 1)  # Avoid division by zero
            stats['response_rate'] = (stats['interviews'] + stats['offers'] + stats['rejections']) / total_apps * 100
            stats['success_rate'] = stats['offers'] / total_apps * 100
        else:
            stats['total_applications'] = 0
            stats['interviews'] = 0
            stats['offers'] = 0
            stats['rejections'] = 0
            stats['response_rate'] = 0
            stats['success_rate'] = 0
        
        if not self.job_data.empty:
            stats['available_jobs'] = len(self.job_data)
            stats['unique_companies'] = self.job_data['company'].nunique()
            stats['job_sources'] = self.job_data['source'].nunique()
        else:
            stats['available_jobs'] = 0
            stats['unique_companies'] = 0
            stats['job_sources'] = 0
        
        return stats
    
    def save_all_visualizations(self):
        """Save all visualizations to files"""
        print("Generating visualizations...")
        
        # Create timeline
        timeline_fig = self.create_applications_timeline()
        timeline_fig.write_html("visualizations/applications_timeline.html")
        
        # Create funnel
        funnel_fig = self.create_application_funnel()
        funnel_fig.write_html("visualizations/application_funnel.html")
        
        # Create company analysis
        company_fig = self.create_company_analysis()
        company_fig.write_html("visualizations/company_analysis.html")
        
        # Create monthly summary
        monthly_fig = self.create_monthly_summary()
        monthly_fig.write_html("visualizations/monthly_summary.html")
        
        # Create job market analysis
        market_fig = self.create_job_market_analysis()
        market_fig.write_html("visualizations/job_market_analysis.html")
        
        # Create word cloud
        self.create_skills_wordcloud()
        
        print("All visualizations saved to 'visualizations/' directory")

    # ===== FILTERED VISUALIZATION METHODS =====
    
    def get_filtered_email_data(self, start_date, end_date):
        """Get email data filtered by date range"""
        try:
            query = """
                SELECT date, category, company, subject 
                FROM email_analysis 
                WHERE date >= %s AND date <= %s
                ORDER BY date DESC
            """
            result = self.db_manager.execute_query(query, (start_date, end_date), fetch='all')
            
            if result:
                return pd.DataFrame(result, columns=['date', 'category', 'company', 'subject'])
            else:
                return pd.DataFrame(columns=['date', 'category', 'company', 'subject'])
        except Exception as e:
            return pd.DataFrame(columns=['date', 'category', 'company', 'subject'])
    
    def get_filtered_job_data(self, start_date, end_date):
        """Get job data filtered by date range"""
        try:
            query = """
                SELECT title, company, location, salary, source, scraped_date 
                FROM job_listings 
                WHERE scraped_date >= %s AND scraped_date <= %s
                ORDER BY scraped_date DESC
            """
            result = self.db_manager.execute_query(query, (start_date, end_date), fetch='all')
            
            if result:
                return pd.DataFrame(result, columns=['title', 'company', 'location', 'salary', 'source', 'scraped_date'])
            else:
                return pd.DataFrame(columns=['title', 'company', 'location', 'salary', 'source', 'scraped_date'])
        except Exception as e:
            return pd.DataFrame(columns=['title', 'company', 'location', 'salary', 'source', 'scraped_date'])
    
    def create_applications_timeline_filtered(self, start_date, end_date) -> go.Figure:
        """Create timeline visualization filtered by date range using LLM grouping"""
        filtered_email_data = self.get_filtered_email_data(start_date, end_date)
        
        if filtered_email_data.empty:
            return go.Figure().add_annotation(
                text=f"No email data available for {start_date} to {end_date}", 
                xref="paper", yref="paper", x=0.5, y=0.5
            )
        
        # Use LLM grouping if available
        llm_grouper = self.get_llm_email_grouper()
        if llm_grouper:
            grouped_applications = llm_grouper(filtered_email_data)
            # Create timeline data from grouped applications
            timeline_data = []
            for app_id, app_emails in grouped_applications.items():
                if isinstance(app_emails, list):
                    app_df = pd.DataFrame(app_emails)
                else:
                    app_df = app_emails
                if not app_df.empty:
                    app_df['date'] = pd.to_datetime(app_df['date'])
                    # Group by week and category for this application
                    if app_df['date'].dt.tz is not None:
                        app_df['week'] = app_df['date'].dt.tz_localize(None).dt.to_period('W')
                    else:
                        app_df['week'] = app_df['date'].dt.to_period('W')
                    weekly_counts = app_df.groupby(['week', 'category']).size().unstack(fill_value=0)
                    for week in weekly_counts.index:
                        for category in weekly_counts.columns:
                            if weekly_counts.loc[week, category] > 0:
                                timeline_data.append({
                                    'week': week,
                                    'category': category,
                                    'count': weekly_counts.loc[week, category],
                                    'application_id': app_id
                                })
            
            if timeline_data:
                timeline_df = pd.DataFrame(timeline_data)
                weekly_counts = timeline_df.groupby(['week', 'category'])['count'].sum().unstack(fill_value=0)
            else:
                # Fallback to original method
                emails_df = filtered_email_data.copy()
                emails_df['date'] = pd.to_datetime(emails_df['date'])
                if emails_df['date'].dt.tz is not None:
                    emails_df['week'] = emails_df['date'].dt.tz_localize(None).dt.to_period('W')
                else:
                    emails_df['week'] = emails_df['date'].dt.to_period('W')
                weekly_counts = emails_df.groupby(['week', 'category']).size().unstack(fill_value=0)
        else:
            # Fallback to original method
            emails_df = filtered_email_data.copy()
            emails_df['date'] = pd.to_datetime(emails_df['date'])
            if emails_df['date'].dt.tz is not None:
                emails_df['week'] = emails_df['date'].dt.tz_localize(None).dt.to_period('W')
            else:
                emails_df['week'] = emails_df['date'].dt.to_period('W')
            weekly_counts = emails_df.groupby(['week', 'category']).size().unstack(fill_value=0)
        
        fig = go.Figure()
        
        colors = {
            'application_confirmation': '#1f77b4',
            'interview_invitation': '#2ca02c', 
            'rejection': '#d62728',
            'job_offer': '#ff7f0e',
            'job_alert': '#9467bd',
            'other': '#8c564b'
        }
        
        for category in weekly_counts.columns:
            fig.add_trace(go.Scatter(
                x=weekly_counts.index.astype(str),
                y=weekly_counts[category],
                mode='lines+markers',
                name=category.replace('_', ' ').title(),
                line=dict(color=colors.get(category, '#7f7f7f'), width=3),
                marker=dict(size=8),
                stackgroup='one'
            ))
        
        title = f"Job Application Activity Timeline (LLM-Grouped) - {start_date} to {end_date}" if llm_grouper else f"Job Application Activity Timeline ({start_date} to {end_date})"
        fig.update_layout(
            title=title,
            xaxis_title="Week",
            yaxis_title="Number of Emails",
            hovermode='x unified',
            template='plotly_white',
            height=500,
            legend_title_text='Email Category'
        )
        
        return fig
    
    def create_application_funnel_filtered(self, start_date, end_date) -> go.Figure:
        """Create funnel chart filtered by date range using LLM grouping"""
        filtered_email_data = self.get_filtered_email_data(start_date, end_date)
        
        if filtered_email_data.empty:
            return go.Figure().add_annotation(
                text=f"No email data available for {start_date} to {end_date}", 
                xref="paper", yref="paper", x=0.5, y=0.5
            )
        
        # Use LLM grouping if available
        llm_grouper = self.get_llm_email_grouper()
        if llm_grouper:
            grouped_applications = llm_grouper(filtered_email_data)
            # Count applications, interviews, rejections, and offers from grouped data
            applications = 0
            interviews = 0
            rejections = 0
            offers = 0
            
            for app_id, app_emails in grouped_applications.items():
                if isinstance(app_emails, list):
                    app_df = pd.DataFrame(app_emails)
                else:
                    app_df = app_emails
                if not app_df.empty:
                    categories = app_df['category'].value_counts()
                    if 'application_confirmation' in categories:
                        applications += 1
                    if 'interview_invitation' in categories:
                        interviews += 1
                    if 'rejection' in categories:
                        rejections += 1
                    if 'job_offer' in categories:
                        offers += 1
                    # Check for offers in 'other' category
                    other_emails = app_df[app_df['category'] == 'other']
                    if not other_emails.empty:
                        job_offer_keywords = ['offer', 'congratulations', 'pleased to offer', 'job offer', 'offer letter']
                        offer_mask = other_emails['subject'].str.contains('|'.join(job_offer_keywords), case=False, na=False)
                        if offer_mask.any():
                            offers += 1
        else:
            # Fallback to original method
            category_counts = filtered_email_data['category'].value_counts()
            applications = category_counts.get('application_confirmation', 0)
            interviews = category_counts.get('interview_invitation', 0)
            rejections = category_counts.get('rejection', 0)
            direct_offers = len(filtered_email_data[filtered_email_data['category'] == 'job_offer'])
            other_emails = filtered_email_data[filtered_email_data['category'] == 'other']
            job_offer_keywords = ['offer', 'congratulations', 'pleased to offer', 'job offer', 'offer letter']
            keyword_offers = 0
            if not other_emails.empty:
                offer_mask = other_emails['subject'].str.contains('|'.join(job_offer_keywords), case=False, na=False)
                offer_emails = other_emails[offer_mask]
                
                if not offer_emails.empty:
                    keyword_offers = offer_emails['company'].nunique()
            offers = direct_offers + keyword_offers
        
        if applications == 0:
            return go.Figure().add_annotation(
                text=f"No application confirmations found for {start_date} to {end_date}", 
                xref="paper", yref="paper", x=0.5, y=0.5
            )
        
        title = f"Job Application Funnel (LLM-Grouped) - {start_date} to {end_date}" if llm_grouper else f"Job Application Funnel ({start_date} to {end_date})"
        fig = go.Figure(go.Funnel(
            y=["Applications Sent", "Interviews Scheduled", "Rejections Received", "Job Offers Received"],
            x=[applications, interviews, rejections, offers],
            textinfo="value+percent initial",
            marker=dict(color=["#1f77b4", "#2ca02c", "#d62728", "#ff7f0e"])
        ))
        
        fig.update_layout(
            title=title,
            height=500,
            template='plotly_white'
        )
        
        return fig
    
    def create_company_analysis_filtered(self, start_date, end_date) -> go.Figure:
        """Create analysis of companies applied to using LLM grouping, filtered by date range"""
        filtered_email_data = self.get_filtered_email_data(start_date, end_date)
        
        if filtered_email_data.empty:
            return go.Figure().add_annotation(
                text=f"No email data available for {start_date} to {end_date}", 
                xref="paper", yref="paper", x=0.5, y=0.5
            )
        
        # Use LLM grouping if available
        llm_grouper = self.get_llm_email_grouper()
        if llm_grouper:
            grouped_applications = llm_grouper(filtered_email_data)
            # Count applications per company from grouped data
            company_counts = {}
            for app_id, app_emails in grouped_applications.items():
                if isinstance(app_emails, list):
                    app_df = pd.DataFrame(app_emails)
                else:
                    app_df = app_emails
                if not app_df.empty:
                    company = app_df.iloc[0].get('company', app_id)
                    if company not in company_counts:
                        company_counts[company] = 0
                    company_counts[company] += 1
            
            if company_counts:
                company_counts = pd.Series(company_counts).sort_values(ascending=False).head(15)
            else:
                company_counts = pd.Series()
        else:
            # Fallback to original method
            company_counts = filtered_email_data['company'].value_counts().head(15)
        
        if company_counts.empty:
            return go.Figure().add_annotation(
                text=f"No company data found for {start_date} to {end_date}", 
                xref="paper", yref="paper", x=0.5, y=0.5
            )
        
        title = f"Top Companies by Application Count (LLM-Grouped) - {start_date} to {end_date}" if llm_grouper else f"Top Companies by Application Count ({start_date} to {end_date})"
        fig = go.Figure(data=[
            go.Bar(x=company_counts.values, y=company_counts.index, orientation='h',
                  marker_color='#3498DB')
        ])
        
        fig.update_layout(
            title=title,
            xaxis_title="Number of Applications",
            yaxis_title="Company",
            height=600,
            template='plotly_white'
        )
        
        return fig
    
    def create_monthly_summary_filtered(self, start_date, end_date) -> go.Figure:
        """Create monthly summary filtered by date range"""
        filtered_email_data = self.get_filtered_email_data(start_date, end_date)
        
        if filtered_email_data.empty:
            return go.Figure().add_annotation(
                text=f"No email data available for {start_date} to {end_date}", 
                xref="paper", yref="paper", x=0.5, y=0.5
            )
        
        # Process monthly data
        emails_df = filtered_email_data.copy()
        emails_df['date'] = pd.to_datetime(emails_df['date'])
        emails_df['month'] = emails_df['date'].dt.to_period('M')
        
        # Get monthly counts by category
        monthly_data = emails_df.groupby(['month', 'category']).size().unstack(fill_value=0)
        
        if monthly_data.empty:
            return go.Figure().add_annotation(
                text=f"No monthly data for {start_date} to {end_date}", 
                xref="paper", yref="paper", x=0.5, y=0.5
            )
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Monthly Applications', 'Response Rates', 'Success Rate Trend', 'Activity Heatmap'),
            specs=[[{"type": "bar"}, {"type": "scatter"}],
                   [{"type": "scatter"}, {"type": "bar"}]]
        )
        
        # Monthly applications
        applications = monthly_data.get('application_confirmation', pd.Series(0, index=monthly_data.index))
        fig.add_trace(
            go.Bar(x=applications.index.astype(str), y=applications.values, name="Applications", marker_color='#3498DB'),
            row=1, col=1
        )
        
        # Response rates
        interviews = monthly_data.get('interview_invitation', pd.Series(0, index=monthly_data.index))
        rejections = monthly_data.get('rejection', pd.Series(0, index=monthly_data.index))
        responses = interviews + rejections
        response_rate = (responses / applications.replace(0, 1) * 100).fillna(0)
        
        fig.add_trace(
            go.Scatter(x=response_rate.index.astype(str), y=response_rate.values, 
                      mode='lines+markers', name="Response Rate %", line=dict(color='#2ECC71')),
            row=1, col=2
        )
        
        # Success rate trend
        offers = monthly_data.get('job_offer', pd.Series(0, index=monthly_data.index))
        success_rate = (offers / applications.replace(0, 1) * 100).fillna(0)
        
        fig.add_trace(
            go.Scatter(x=success_rate.index.astype(str), y=success_rate.values,
                      mode='lines+markers', name="Success Rate %", line=dict(color='#E74C3C')),
            row=2, col=1
        )
        
        # Activity summary
        total_activity = monthly_data.sum(axis=1)
        fig.add_trace(
            go.Bar(x=total_activity.index.astype(str), y=total_activity.values, 
                  name="Total Activity", marker_color='#9B59B6'),
            row=2, col=2
        )
        
        fig.update_layout(
            height=800, 
            title_text=f"Monthly Job Search Summary ({start_date} to {end_date})",
            showlegend=False
        )
        
        return fig
    
    def create_job_market_analysis_filtered(self, start_date, end_date) -> go.Figure:
        """Create job market analysis filtered by date range"""
        filtered_job_data = self.get_filtered_job_data(start_date, end_date)
        
        if filtered_job_data.empty:
            return go.Figure().add_annotation(
                text=f"No job market data available for {start_date} to {end_date}", 
                xref="paper", yref="paper", x=0.5, y=0.5
            )
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Jobs by Source', 'Top Companies Hiring', 
                          'Location Distribution', 'Jobs Over Time'),
            specs=[[{"type": "pie"}, {"type": "bar"}],
                   [{"type": "bar"}, {"type": "scatter"}]]
        )
        
        # Jobs by source
        source_counts = filtered_job_data['source'].value_counts()
        fig.add_trace(
            go.Pie(labels=source_counts.index, values=source_counts.values,
                  name="Job Sources"),
            row=1, col=1
        )
        
        # Top companies hiring
        company_counts = filtered_job_data['company'].value_counts().head(10)
        fig.add_trace(
            go.Bar(x=company_counts.index, y=company_counts.values,
                  name="Companies"),
            row=1, col=2
        )
        
        # Location distribution
        location_counts = filtered_job_data['location'].value_counts().head(10)
        fig.add_trace(
            go.Bar(x=location_counts.index, y=location_counts.values,
                  name="Locations"),
            row=2, col=1
        )
        
        # Jobs over time
        filtered_job_data['scraped_date'] = pd.to_datetime(filtered_job_data['scraped_date'])
        daily_jobs = filtered_job_data.groupby(filtered_job_data['scraped_date'].dt.date).size()
        fig.add_trace(
            go.Scatter(x=daily_jobs.index, y=daily_jobs.values,
                      mode='lines+markers', name='Jobs Found'),
            row=2, col=2
        )
        
        fig.update_layout(
            height=800, 
            title_text=f"Job Market Analysis ({start_date} to {end_date})"
        )
        
        return fig
    
    def generate_summary_stats_filtered(self, start_date, end_date) -> Dict:
        """Generate summary statistics filtered by date range"""
        stats = {}
        
        filtered_email_data = self.get_filtered_email_data(start_date, end_date)
        filtered_job_data = self.get_filtered_job_data(start_date, end_date)
        
        if not filtered_email_data.empty:
            stats['total_applications'] = len(filtered_email_data[filtered_email_data['category'] == 'application_confirmation'])
            stats['interviews'] = len(filtered_email_data[filtered_email_data['category'] == 'interview_invitation'])
            stats['rejections'] = len(filtered_email_data[filtered_email_data['category'] == 'rejection'])
            
            # Look for job offers
            direct_offers_data = filtered_email_data[filtered_email_data['category'] == 'job_offer']
            
            # Check 'other' category emails for job offer keywords
            other_emails = filtered_email_data[filtered_email_data['category'] == 'other']
            job_offer_keywords = [
                'offer', 'congratulations', 'pleased to offer', 'job offer', 'offer letter', 
                'we are pleased', 'happy to offer', 'welcome to', 'join us', 'orientation',
                'start date', 'onboarding', 'welcome aboard', 'you got the job', 'hired',
                'your offer', 'offer accepted', 'contract'
            ]
            
            offer_emails = pd.DataFrame()
            if not other_emails.empty:
                offer_mask = other_emails['subject'].str.contains('|'.join(job_offer_keywords), case=False, na=False)
                offer_emails = other_emails[offer_mask]
            
            # Combine both sources
            all_offers = pd.concat([direct_offers_data, offer_emails]).drop_duplicates()
            
            # Filter out emails from excluded patterns
            excluded_patterns = 'aznh7|gmail|yahoo|hotmail|outlook|docusign|eumail'
            company_offers = all_offers[~all_offers['company'].str.contains(excluded_patterns, case=False, na=False)]
            
            if not company_offers.empty:
                company_offers = company_offers.copy()
                # Use same normalization as original method
                def normalize_company_name(company_name):
                    if pd.isna(company_name):
                        return company_name
                    
                    if 'flink' in company_name.lower():
                        return 'Flink'
                    
                    if 'trade' in company_name.lower() and 'republic' in company_name.lower():
                        return 'Trade Republic'
                        
                    import re
                    normalized = re.sub(r'^(your\s+offer\s+to\s+join\s+the\s+|congratulations\s+on\s+joining\s+the\s+)', '', company_name, flags=re.IGNORECASE)
                    normalized = re.sub(r'\s+(team|group|company)$', '', normalized, flags=re.IGNORECASE)
                    
                    return normalized.strip().title()
                
                company_offers['normalized_company'] = company_offers['company'].apply(normalize_company_name)
                stats['offers'] = company_offers['normalized_company'].nunique()
            else:
                stats['offers'] = 0
            
            # Calculate rates
            total_apps = max(stats['total_applications'], 1)
            stats['response_rate'] = (stats['interviews'] + stats['offers'] + stats['rejections']) / total_apps * 100
            stats['success_rate'] = stats['offers'] / total_apps * 100
        else:
            stats['total_applications'] = 0
            stats['interviews'] = 0
            stats['offers'] = 0
            stats['rejections'] = 0
            stats['response_rate'] = 0
            stats['success_rate'] = 0
        
        if not filtered_job_data.empty:
            stats['available_jobs'] = len(filtered_job_data)
            stats['unique_companies'] = filtered_job_data['company'].nunique()
            stats['job_sources'] = filtered_job_data['source'].nunique()
        else:
            stats['available_jobs'] = 0
            stats['unique_companies'] = 0
            stats['job_sources'] = 0
        
        return stats

if __name__ == "__main__":
    visualizer = JobTrackerVisualizer()
    stats = visualizer.generate_summary_stats()
    print("Summary Statistics:")
    for key, value in stats.items():
        print(f"{key}: {value}")
    
    visualizer.save_all_visualizations() 