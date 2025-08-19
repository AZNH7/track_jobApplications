"""
Quick Insights Widget for Job Tracker
Provides bite-sized insights and recommendations
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re

class QuickInsightsWidget:
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def _parse_salary(self, salary_str):
        """Parse salary string to extract numeric value"""
        if pd.isna(salary_str):
            return None
            
        numbers = re.findall(r'[\d.,]+', str(salary_str))
        if not numbers:
            return None
            
        salary_num = numbers[0].replace('.', '').replace(',', '.')
        try:
            return float(salary_num)
        except ValueError:
            return None
    
    def show_quick_metrics(self, df, applications_df=None):
        """Show quick metrics in a compact format"""
        if df.empty:
            st.info("📊 No job data available")
            return
        
        # Quick stats
        total_jobs = len(df)
        unique_companies = df['company'].nunique()
        
        # Parse salaries for insights
        df['parsed_salary'] = df['salary'].apply(self._parse_salary)
        salary_data = df[df['parsed_salary'].notna()]['parsed_salary']
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("📋 Jobs", total_jobs)
            if len(salary_data) > 0:
                st.metric("💰 Avg Salary", f"€{salary_data.mean():,.0f}")
        
        with col2:
            st.metric("🏢 Companies", unique_companies)
            if len(salary_data) > 0:
                st.metric("📈 Median", f"€{salary_data.median():,.0f}")
        
        # Application insights
        if applications_df is not None and not applications_df.empty:
            st.markdown("---")
            st.markdown("**📝 Applications**")
            
            total_apps = len(applications_df)
            active_apps = len(applications_df[applications_df['status'].isin(['saved', 'applied', 'interview'])])
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total", total_apps)
            with col2:
                st.metric("Active", active_apps)
    
    def show_market_pulse(self, df):
        """Show market pulse indicators"""
        if df.empty:
            return
        
        st.markdown("### 📊 Market Pulse")
        
        # Recent activity (last 7 days)
        df['scraped_date'] = pd.to_datetime(df['scraped_date'])
        recent_date = datetime.now() - timedelta(days=7)
        recent_jobs = df[df['scraped_date'] >= recent_date]
        
        # Activity indicator
        if len(recent_jobs) > 10:
            pulse = "🟢 High Activity"
            color = "green"
        elif len(recent_jobs) > 5:
            pulse = "🟡 Moderate Activity"
            color = "orange"
        else:
            pulse = "🔴 Low Activity"
            color = "red"
        
        st.markdown(f"<h4 style='color: {color};'>{pulse}</h4>", unsafe_allow_html=True)
        st.caption(f"{len(recent_jobs)} jobs in last 7 days")
        
        # Top platform
        if not df.empty:
            top_platform = df['source'].value_counts().index[0]
            st.caption(f"🏆 {top_platform.title()} leads with most jobs")
    
    def show_salary_insights(self, df):
        """Show quick salary insights"""
        if df.empty or 'parsed_salary' not in df.columns:
            return
        
        salary_data = df[df['parsed_salary'].notna()]['parsed_salary']
        if len(salary_data) < 5:
            return
        
        st.markdown("### 💰 Salary Insights")
        
        # Salary range
        min_salary = salary_data.min()
        max_salary = salary_data.max()
        median_salary = salary_data.median()
        
        st.caption(f"Range: €{min_salary:,.0f} - €{max_salary:,.0f}")
        st.caption(f"Median: €{median_salary:,.0f}")
        
        # Market position indicator
        if median_salary > 80000:
            market_position = "💰 High-paying market"
        elif median_salary > 60000:
            market_position = "💵 Good-paying market"
        else:
            market_position = "📉 Lower-paying market"
        
        st.caption(market_position)
    
    def show_skill_hotlist(self, df):
        """Show hot skills in demand"""
        if df.empty:
            return
        
        st.markdown("### 🔥 Hot Skills")
        
        # Common skills to check (simplified without regex)
        hot_skills = ['python', 'javascript', 'react', 'aws', 'docker', 'kubernetes', 'machine learning']
        
        skill_counts = {}
        for skill in hot_skills:
            try:
                # Simple string search without regex
                count = df['description'].str.lower().str.contains(skill, na=False).sum()
                if count > 0:
                    skill_counts[skill.title()] = count
            except Exception:
                continue
        
        if skill_counts:
            # Show top 3 skills
            top_skills = dict(sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:3])
            
            for skill, count in top_skills.items():
                percentage = (count / len(df)) * 100
                st.caption(f"🔥 {skill}: {count} jobs ({percentage:.1f}%)")
        else:
            st.caption("No common skills detected")
    
    def show_recommendations(self, df, applications_df=None):
        """Show actionable recommendations"""
        st.markdown("### 💡 Quick Tips")
        
        recommendations = []
        
        # Data-based recommendations
        if not df.empty:
            # Platform recommendation
            platform_counts = df['source'].value_counts()
            if not platform_counts.empty:
                top_platform = platform_counts.index[0]
                recommendations.append(f"🎯 Focus on {top_platform.title()} for most opportunities")
            
            # Location recommendation
            location_counts = df['location'].value_counts()
            if not location_counts.empty:
                top_location = location_counts.index[0]
                recommendations.append(f"📍 {top_location} has the most job postings")
            
            # Remote work insight
            remote_keywords = ['remote', 'home', 'hybrid']
            remote_count = df['description'].str.lower().str.contains('|'.join(remote_keywords), na=False).sum()
            remote_percentage = (remote_count / len(df)) * 100
            if remote_percentage > 20:
                recommendations.append(f"🏠 {remote_percentage:.1f}% of jobs offer remote work")
        
        # Application recommendations
        if applications_df is not None and not applications_df.empty:
            total_apps = len(applications_df)
            if total_apps < 10:
                recommendations.append("📝 Consider applying to more positions")
            elif total_apps > 50:
                recommendations.append("🎯 Focus on quality over quantity")
        
        # Display recommendations
        for rec in recommendations[:3]:  # Show top 3
            st.caption(f"• {rec}")
    
    def show_sidebar_widget(self, df, applications_df=None):
        """Show comprehensive sidebar widget"""
        st.sidebar.markdown("## 📊 Quick Insights")
        
        # Quick metrics
        self.show_quick_metrics(df, applications_df)
        
        # Market pulse
        self.show_market_pulse(df)
        
        # Salary insights
        self.show_salary_insights(df)
        
        # Hot skills
        self.show_skill_hotlist(df)
        
        # Recommendations
        self.show_recommendations(df, applications_df)
        
        # Data freshness
        if not df.empty:
            st.sidebar.markdown("---")
            latest_date = df['scraped_date'].max()
            days_old = (datetime.now() - latest_date).days
            
            if days_old == 0:
                freshness = "🟢 Today"
            elif days_old == 1:
                freshness = "🟡 Yesterday"
            elif days_old < 7:
                freshness = f"🟡 {days_old} days ago"
            else:
                freshness = f"🔴 {days_old} days ago"
            
            st.sidebar.caption(f"📅 Data: {freshness}")
    
    def show_mini_dashboard(self, df, applications_df=None):
        """Show mini dashboard for compact spaces"""
        if df.empty:
            st.info("No data available")
            return
        
        # Compact metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📋", len(df))
        
        with col2:
            st.metric("🏢", df['company'].nunique())
        
        with col3:
            if applications_df is not None and not applications_df.empty:
                active = len(applications_df[applications_df['status'].isin(['saved', 'applied', 'interview'])])
                st.metric("📝", active)
        
        with col4:
            df['parsed_salary'] = df['salary'].apply(self._parse_salary)
            salary_data = df[df['parsed_salary'].notna()]['parsed_salary']
            if len(salary_data) > 0:
                st.metric("💰", f"€{salary_data.mean():,.0f}")
        
        # Quick insights
        with st.expander("🔍 Quick Insights", expanded=False):
            self.show_market_pulse(df)
            self.show_skill_hotlist(df)
            self.show_recommendations(df, applications_df) 