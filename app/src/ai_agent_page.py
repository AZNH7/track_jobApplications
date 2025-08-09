#!/usr/bin/env python3
"""
AI Career Agent Page - Streamlit Interface
Intelligent career advisory assistant interface
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
import os
from ai_career_agent import AICareerAgent
from config_manager import ConfigManager
from database_manager import get_db_manager
from gmail_analyzer import OptimizedGmailJobAnalyzer

def load_ai_agent():
    """Load and initialize AI Career Agent"""
    try:
        config = ConfigManager()
        ollama_config = config.get_setting("llm", {})
        
        agent = AICareerAgent(
            ollama_host=ollama_config.get('ollama_host', 'http://localhost:11434'),
            model_name=ollama_config.get('ollama_model', 'llama3:8b')
        )
        return agent
    except Exception as e:
        st.error(f"Failed to initialize AI Career Agent: {e}")
        return None

def display_cv_analysis(agent: AICareerAgent):
    """Display comprehensive CV analysis"""
    st.header("🎯 CV Analysis & Optimization")
    
    if not agent.cv_analysis:
        st.warning("📄 No CV found or analysis not available. Please ensure your resume.pdf is in the shared/cv/ directory.")
        return
    
    analysis = agent.cv_analysis
    
    # Overall Assessment
    st.subheader("📊 Overall Assessment")
    
    if 'overall_assessment' in analysis:
        assessment = analysis['overall_assessment']
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Strength Score", f"{assessment.get('strength_score', 0)}/10")
        with col2:
            st.metric("Clarity Score", f"{assessment.get('clarity_score', 0)}/10")
        with col3:
            st.metric("Completeness", f"{assessment.get('completeness_score', 0)}/10")
        with col4:
            st.metric("Market Ready", f"{assessment.get('market_readiness', 0)}/10")
        
        if 'summary' in assessment:
            st.info(f"💡 **Overall Summary:** {assessment['summary']}")
    
    # Strengths and Weaknesses
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("✅ Key Strengths")
        if 'strengths' in analysis:
            for strength in analysis['strengths']:
                st.success(f"• {strength}")
    
    with col2:
        st.subheader("⚠️ Areas for Improvement")
        if 'weaknesses' in analysis:
            for weakness in analysis['weaknesses']:
                st.warning(f"• {weakness}")
    
    # Skills Analysis
    if 'skills_analysis' in analysis:
        st.subheader("🛠️ Skills Analysis")
        skills = analysis['skills_analysis']
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.write("**Technical Skills:**")
            for skill in skills.get('technical_skills', []):
                st.write(f"• {skill}")
        
        with col2:
            st.write("**Soft Skills:**")
            for skill in skills.get('soft_skills', []):
                st.write(f"• {skill}")
        
        with col3:
            st.write("**Missing Skills:**")
            for skill in skills.get('missing_skills', []):
                st.write(f"❌ {skill}")
        
        if 'skill_level' in skills:
            st.info(f"🎯 **Skill Level:** {skills['skill_level']}")
        
        if 'recommendations' in skills:
            st.write("**Skill Development Recommendations:**")
            for rec in skills['recommendations']:
                st.write(f"📈 {rec}")
    
    # Experience Analysis
    if 'experience_analysis' in analysis:
        st.subheader("💼 Experience Analysis")
        exp = analysis['experience_analysis']
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Years Experience", exp.get('years_experience', 0))
        with col2:
            st.metric("Career Progression", exp.get('career_progression', 'Unknown'))
        with col3:
            st.metric("Industry Focus", exp.get('industry_focus', 'Unknown'))
        
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Role Consistency:** {exp.get('role_consistency', 'Unknown')}")
            st.write(f"**Leadership Experience:** {'Yes' if exp.get('leadership_experience') else 'No'}")
        with col2:
            st.metric("Achievement Quality", f"{exp.get('achievements_quality', 0)}/10")
    
    # Market Positioning
    if 'market_positioning' in analysis:
        st.subheader("🎯 Market Positioning")
        market = analysis['market_positioning']
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Target Roles:**")
            for role in market.get('target_roles', []):
                st.write(f"• {role}")
            
            st.write(f"**Salary Range:** {market.get('salary_range', 'Not specified')}")
        
        with col2:
            st.write(f"**Market Demand:** {market.get('market_demand', 'Unknown')}")
            st.write(f"**Competitive Advantage:** {market.get('competitive_advantage', 'Not identified')}")
            st.write(f"**Differentiation:** {market.get('differentiation', 'Not specified')}")
    
    # Recommendations
    if 'recommendations' in analysis:
        st.subheader("🚀 Action Plan")
        recs = analysis['recommendations']
        
        col1, col2 = st.columns(2)
        
        with col1:
            if 'immediate_actions' in recs:
                st.write("**Immediate Actions:**")
                for action in recs['immediate_actions']:
                    st.write(f"🎯 {action}")
            
            if 'skill_development' in recs:
                st.write("**Skill Development:**")
                for skill in recs['skill_development']:
                    st.write(f"📚 {skill}")
        
        with col2:
            if 'experience_gaps' in recs:
                st.write("**Experience Gaps to Fill:**")
                for gap in recs['experience_gaps']:
                    st.write(f"🔧 {gap}")
            
            if 'networking_focus' in recs:
                st.write("**Networking Focus:**")
                for area in recs['networking_focus']:
                    st.write(f"🤝 {area}")
        
        if 'application_strategy' in recs:
            st.info(f"📋 **Application Strategy:** {recs['application_strategy']}")

def display_job_market_insights(agent: AICareerAgent):
    """Display job market analysis"""
    st.header("📈 Job Market Intelligence")
    
    # Load job data
    try:
        db_manager = get_db_manager()
        engine = db_manager.get_sqlalchemy_engine()
        jobs_df = pd.read_sql_query("SELECT * FROM job_listings", engine)
        
        if jobs_df.empty:
            st.warning("No job data available. Please run a job search first.")
            return
        
        job_data = jobs_df.to_dict('records')
        
        # Market Overview
        st.subheader("📊 Market Overview")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Jobs", len(job_data))
        with col2:
            unique_companies = jobs_df['company'].nunique()
            st.metric("Companies", unique_companies)
        with col3:
            unique_locations = jobs_df['location'].nunique()
            st.metric("Locations", unique_locations)
        with col4:
            # Check if cv_match_score column exists
            if 'cv_match_score' in jobs_df.columns:
                avg_cv_match = jobs_df['cv_match_score'].mean()
                st.metric("Avg CV Match", f"{avg_cv_match:.1f}%")
            else:
                st.metric("Avg CV Match", "N/A")
        
        # Visualizations
        col1, col2 = st.columns(2)
        
        with col1:
            # Top companies
            company_counts = jobs_df['company'].value_counts().head(10)
            fig = px.bar(
                x=company_counts.values,
                y=company_counts.index,
                orientation='h',
                title="Top Hiring Companies",
                labels={'x': 'Job Postings', 'y': 'Company'}
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Location distribution
            location_counts = jobs_df['location'].value_counts().head(10)
            fig = px.pie(
                values=location_counts.values,
                names=location_counts.index,
                title="Job Locations"
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        # Work arrangement analysis
        if 'work_arrangement' in jobs_df.columns:
            st.subheader("🏠 Work Arrangement Analysis")
            work_counts = jobs_df['work_arrangement'].value_counts()
            
            col1, col2 = st.columns(2)
            with col1:
                fig = px.bar(
                    x=work_counts.index,
                    y=work_counts.values,
                    title="Work Arrangement Distribution",
                    labels={'x': 'Work Type', 'y': 'Job Count'}
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                for work_type, count in work_counts.items():
                    percentage = (count / len(jobs_df) * 100)
                    st.metric(work_type, f"{count} ({percentage:.1f}%)")
        
        # AI Analysis
        st.subheader("🤖 AI Market Analysis")
        
        if st.button("Generate Market Intelligence Report", type="primary"):
            with st.spinner("Analyzing job market trends..."):
                market_analysis = agent.analyze_job_market_trends(job_data)
                st.markdown(market_analysis)
    
    except Exception as e:
        st.error(f"Error loading job market data: {e}")
        st.info("💡 Run a job search first to populate the database with job data.")

def display_email_insights(agent: AICareerAgent):
    """Display email analysis and application insights"""
    st.header("📧 Email & Application Analysis")
    
    try:
        # Try to load email data from database
        db_manager = get_db_manager()
        engine = db_manager.get_sqlalchemy_engine()
        email_data = pd.read_sql_query("SELECT * FROM email_analysis", engine)
        
        if email_data.empty:
            st.warning("No email data available. Please configure Gmail integration and run email analysis first.")
            return
        
        # Convert to list of dictionaries for the agent
        email_list = email_data.to_dict('records')
        
        # Application Performance Metrics
        st.subheader("📊 Application Performance")
        
        performance = agent.analyze_application_performance(email_list)
        
        if performance:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Applications", performance['total_applications'])
            with col2:
                st.metric("Response Rate", f"{performance['response_rate']:.1f}%")
            with col3:
                st.metric("Interview Rate", f"{performance['interview_rate']:.1f}%")
            with col4:
                st.metric("Offer Rate", f"{performance['offer_rate']:.1f}%")
            
            # Performance visualization
            metrics = ['Applications', 'Responses', 'Interviews', 'Offers']
            values = [
                performance['total_applications'],
                performance['responses'],
                performance['interviews'],
                performance['offers']
            ]
            
            fig = go.Figure(data=[
                go.Bar(name='Application Funnel', x=metrics, y=values)
            ])
            fig.update_layout(title="Application Success Funnel")
            st.plotly_chart(fig, use_container_width=True)
        
        # Email Pattern Analysis
        st.subheader("🤖 AI Email Pattern Analysis")
        
        if st.button("Analyze Email Patterns", type="primary"):
            with st.spinner("Analyzing email patterns and application success..."):
                email_analysis = agent.analyze_email_patterns(email_list)
                st.markdown(email_analysis)
    
    except Exception as e:
        st.error(f"Error loading email data: {e}")
        st.info("💡 To enable email analysis, please configure Gmail integration and run email analysis first.")

def display_career_advisor(agent: AICareerAgent):
    """Display interactive career advisor"""
    st.header("🤖 AI Career Advisor")
    
    st.write("Ask me anything about your career, job search strategy, or professional development!")
    
    # Predefined question categories
    st.subheader("💡 Quick Questions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🎯 Optimize My Job Search"):
            query = "How can I optimize my job search strategy based on my CV and current market conditions?"
            st.session_state.career_query = query
    
    with col2:
        if st.button("💰 Salary Negotiation Tips"):
            query = "What salary negotiation strategies should I use based on my experience level and market position?"
            st.session_state.career_query = query
    
    with col3:
        if st.button("🚀 Career Advancement"):
            query = "What are the best ways to advance my career and increase my market value?"
            st.session_state.career_query = query
    
    # Custom question input
    st.subheader("❓ Ask Your Question")
    
    # Initialize session state
    if 'career_query' not in st.session_state:
        st.session_state.career_query = ""
    
    query = st.text_area(
        "What would you like to know?",
        value=st.session_state.career_query,
        height=100,
        placeholder="e.g., How should I prepare for interviews in my field? What skills should I develop next?"
    )
    
    # Context options
    with st.expander("🔧 Additional Context (Optional)"):
        target_role = st.text_input("Target Role", placeholder="e.g., Senior Software Engineer")
        target_location = st.text_input("Target Location", placeholder="e.g., Berlin, Remote")
        salary_expectation = st.text_input("Salary Expectation", placeholder="e.g., €70,000 - €90,000")
        timeline = st.selectbox("Job Search Timeline", ["Immediate", "1-3 months", "3-6 months", "6+ months"])
        
        context = {}
        if target_role:
            context['target_role'] = target_role
        if target_location:
            context['target_location'] = target_location
        if salary_expectation:
            context['salary_expectation'] = salary_expectation
        if timeline:
            context['timeline'] = timeline
    
    if st.button("Get AI Advice", type="primary") and query.strip():
        with st.spinner("Consulting AI career advisor..."):
            advice = agent.get_personalized_advice(query, context if 'context' in locals() else None)
            
            st.subheader("🎯 AI Career Advice")
            st.markdown(advice)
            
            # Clear the query
            st.session_state.career_query = ""

def display_job_search_strategy(agent: AICareerAgent):
    """Display job search strategy generator"""
    st.header("📋 Personalized Job Search Strategy")
    
    st.write("Generate a comprehensive, personalized job search strategy based on your profile and preferences.")
    
    with st.form("strategy_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            target_roles = st.text_area("Target Roles", placeholder="e.g., Software Engineer, Data Scientist")
            preferred_locations = st.text_area("Preferred Locations", placeholder="e.g., Berlin, Munich, Remote")
            salary_range = st.text_input("Salary Range", placeholder="e.g., €60,000 - €80,000")
            work_preference = st.selectbox("Work Preference", ["Remote", "Hybrid", "On-site", "Flexible"])
        
        with col2:
            company_size = st.selectbox("Company Size Preference", ["Startup", "Scale-up", "Mid-size", "Enterprise", "Any"])
            industry_focus = st.text_area("Industry Focus", placeholder="e.g., FinTech, E-commerce, Healthcare")
            timeline = st.selectbox("Job Search Timeline", ["1 month", "2-3 months", "3-6 months", "6+ months"])
            availability = st.selectbox("Availability", ["Immediate", "2 weeks notice", "1 month notice", "Flexible"])
        
        # Additional preferences
        st.subheader("Additional Preferences")
        skill_development = st.text_area("Skills to Develop", placeholder="e.g., Python, Machine Learning, Leadership")
        career_goals = st.text_area("Career Goals", placeholder="e.g., Technical leadership, Product management transition")
        
        submitted = st.form_submit_button("Generate Strategy", type="primary")
        
        if submitted:
            preferences = {
                "target_roles": target_roles.split(',') if target_roles else [],
                "preferred_locations": preferred_locations.split(',') if preferred_locations else [],
                "salary_range": salary_range,
                "work_preference": work_preference,
                "company_size": company_size,
                "industry_focus": industry_focus.split(',') if industry_focus else [],
                "timeline": timeline,
                "availability": availability,
                "skill_development": skill_development.split(',') if skill_development else [],
                "career_goals": career_goals
            }
            
            with st.spinner("Generating personalized job search strategy..."):
                strategy = agent.generate_job_search_strategy(preferences)
                
                st.subheader("🎯 Your Personalized Job Search Strategy")
                st.markdown(strategy)

def main():
    """Main AI Agent page"""
    st.set_page_config(
        page_title="AI Career Agent",
        page_icon="🤖",
        layout="wide"
    )
    
    st.title("🤖 AI Career Agent")
            st.write(f"Your intelligent career advisory assistant powered by {agent.model_name}")
    
    # Initialize AI Agent
    agent = load_ai_agent()
    
    if not agent:
        st.error("❌ AI Career Agent is not available. Please check your Ollama configuration.")
        return
    
    if not agent.available:
        st.error(f"❌ AI model is not available. Please ensure Ollama is running with {agent.model_name} model.")
        return
    
    # Agent status
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.success("✅ AI Career Agent is ready!")
    with col2:
        st.info(f"Model: {agent.model_name}")
    with col3:
        cv_status = "✅ CV Loaded" if agent.cv_content else "❌ No CV"
        st.info(cv_status)
    
    # Navigation tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🎯 CV Analysis",
        "📈 Market Intelligence", 
        "📧 Email Insights",
        "🤖 Career Advisor",
        "📋 Job Strategy"
    ])
    
    with tab1:
        display_cv_analysis(agent)
    
    with tab2:
        display_job_market_insights(agent)
    
    with tab3:
        display_email_insights(agent)
    
    with tab4:
        display_career_advisor(agent)
    
    with tab5:
        display_job_search_strategy(agent)

if __name__ == "__main__":
    main() 