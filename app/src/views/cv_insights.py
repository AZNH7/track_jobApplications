import streamlit as st
import PyPDF2
from io import BytesIO
import json

from core.base_tracker import BaseJobTracker
from utils.ui_components import UIComponents
from ollama_client import ollama_client
from scrapers.job_scraper_orchestrator import JobScraperOrchestrator

class CVInsightsView(BaseJobTracker):
    def __init__(self):
        super().__init__()
        self.ui = UIComponents()
        if 'job_titles' not in st.session_state:
            st.session_state.job_titles = []
        if 'search_results' not in st.session_state:
            st.session_state.search_results = None

    def _extract_text(self, file_bytes, file_type):
        text = ""
        if file_type == "application/pdf":
            pdf_reader = PyPDF2.PdfReader(BytesIO(file_bytes))
            for page in pdf_reader.pages:
                text += page.extract_text()
        return text

    def _display_results(self, df):
        st.subheader("Top 10 Job Postings")
        if df is not None and not df.empty:
            for index, row in df.head(10).iterrows():
                st.markdown(f"#### {row['title']}")
                st.markdown(f"**Company:** {row['company']}")
                st.markdown(f"**Location:** {row['location']}")
                st.markdown(f"[Link]({row['link']})")
                st.markdown("---")
        else:
            st.info("No jobs found.")

    def show(self):
        """Show the CV Insights page"""
        self.ui.show_header("📄 CV Insights")
        st.write("Get AI-powered insights from your CV to supercharge your job search.")

        # 1. CV Upload
        st.subheader("Upload your CV")
        uploaded_file = st.file_uploader("Choose a CV file (PDF only)", type=["pdf"])

        if uploaded_file is not None:
            bytes_data = uploaded_file.getvalue()
            
            # 2. LLM Evaluation
            if st.button("Analyze CV"):
                with st.spinner("Analyzing CV... This may take a moment."):
                    cv_text = self._extract_text(bytes_data, uploaded_file.type)
                    
                    if not cv_text.strip():
                        st.error("Could not extract text from the CV. Please try another file.")
                        return

                    system_prompt = """
                    You are an expert career advisor. Your task is to analyze a CV and provide a summary, 
                    and suggest relevant job titles for a job search.
                    The user will provide their CV content.
                    Go over the full cv as it contains job title and describtion of the each experiance.
                    Respond with a JSON object with two keys: 'summary' and 'job_titles'.
                    'summary' should be a string containing a brief overview of the candidate's profile.
                    'job_titles' should be a list of 5-10 relevant job titles.
                    """
                    
                    prompt = f"Here is the CV:\n\n{cv_text}"

                    response = ollama_client.generate(prompt=prompt, system_prompt=system_prompt)

                    if response:
                        try:
                            # Clean the response to handle potential markdown code blocks
                            clean_response = response.strip()
                            if clean_response.startswith("```json"):
                                clean_response = clean_response[7:]
                            if clean_response.startswith("```"):
                                clean_response = clean_response[3:]
                            if clean_response.endswith("```"):
                                clean_response = clean_response[:-3]
                            
                            analysis = json.loads(clean_response)
                            st.session_state.cv_summary = analysis.get("summary", "No summary available.")
                            st.session_state.job_titles = analysis.get("job_titles", [])
                        except json.JSONDecodeError:
                            st.error("Could not parse the analysis from the LLM. Please try again.")
                            st.text_area("LLM Raw Response", response)
                    else:
                        st.error("Failed to get a response from the LLM.")
        
        if 'cv_summary' in st.session_state:
            st.subheader("CV Analysis")
            st.write(st.session_state.cv_summary)
        
        if st.session_state.job_titles:
            st.subheader("Suggested Job Titles")
            for title in st.session_state.job_titles:
                st.markdown(f"- {title}")
            
            st.subheader("Job Search")
            location = st.text_input("Enter a location for job search", "Germany")
            
            if st.button("Search for Jobs"):
                with st.spinner("Searching for jobs..."):
                    orchestrator = JobScraperOrchestrator()
                    results_df = orchestrator.search_all_platforms(
                        keywords=st.session_state.job_titles,
                        location=location,
                        max_pages=1
                    )
                    st.session_state.search_results = results_df
        
        if st.session_state.search_results is not None:
            self._display_results(st.session_state.search_results) 