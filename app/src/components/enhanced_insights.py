"""
Enhanced Insights Component for Job Tracker
Provides comprehensive analytics and insights
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import re

class EnhancedInsights:
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def show_market_intelligence(self, df, applications_df=None):
        """Show market intelligence insights"""
        st.markdown("### 🎯 Market Intelligence")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Market saturation analysis
            if not df.empty:
                total_jobs = len(df)
                unique_companies = df['company'].nunique()
                saturation_ratio = unique_companies / total_jobs if total_jobs > 0 else 0
                
                st.metric(
                    "Market Saturation",
                    f"{saturation_ratio:.1%}",
                    help="Ratio of unique companies to total jobs (lower = more concentrated market)"
                )
        
        with col2:
            # Average response time
            if applications_df is not None and not applications_df.empty:
                if 'applied_date' in applications_df.columns and 'status_date' in applications_df.columns:
                    applications_df['applied_date'] = pd.to_datetime(applications_df['applied_date'], errors='coerce')
                    applications_df['status_date'] = pd.to_datetime(applications_df['status_date'], errors='coerce')
                    
                    applications_df['response_time'] = (
                        applications_df['status_date'] - applications_df['applied_date']
                    ).dt.days
                    
                    avg_response = applications_df['response_time'].mean()
                    if pd.notna(avg_response):
                        st.metric("Avg Response Time", f"{avg_response:.1f} days")
        
        with col3:
            # Salary competitiveness
            if not df.empty and 'parsed_salary' in df.columns:
                salary_data = df[df['parsed_salary'].notna()]['parsed_salary']
                if len(salary_data) > 0:
                    salary_std = salary_data.std()
                    salary_mean = salary_data.mean()
                    coefficient_of_variation = salary_std / salary_mean if salary_mean > 0 else 0
                    
                    st.metric(
                        "Salary Variability",
                        f"{coefficient_of_variation:.2f}",
                        help="Coefficient of variation (higher = more salary variation)"
                    )
    
    def show_competitive_analysis(self, df):
        """Show competitive analysis insights"""
        st.markdown("### 🏆 Competitive Analysis")
        
        if df.empty:
            st.info("No data available for competitive analysis.")
            return
        
        # Company posting frequency analysis
        company_freq = df['company'].value_counts()
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Most active recruiters
            top_recruiters = company_freq.head(10)
            fig = px.bar(
                x=top_recruiters.values,
                y=top_recruiters.index,
                title="Most Active Recruiters",
                orientation='h'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Company size distribution
            company_size_categories = pd.cut(
                company_freq.values,
                bins=[0, 1, 3, 10, float('inf')],
                labels=['Small (1 job)', 'Medium (2-3 jobs)', 'Large (4-10 jobs)', 'Very Large (10+ jobs)']
            )
            size_dist = pd.Series(company_size_categories).value_counts()
            
            fig = px.pie(
                values=size_dist.values,
                names=size_dist.index,
                title="Company Size Distribution"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    def show_salary_benchmarking(self, df):
        """Show salary benchmarking insights"""
        st.markdown("### 💰 Salary Benchmarking")
        
        if df.empty or 'parsed_salary' not in df.columns:
            st.info("No salary data available for benchmarking.")
            return
        
        salary_data = df[df['parsed_salary'].notna()]['parsed_salary']
        
        if len(salary_data) < 5:
            st.info("Insufficient salary data for benchmarking.")
            return
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Median Salary", f"€{salary_data.median():,.0f}")
        
        with col2:
            st.metric("25th Percentile", f"€{salary_data.quantile(0.25):,.0f}")
        
        with col3:
            st.metric("75th Percentile", f"€{salary_data.quantile(0.75):,.0f}")
        
        with col4:
            st.metric("90th Percentile", f"€{salary_data.quantile(0.90):,.0f}")
        
        # Salary distribution with percentiles
        fig = go.Figure()
        
        fig.add_trace(go.Histogram(
            x=salary_data,
            nbinsx=30,
            name='Salary Distribution',
            opacity=0.7
        ))
        
        # Add percentile lines
        percentiles = [25, 50, 75, 90]
        colors = ['orange', 'red', 'purple', 'brown']
        
        for p, color in zip(percentiles, colors):
            value = salary_data.quantile(p/100)
            fig.add_vline(
                x=value,
                line_dash="dash",
                line_color=color,
                annotation_text=f"{p}th percentile: €{value:,.0f}"
            )
        
        fig.update_layout(
            title="Salary Distribution with Percentiles",
            xaxis_title="Salary (€)",
            yaxis_title="Frequency"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def show_temporal_analysis(self, df):
        """Show temporal analysis insights"""
        st.markdown("### 📅 Temporal Analysis")
        
        if df.empty:
            st.info("No data available for temporal analysis.")
            return
        
        # Convert to datetime if needed
        df['scraped_date'] = pd.to_datetime(df['scraped_date'])
        
        # Weekly patterns
        df['weekday'] = df['scraped_date'].dt.day_name()
        df['hour'] = df['scraped_date'].dt.hour
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Jobs by day of week
            weekday_counts = df['weekday'].value_counts()
            weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            weekday_counts = weekday_counts.reindex(weekday_order, fill_value=0)
            
            fig = px.bar(
                x=weekday_counts.index,
                y=weekday_counts.values,
                title="Jobs Posted by Day of Week"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Jobs by hour
            hour_counts = df['hour'].value_counts().sort_index()
            
            fig = px.bar(
                x=hour_counts.index,
                y=hour_counts.values,
                title="Jobs Posted by Hour of Day"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Monthly trends with moving average
        monthly_data = df.groupby(df['scraped_date'].dt.to_period('M')).size().reset_index()
        monthly_data.columns = ['month', 'count']
        monthly_data['month'] = monthly_data['month'].astype(str)
        
        # Calculate moving average
        monthly_data['moving_avg'] = monthly_data['count'].rolling(window=3, center=True).mean()
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=monthly_data['month'],
            y=monthly_data['count'],
            mode='lines+markers',
            name='Monthly Jobs',
            line=dict(color='blue')
        ))
        
        fig.add_trace(go.Scatter(
            x=monthly_data['month'],
            y=monthly_data['moving_avg'],
            mode='lines',
            name='3-Month Moving Average',
            line=dict(color='red', dash='dash')
        ))
        
        fig.update_layout(
            title="Monthly Job Posting Trends",
            xaxis_title="Month",
            yaxis_title="Number of Jobs"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def show_skill_demand_analysis(self, df):
        """Show skill demand analysis"""
        st.markdown("### 🔧 Skill Demand Analysis")
        
        if df.empty:
            st.info("No data available for skill analysis.")
            return
        
        # Extended skill keywords
        skill_keywords = {
            'Programming Languages': ['python', 'java', 'javascript', 'typescript', 'c\\+\\+', 'c#', 'php', 'ruby', 'go', 'rust', 'swift', 'kotlin'],
            'Frontend': ['react', 'angular', 'vue', 'html', 'css', 'sass', 'bootstrap', 'tailwind'],
            'Backend': ['node\\.js', 'express', 'django', 'flask', 'spring', 'laravel', 'asp\\.net'],
            'Databases': ['sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch'],
            'Cloud & DevOps': ['aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins', 'gitlab', 'terraform'],
            'Data & AI': ['machine learning', 'ai', 'data science', 'pandas', 'numpy', 'tensorflow', 'pytorch'],
            'Methodologies': ['agile', 'scrum', 'kanban', 'devops', 'ci/cd', 'tdd', 'bdd'],
            'Tools': ['git', 'jira', 'confluence', 'slack', 'teams', 'figma', 'postman']
        }
        
        # Analyze skill demand
        skill_analysis = {}
        
        for category, skills in skill_keywords.items():
            category_count = 0
            skill_details = {}
            
            for skill in skills:
                try:
                    # Use case-insensitive search with word boundaries
                    pattern = f"\\b{skill}\\b"
                    count = df['description'].str.lower().str.contains(pattern, regex=True, na=False).sum()
                    if count > 0:
                        skill_details[skill.replace('\\', '')] = count
                        category_count += count
                except Exception:
                    # Fallback to simple string search if regex fails
                    try:
                        count = df['description'].str.lower().str.contains(skill.replace('\\', ''), na=False).sum()
                        if count > 0:
                            skill_details[skill.replace('\\', '')] = count
                            category_count += count
                    except Exception:
                        continue
            
            if category_count > 0:
                skill_analysis[category] = {
                    'total_demand': category_count,
                    'skills': skill_details
                }
        
        # Show top skill categories
        if skill_analysis:
            category_demand = {cat: data['total_demand'] for cat, data in skill_analysis.items()}
            top_categories = dict(sorted(category_demand.items(), key=lambda x: x[1], reverse=True)[:8])
            
            fig = px.bar(
                x=list(top_categories.values()),
                y=list(top_categories.keys()),
                title="Skill Category Demand",
                orientation='h'
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Show detailed skills within top categories
            st.markdown("#### Top Skills by Category")
            
            for category, data in list(skill_analysis.items())[:4]:  # Top 4 categories
                with st.expander(f"{category} ({data['total_demand']} mentions)"):
                    top_skills = dict(sorted(data['skills'].items(), key=lambda x: x[1], reverse=True)[:5])
                    
                    fig = px.bar(
                        x=list(top_skills.values()),
                        y=list(top_skills.keys()),
                        title=f"Top {category} Skills",
                        orientation='h'
                    )
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No skill data found in job descriptions.")
    
    def show_application_performance_insights(self, applications_df):
        """Show application performance insights"""
        st.markdown("### 📊 Application Performance Insights")
        
        if applications_df.empty:
            st.info("No application data available for analysis.")
            return
        
        # Calculate performance metrics
        total_apps = len(applications_df)
        
        # Status progression analysis
        status_order = ['saved', 'applied', 'interview', 'offer', 'accepted']
        status_counts = applications_df['status'].value_counts()
        
        # Calculate conversion rates
        conversion_rates = {}
        cumulative = 0
        
        for status in status_order:
            if status in status_counts:
                count = status_counts[status]
                conversion_rates[status] = (count / total_apps) * 100
                cumulative += count
            else:
                conversion_rates[status] = 0
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        cols = [col1, col2, col3, col4, col5]
        
        for i, status in enumerate(status_order):
            with cols[i]:
                if status in status_counts:
                    count = status_counts[status]
                    rate = conversion_rates[status]
                    st.metric(
                        status.title(),
                        f"{count} ({rate:.1f}%)",
                        help=f"Jobs in {status} status"
                    )
        
        # Funnel chart
        fig = go.Figure(go.Funnel(
            y=status_order,
            x=[status_counts.get(status, 0) for status in status_order],
            textinfo="value+percent initial"
        ))
        
        fig.update_layout(
            title="Application Funnel",
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Time-based performance analysis
        if 'applied_date' in applications_df.columns:
            applications_df['applied_date'] = pd.to_datetime(applications_df['applied_date'], errors='coerce')
            
            # Applications over time
            monthly_apps = applications_df.groupby(
                applications_df['applied_date'].dt.to_period('M')
            ).size().reset_index()
            monthly_apps.columns = ['month', 'applications']
            monthly_apps['month'] = monthly_apps['month'].astype(str)
            
            fig = px.line(
                monthly_apps,
                x='month',
                y='applications',
                title="Applications Over Time"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    def show_predictive_insights(self, df, applications_df=None):
        """Show predictive insights and recommendations"""
        st.markdown("### 🔮 Predictive Insights & Recommendations")
        
        if df.empty:
            st.info("No data available for predictive insights.")
            return
        
        # Market trend analysis
        if len(df) > 10:
            df['scraped_date'] = pd.to_datetime(df['scraped_date'])
            
            # Calculate weekly growth rate
            weekly_data = df.groupby(df['scraped_date'].dt.to_period('W')).size().reset_index()
            weekly_data.columns = ['week', 'count']
            weekly_data['week'] = weekly_data['week'].astype(str)
            
            if len(weekly_data) > 2:
                # Calculate growth rate
                weekly_data['growth_rate'] = weekly_data['count'].pct_change() * 100
                
                recent_growth = weekly_data['growth_rate'].tail(3).mean()
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric(
                        "Recent Market Growth",
                        f"{recent_growth:+.1f}%",
                        help="Average weekly growth rate over last 3 weeks"
                    )
                
                with col2:
                    # Predict next week
                    if recent_growth > 0:
                        prediction = "📈 Growing"
                        color = "green"
                    elif recent_growth < 0:
                        prediction = "📉 Declining"
                        color = "red"
                    else:
                        prediction = "➡️ Stable"
                        color = "blue"
                    
                    st.markdown(f"<h3 style='color: {color};'>{prediction}</h3>", unsafe_allow_html=True)
                
                with col3:
                    # Market sentiment
                    if recent_growth > 5:
                        sentiment = "🔥 Hot Market"
                    elif recent_growth > 0:
                        sentiment = "📈 Active Market"
                    elif recent_growth > -5:
                        sentiment = "➡️ Stable Market"
                    else:
                        sentiment = "❄️ Slow Market"
                    
                    st.markdown(f"<h3>{sentiment}</h3>", unsafe_allow_html=True)
        
        # Recommendations
        st.markdown("#### 💡 Recommendations")
        
        recommendations = []
        
        # Salary recommendations
        if 'parsed_salary' in df.columns:
            salary_data = df[df['parsed_salary'].notna()]['parsed_salary']
            if len(salary_data) > 0:
                median_salary = salary_data.median()
                recommendations.append(f"💰 **Salary Benchmark**: Median salary is €{median_salary:,.0f}")
        
        # Platform recommendations
        platform_counts = df['source'].value_counts()
        if not platform_counts.empty:
            top_platform = platform_counts.index[0]
            recommendations.append(f"🌐 **Best Platform**: {top_platform.title()} has the most job postings")
        
        # Location recommendations
        location_counts = df['location'].value_counts()
        if not location_counts.empty:
            top_location = location_counts.index[0]
            recommendations.append(f"📍 **Hot Location**: {top_location} has the most opportunities")
        
        # Skill recommendations
        if 'description' in df.columns:
            skill_keywords = ['python', 'javascript', 'react', 'aws', 'docker']
            skill_demand = {}
            
            for skill in skill_keywords:
                count = df['description'].str.lower().str.contains(skill, na=False).sum()
                if count > 0:
                    skill_demand[skill] = count
            
            if skill_demand:
                top_skill = max(skill_demand, key=skill_demand.get)
                recommendations.append(f"🔧 **In-Demand Skill**: {top_skill.title()} is most requested")
        
        # Remote work insight
        remote_keywords = ['remote', 'home', 'hybrid']
        try:
            remote_count = df['description'].str.lower().str.contains('|'.join(remote_keywords), na=False).sum()
        except Exception:
            # Fallback: check each keyword separately
            remote_count = 0
            for keyword in remote_keywords:
                try:
                    remote_count += df['description'].str.lower().str.contains(keyword, na=False).sum()
                except Exception:
                    continue
        
        remote_percentage = (remote_count / len(df)) * 100
        if remote_percentage > 20:
            recommendations.append(f"🏠 {remote_percentage:.1f}% of jobs offer remote work")
        
        # Display recommendations
        for rec in recommendations:
            st.markdown(f"• {rec}")
        
        # Application strategy recommendations
        if applications_df is not None and not applications_df.empty:
            st.markdown("#### 📝 Application Strategy")
            
            # Calculate success rate
            success_statuses = ['interview', 'offer', 'accepted']
            successful = len(applications_df[applications_df['status'].isin(success_statuses)])
            success_rate = (successful / len(applications_df)) * 100
            
            if success_rate < 10:
                st.warning("⚠️ **Low Success Rate**: Consider improving your application strategy")
                st.markdown("""
                **Suggestions:**
                - Review and update your resume
                - Customize cover letters for each application
                - Follow up on applications after 1-2 weeks
                - Practice interview skills
                """)
            elif success_rate < 25:
                st.info("📈 **Good Progress**: Your success rate is improving")
            else:
                st.success("🎉 **Excellent Performance**: Keep up the great work!")
    
    def show_comprehensive_dashboard(self, df, applications_df=None):
        """Show comprehensive insights dashboard"""
        st.markdown("## 📊 Enhanced Analytics Dashboard")
        
        # Market Intelligence
        self.show_market_intelligence(df, applications_df)
        
        # Competitive Analysis
        self.show_competitive_analysis(df)
        
        # Salary Benchmarking
        self.show_salary_benchmarking(df)
        
        # Temporal Analysis
        self.show_temporal_analysis(df)
        
        # Skill Demand Analysis
        self.show_skill_demand_analysis(df)
        
        # Application Performance (if available)
        if applications_df is not None:
            self.show_application_performance_insights(applications_df)
        
        # Predictive Insights
        self.show_predictive_insights(df, applications_df) 