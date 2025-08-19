"""
Enhanced UI components for Job Tracker
"""

import streamlit as st
from typing import Optional, Dict, Any, List
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

class UIComponents:
    def __init__(self):
        self.apply_custom_css()
    
    def apply_custom_css(self):
        """Apply custom CSS styling"""
        st.markdown("""
        <style>
        /* Main header styling */
        .main-header {
            font-size: 2.5rem;
            color: #1f77b4;
            text-align: center;
            margin-bottom: 2rem;
        }

        /* Responsive font sizes */
        @media (max-width: 768px) {
            .main-header {
                font-size: 1.8rem;
            }
            .metric-card, .success-card, .warning-card {
                padding: 0.75rem;
                margin-bottom: 0.5rem;
            }
        }

        /* Enhanced card styling */
        .metric-card {
            background-color: #f0f2f6;
            padding: 1rem;
            border-radius: 0.5rem;
            border-left: 4px solid #1f77b4;
            margin-bottom: 1rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: transform 0.2s ease;
        }

        .metric-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }

        .success-card {
            background-color: #d4edda;
            padding: 1rem;
            border-radius: 0.5rem;
            border-left: 4px solid #28a745;
            margin-bottom: 1rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .warning-card {
            background-color: #fff3cd;
            padding: 1rem;
            border-radius: 0.5rem;
            border-left: 4px solid #ffc107;
            margin-bottom: 1rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        /* Progress indicators */
        .progress-container {
            background-color: #f8f9fa;
            border-radius: 0.5rem;
            padding: 1rem;
            margin: 1rem 0;
            border: 1px solid #e9ecef;
        }

        .progress-bar {
            background-color: #007bff;
            height: 20px;
            border-radius: 10px;
            transition: width 0.3s ease;
        }

        /* Enhanced button styling */
        .stButton > button {
            border-radius: 0.5rem;
            border: none;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: all 0.2s ease;
        }

        .stButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }

        /* Mobile-responsive tables */
        @media (max-width: 768px) {
            .dataframe {
                font-size: 0.8rem;
            }
            .stSelectbox {
                min-width: auto;
            }
        }

        /* Real-time indicator */
        .real-time-indicator {
            display: inline-block;
            width: 8px;
            height: 8px;
            background-color: #28a745;
            border-radius: 50%;
            animation: pulse 2s infinite;
            margin-right: 8px;
        }

        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }

        /* Export/Import section styling */
        .export-import-section {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1.5rem;
            border-radius: 0.5rem;
            margin: 1rem 0;
        }

        .export-import-section h3 {
            color: white;
            margin-bottom: 1rem;
        }

        /* Cache status indicator */
        .cache-status {
            font-size: 0.8rem;
            color: #6c757d;
            margin-left: 0.5rem;
        }
        </style>
        """, unsafe_allow_html=True)
    
    def show_header(self, title: str, icon: str = "💼"):
        """Show page header with icon"""
        st.markdown(f"""
        <div class="main-header">
            {icon} {title}
        </div>
        """, unsafe_allow_html=True)
    
    def show_metric_card(self, title: str, value: Any, description: Optional[str] = None):
        """Show metric card with optional description"""
        st.markdown(f"""
        <div class="metric-card">
            <h3>{title}</h3>
            <h2>{value}</h2>
            {f"<p>{description}</p>" if description else ""}
        </div>
        """, unsafe_allow_html=True)
    
    def show_success_card(self, message: str):
        """Show success message card"""
        st.markdown(f"""
        <div class="success-card">
            ✅ {message}
        </div>
        """, unsafe_allow_html=True)
    
    def show_warning_card(self, message: str):
        """Show warning message card"""
        st.markdown(f"""
        <div class="warning-card">
            ⚠️ {message}
        </div>
        """, unsafe_allow_html=True)
    
    def show_progress_container(self, message: str, progress: float):
        """Show progress container with message"""
        st.markdown(f"""
        <div class="progress-container">
            <p>{message}</p>
            <div class="progress-bar" style="width: {progress * 100}%"></div>
        </div>
        """, unsafe_allow_html=True)
    
    def show_real_time_indicator(self, message: str):
        """Show real-time indicator with message"""
        st.markdown(f"""
        <div>
            <span class="real-time-indicator"></span>
            {message}
        </div>
        """, unsafe_allow_html=True)
    
    def show_cache_status(self, status: Dict[str, Any]):
        """Show cache status indicator"""
        if status['valid']:
            st.markdown(f"""
            <div class="cache-status">
                🔄 Cache valid for {status['expires_in']}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="cache-status">
                🔄 Cache expired
            </div>
            """, unsafe_allow_html=True)
    
    def show_export_import_section(self, title: str):
        """Show export/import section"""
        st.markdown(f"""
        <div class="export-import-section">
            <h3>{title}</h3>
        </div>
        """, unsafe_allow_html=True)
    
    def create_trend_chart(self, data, x, y, title: str):
        """Create trend chart using plotly"""
        fig = px.line(data, x=x, y=y, title=title)
        fig.update_layout(
            template="plotly_white",
            xaxis_title=x,
            yaxis_title=y,
            showlegend=True
        )
        return fig
    
    def create_bar_chart(self, data, x, y, title: str, orientation: str = 'v'):
        """Create bar chart using plotly"""
        fig = px.bar(
            data,
            x=x,
            y=y,
            title=title,
            orientation=orientation
        )
        fig.update_layout(
            template="plotly_white",
            showlegend=True
        )
        return fig
    
    def create_pie_chart(self, data, names, values, title: str):
        """Create pie chart using plotly"""
        fig = px.pie(
            data,
            names=names,
            values=values,
            title=title
        )
        fig.update_layout(
            template="plotly_white",
            showlegend=True
        )
        return fig

    def get_modal(self, title: str):
        """
        Creates and returns a modal dialog.
        A simple wrapper around st.dialog.
        """
        return st.dialog(title)
        
    def show_table(self, df: pd.DataFrame, columns: Optional[List[str]] = None):
        """
        Shows a table using streamlit's data frame display capabilities.
        If columns are specified, only those columns are displayed.
        """
        st.write(df.head() if columns is None else df[columns].head())

        with st.expander("Show Details"):
            st.json(df.to_dict()) 