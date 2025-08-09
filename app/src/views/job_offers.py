"""
Job offers view for Job Tracker
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px

from core.base_tracker import BaseJobTracker
from utils.ui_components import UIComponents

class JobOffersView(BaseJobTracker):
    def __init__(self):
        super().__init__()
        self.ui = UIComponents()
    
    def normalize_company_name(self, company_name: str) -> str:
        """Normalize company name for comparison"""
        if not company_name:
            return ""
        # Remove common suffixes and clean up
        suffixes = [" GmbH", " AG", " Inc.", " Ltd.", " Limited", " LLC"]
        name = company_name.strip().lower()
        for suffix in suffixes:
            name = name.replace(suffix.lower(), "")
        return name.strip()
    
    def calculate_offer_score(self, offer: dict) -> float:
        """Calculate a weighted score for an offer"""
        weights = {
            'base_salary': 0.4,
            'bonus': 0.1,
            'benefits': 0.15,
            'work_life_balance': 0.15,
            'growth_potential': 0.2
        }
        
        score = 0
        max_salary = self.get_max_salary_in_market()
        
        # Normalize and weight each component
        if offer.get('base_salary'):
            score += weights['base_salary'] * (offer['base_salary'] / max_salary)
        
        if offer.get('bonus'):
            score += weights['bonus'] * (offer['bonus'] / max_salary)
            
        if offer.get('benefits_score'):
            score += weights['benefits'] * offer['benefits_score']
            
        if offer.get('work_life_balance_score'):
            score += weights['work_life_balance'] * offer['work_life_balance_score']
            
        if offer.get('growth_score'):
            score += weights['growth_potential'] * offer['growth_score']
            
        return score
    
    def get_max_salary_in_market(self) -> float:
        """Get maximum salary in the market for normalization"""
        try:
            query = """
            SELECT MAX(CASE 
                WHEN salary ~ '^[0-9]+([,.][0-9]+)?$' 
                THEN REPLACE(REPLACE(salary, '.', ''), ',', '.')::float 
                ELSE 0 
            END) as max_salary
            FROM job_listings
            WHERE salary IS NOT NULL
            """
            result = self.db_manager.execute_query(query, fetch='one')
            return float(result[0]) if result else 100000
        except Exception:
            return 100000  # Default fallback
    
    def add_offer(self, company: str, role: str, details: dict):
        """Add a new job offer"""
        try:
            offer_data = {
                'company': company,
                'role': role,
                'base_salary': details.get('base_salary'),
                'bonus': details.get('bonus'),
                'benefits': details.get('benefits'),
                'location': details.get('location'),
                'remote_policy': details.get('remote_policy'),
                'created_at': datetime.now(),
                'status': 'active',
                'notes': details.get('notes', '')
            }
            
            query = """
            INSERT INTO job_offers (
                company, role, base_salary, bonus, benefits, 
                location, remote_policy, created_at, status, notes
            ) VALUES (
                %(company)s, %(role)s, %(base_salary)s, %(bonus)s, %(benefits)s,
                %(location)s, %(remote_policy)s, %(created_at)s, %(status)s, %(notes)s
            )
            """
            self.db_manager.execute_query(query, offer_data)
            return True
        except Exception as e:
            st.error(f"Error adding offer: {str(e)}")
            return False
    
    def update_offer_status(self, offer_id: int, status: str, notes: str = None):
        """Update job offer status"""
        try:
            query = """
            UPDATE job_offers 
            SET status = %(status)s, 
                notes = CASE WHEN %(notes)s IS NOT NULL THEN %(notes)s ELSE notes END,
                updated_at = NOW()
            WHERE id = %(offer_id)s
            """
            self.db_manager.execute_query(query, {
                'offer_id': offer_id,
                'status': status,
                'notes': notes
            })
            return True
        except Exception as e:
            st.error(f"Error updating offer: {str(e)}")
            return False
    
    def get_offers(self, status: str = None) -> pd.DataFrame:
        """Get job offers with optional status filter"""
        try:
            query = """
            SELECT * FROM job_offers
            WHERE status = %(status)s
            """ if status else "SELECT * FROM job_offers"
            
            result = self.db_manager.execute_query(query, {'status': status} if status else None)
            return pd.DataFrame(result)
        except Exception as e:
            st.error(f"Error fetching offers: {str(e)}")
            return pd.DataFrame()
    
    def show_offer_comparison(self, offers: pd.DataFrame):
        """Show visual comparison of offers"""
        if offers.empty:
            st.info("No offers to compare.")
            return
            
        # Prepare data for visualization
        comparison_data = []
        for _, offer in offers.iterrows():
            comparison_data.extend([
                {'Company': offer['company'], 'Type': 'Base Salary', 'Value': offer['base_salary']},
                {'Company': offer['company'], 'Type': 'Bonus', 'Value': offer['bonus'] or 0}
            ])
        
        comparison_df = pd.DataFrame(comparison_data)
        
        # Create stacked bar chart
        fig = px.bar(
            comparison_df,
            x='Company',
            y='Value',
            color='Type',
            title='Compensation Comparison',
            labels={'Value': 'Amount (€)'},
            barmode='group'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    def show(self):
        """Show job offers interface"""
        self.ui.show_header("Job Offers", "💰")
        
        # Add new offer form
        with st.expander("➕ Add New Offer"):
            with st.form("new_offer_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    company = st.text_input("Company")
                    base_salary = st.number_input("Base Salary (€)", min_value=0)
                    location = st.text_input("Location")
                
                with col2:
                    role = st.text_input("Role")
                    bonus = st.number_input("Bonus (€)", min_value=0)
                    remote_policy = st.selectbox(
                        "Remote Policy",
                        ["On-site", "Hybrid", "Remote"]
                    )
                
                benefits = st.text_area("Benefits")
                notes = st.text_area("Notes")
                
                if st.form_submit_button("Add Offer"):
                    if company and role:
                        details = {
                            'base_salary': base_salary,
                            'bonus': bonus,
                            'benefits': benefits,
                            'location': location,
                            'remote_policy': remote_policy,
                            'notes': notes
                        }
                        if self.add_offer(company, role, details):
                            st.success("Offer added successfully!")
                    else:
                        st.warning("Company and Role are required.")
        
        # Show existing offers
        st.markdown("### 📋 Current Offers")
        
        # Status filter
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "Active", "Accepted", "Rejected", "Expired"]
        )
        
        # Get and display offers
        offers = self.get_offers(status_filter.lower() if status_filter != "All" else None)
        
        if not offers.empty:
            # Show comparison
            st.markdown("### 📊 Offer Comparison")
            self.show_offer_comparison(offers)
            
            # Show detailed list
            st.markdown("### 📝 Offer Details")
            for _, offer in offers.iterrows():
                with st.expander(f"{offer['company']} - {offer['role']}"):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Base Salary", f"€{offer['base_salary']:,.2f}")
                    
                    with col2:
                        if offer['bonus']:
                            st.metric("Bonus", f"€{offer['bonus']:,.2f}")
                    
                    with col3:
                        st.metric("Total", f"€{(offer['base_salary'] + (offer['bonus'] or 0)):,.2f}")
                    
                    st.markdown(f"**Location:** {offer['location']}")
                    st.markdown(f"**Remote Policy:** {offer['remote_policy']}")
                    
                    if offer['benefits']:
                        st.markdown("**Benefits:**")
                        st.markdown(offer['benefits'])
                    
                    if offer['notes']:
                        st.markdown("**Notes:**")
                        st.markdown(offer['notes'])
                    
                    # Status update
                    new_status = st.selectbox(
                        "Status",
                        ["Active", "Accepted", "Rejected", "Expired"],
                        index=["Active", "Accepted", "Rejected", "Expired"].index(offer['status'].capitalize())
                    )
                    
                    if new_status.lower() != offer['status']:
                        if st.button(f"Update Status to {new_status}", key=f"status_{offer['id']}"):
                            if self.update_offer_status(offer['id'], new_status.lower()):
                                st.success("Status updated successfully!")
                                st.rerun()
        else:
            st.info("No offers found. Add your first offer using the form above.") 