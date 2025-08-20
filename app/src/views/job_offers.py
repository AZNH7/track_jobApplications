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
        self._ensure_job_offers_table()
    
    def _ensure_job_offers_table(self):
        """Create job_offers table if it doesn't exist"""
        try:
            # Drop the existing table if it has the problematic foreign key constraint
            try:
                self.db_manager.execute_query("DROP TABLE IF EXISTS job_offers CASCADE")
            except Exception:
                pass
            
            # Create the table without foreign key constraint
            create_table_query = """
            CREATE TABLE IF NOT EXISTS job_offers (
                id SERIAL PRIMARY KEY,
                company VARCHAR(255) NOT NULL,
                role VARCHAR(255) NOT NULL,
                base_salary DECIMAL(10,2),
                bonus DECIMAL(10,2),
                benefits TEXT,
                location VARCHAR(255),
                remote_policy VARCHAR(50),
                status VARCHAR(50) DEFAULT 'active',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                application_id INTEGER,
                table_source VARCHAR(50) DEFAULT 'applications'
            )
            """
            self.db_manager.execute_query(create_table_query)
            
            # Create indexes for better performance
            self.db_manager.execute_query("CREATE INDEX IF NOT EXISTS idx_job_offers_application_id ON job_offers(application_id)")
            self.db_manager.execute_query("CREATE INDEX IF NOT EXISTS idx_job_offers_table_source ON job_offers(table_source)")
            self.db_manager.execute_query("CREATE INDEX IF NOT EXISTS idx_job_offers_status ON job_offers(status)")
                
        except Exception as e:
            st.error(f"Error creating job_offers table: {str(e)}")
    
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
    
    def get_applications_with_offers(self) -> pd.DataFrame:
        """Get applications that have 'offer' status"""
        try:
            # Query both applications and job_applications tables for offers
            applications_query = """
                SELECT 
                    id,
                    company,
                    position as title,
                    status,
                    applied_date,
                    source,
                    notes,
                    email_subject,
                    email_date,
                    job_id,
                    last_updated,
                    'applications' as table_source,
                    NULL as url,
                    NULL as location,
                    NULL as salary
                FROM applications
                WHERE LOWER(status) = 'offer'
            """
            
            job_applications_query = """
                SELECT 
                    id,
                    company,
                    position_title as title,
                    status,
                    applied_date,
                    source,
                    notes,
                    email_subject,
                    email_date,
                    job_listing_id as job_id,
                    added_date as last_updated,
                    'job_applications' as table_source,
                    url,
                    location,
                    salary
                FROM job_applications
                WHERE LOWER(status) = 'offer'
            """
            
            applications_results = self.db_manager.execute_query(applications_query, fetch='all')
            job_applications_results = self.db_manager.execute_query(job_applications_query, fetch='all')
            
            # Convert to DataFrames with explicit column names
            columns = [
                'id', 'company', 'title', 'status', 'applied_date', 'source', 
                'notes', 'email_subject', 'email_date', 'job_id', 'last_updated', 
                'table_source', 'url', 'location', 'salary'
            ]
            
            if applications_results:
                applications_df = pd.DataFrame(applications_results, columns=columns)
            else:
                applications_df = pd.DataFrame(columns=columns)
            
            if job_applications_results:
                job_applications_df = pd.DataFrame(job_applications_results, columns=columns)
            else:
                job_applications_df = pd.DataFrame(columns=columns)
            

            
            # Combine and sort by last_updated
            if applications_df.empty and job_applications_df.empty:
                return pd.DataFrame()
            
            all_applications = pd.concat([applications_df, job_applications_df], ignore_index=True)
            
            if not all_applications.empty:
                # Ensure all required columns exist
                required_columns = ['id', 'company', 'title', 'status', 'applied_date', 'source', 
                                  'notes', 'email_subject', 'email_date', 'job_id', 'last_updated', 
                                  'table_source', 'url', 'location', 'salary']
                for col in required_columns:
                    if col not in all_applications.columns:
                        all_applications[col] = None
                
                # Sort by last_updated if the column exists and has data
                if 'last_updated' in all_applications.columns and not all_applications['last_updated'].isna().all():
                    all_applications.sort_values('last_updated', ascending=False, inplace=True)
            
            return all_applications
            
        except Exception as e:
            st.error(f"Error fetching applications with offers: {str(e)}")
            return pd.DataFrame()
    
    def check_if_offer_exists(self, application_id: int, table_source: str) -> bool:
        """Check if an offer already exists for this application"""
        try:
            query = """
            SELECT id FROM job_offers 
            WHERE application_id = %s AND table_source = %s
            """
            result = self.db_manager.execute_query(query, (application_id, table_source), fetch='one')
            return result is not None
        except Exception:
            return False
    
    def add_offer_from_application(self, application_id: int, table_source: str, details: dict):
        """Add a new job offer from an application"""
        try:
            # Get application details
            if table_source == 'applications':
                query = """
                SELECT company, position, notes, applied_date, source
                FROM applications WHERE id = %s
                """
            else:
                query = """
                SELECT company, position_title, notes, applied_date, source, location, salary
                FROM job_applications WHERE id = %s
                """
            
            app_result = self.db_manager.execute_query(query, (application_id,), fetch='one')
            if not app_result:
                st.error("Application not found")
                return False
            
            # Prepare offer data
            offer_data = {
                'company': app_result[0],  # company
                'role': app_result[1],     # position/position_title
                'base_salary': details.get('base_salary'),
                'bonus': details.get('bonus'),
                'benefits': details.get('benefits'),
                'location': details.get('location') or (app_result[5] if table_source == 'job_applications' else None),
                'remote_policy': details.get('remote_policy'),
                'created_at': datetime.now(),
                'status': 'active',
                'notes': details.get('notes', '') or app_result[2] or '',  # Combine with original notes
                'application_id': application_id,
                'table_source': table_source
            }
            
            query = """
            INSERT INTO job_offers (
                company, role, base_salary, bonus, benefits, 
                location, remote_policy, created_at, status, notes, application_id, table_source
            ) VALUES (
                %(company)s, %(role)s, %(base_salary)s, %(bonus)s, %(benefits)s,
                %(location)s, %(remote_policy)s, %(created_at)s, %(status)s, %(notes)s, %(application_id)s, %(table_source)s
            )
            """
            self.db_manager.execute_query(query, offer_data)
            return True
        except Exception as e:
            st.error(f"Error adding offer: {str(e)}")
            return False
    
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
                notes = CASE WHEN %(notes)s IS NOT NULL THEN %(notes)s ELSE notes END
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
    
    def update_application_status(self, application_id: int, table_source: str, status: str):
        """Update application status in the original table"""
        try:
            if table_source == 'applications':
                query = """
                UPDATE applications 
                SET status = %(status)s, last_updated = CURRENT_TIMESTAMP
                WHERE id = %(application_id)s
                """
            else:  # job_applications
                query = """
                UPDATE job_applications 
                SET status = %(status)s, last_updated = CURRENT_TIMESTAMP
                WHERE id = %(application_id)s
                """
            
            self.db_manager.execute_query(query, {
                'application_id': application_id,
                'status': status
            })
            return True
        except Exception as e:
            st.error(f"Error updating application status: {str(e)}")
            return False
    
    def get_offers(self, status: str = None) -> pd.DataFrame:
        """Get job offers with optional status filter"""
        try:
            query = """
            SELECT * FROM job_offers
            WHERE status = %(status)s
            """ if status else "SELECT * FROM job_offers"
            
            result = self.db_manager.execute_query(query, {'status': status} if status else None, fetch='all')
            
            if result:
                # Convert result to list of dictionaries with proper column names
                columns = ['id', 'company', 'role', 'base_salary', 'bonus', 'benefits', 'location', 'remote_policy', 'status', 'notes', 'created_at', 'application_id', 'table_source']
                df = pd.DataFrame(result, columns=columns)
                return df
            else:
                return pd.DataFrame(columns=['id', 'company', 'role', 'base_salary', 'bonus', 'benefits', 'location', 'remote_policy', 'status', 'notes', 'created_at', 'application_id', 'table_source'])
        except Exception as e:
            st.error(f"Error fetching offers: {str(e)}")
            return pd.DataFrame(columns=['id', 'company', 'role', 'base_salary', 'bonus', 'benefits', 'location', 'remote_policy', 'status', 'notes', 'created_at', 'application_id', 'table_source'])
    
    def get_applications_by_status(self, status: str = None) -> pd.DataFrame:
        """Get applications with optional status filter"""
        try:
            if status:
                query = """
                SELECT 
                    id, company, position_title as role, NULL as base_salary, NULL as bonus, 
                    NULL as benefits, location, NULL as remote_policy, status, notes, 
                    added_date as created_at, id as application_id, 'job_applications' as table_source
                FROM job_applications
                WHERE LOWER(status) = %(status)s
                """
                result = self.db_manager.execute_query(query, {'status': status}, fetch='all')
            else:
                query = """
                SELECT 
                    id, company, position_title as role, NULL as base_salary, NULL as bonus, 
                    NULL as benefits, location, NULL as remote_policy, status, notes, 
                    added_date as created_at, id as application_id, 'job_applications' as table_source
                FROM job_applications
                WHERE LOWER(status) IN ('accepted', 'rejected', 'withdrawn', 'interview')
                """
                result = self.db_manager.execute_query(query, fetch='all')
            
            if result:
                columns = ['id', 'company', 'role', 'base_salary', 'bonus', 'benefits', 'location', 'remote_policy', 'status', 'notes', 'created_at', 'application_id', 'table_source']
                df = pd.DataFrame(result, columns=columns)
                return df
            else:
                return pd.DataFrame(columns=['id', 'company', 'role', 'base_salary', 'bonus', 'benefits', 'location', 'remote_policy', 'status', 'notes', 'created_at', 'application_id', 'table_source'])
        except Exception as e:
            st.error(f"Error fetching applications: {str(e)}")
            return pd.DataFrame(columns=['id', 'company', 'role', 'base_salary', 'bonus', 'benefits', 'location', 'remote_policy', 'status', 'notes', 'created_at', 'application_id', 'table_source'])
    
    def show_offer_comparison(self, offers: pd.DataFrame):
        """Show visual comparison of offers"""
        if offers.empty:
            st.info("No offers to compare.")
            return
        
        # Check if required columns exist
        required_columns = ['company', 'base_salary', 'bonus']
        missing_columns = [col for col in required_columns if col not in offers.columns]
        if missing_columns:
            st.error(f"Missing required columns for comparison: {missing_columns}")
            return
            
        # Prepare data for visualization
        comparison_data = []
        for _, offer in offers.iterrows():
            try:
                company_name = str(offer.get('company', 'Unknown Company'))
                base_salary = float(offer.get('base_salary', 0) or 0)
                bonus = float(offer.get('bonus', 0) or 0)
                
                comparison_data.extend([
                    {'Company': company_name, 'Type': 'Base Salary', 'Value': base_salary},
                    {'Company': company_name, 'Type': 'Bonus', 'Value': bonus}
                ])
            except (ValueError, TypeError) as e:
                st.warning(f"Error processing offer data: {e}")
                continue
        
        if not comparison_data:
            st.info("No valid offer data to compare.")
            return
        
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
        
        # Show applications with offer status that can be converted to detailed offers
        st.markdown("### 📋 Applications with Offers")
        applications_with_offers = self.get_applications_with_offers()
                
        if not applications_with_offers.empty:
            st.info(f"Found {len(applications_with_offers)} applications with 'offer' status. You can convert these to detailed job offers by filling in additional information.")
            

            
            for _, app in applications_with_offers.iterrows():
                try:
                    app_id = app.get('id')
                    table_source = app.get('table_source', 'job_applications')
                    title = app.get('title', 'Unknown Position')
                    company = app.get('company', 'Unknown Company')
                    
                    if app_id is None:
                        st.warning("Application ID is missing, skipping...")
                        continue
                    
                    offer_exists = self.check_if_offer_exists(app_id, table_source)
                    
                    if not offer_exists:
                        with st.expander(f"🎯 {title} at {company} - Convert to Detailed Offer"):
                            st.markdown(f"**Position:** {title}")
                            st.markdown(f"**Company:** {company}")
                            
                            if app.get('location'):
                                st.markdown(f"**Location:** {app['location']}")
                            
                            if app.get('salary'):
                                st.markdown(f"**Original Salary Info:** {app['salary']}")
                            
                            if app.get('notes'):
                                st.markdown(f"**Notes:** {app['notes']}")
                            
                            if app.get('url'):
                                st.link_button("🔗 View Original Job", app['url'])
                            
                            # Quick status change for applications
                            st.markdown("---")
                            st.markdown("**Quick Status Update:**")
                            
                            col1, col2 = st.columns([2, 1])
                            
                            with col1:
                                new_status = st.selectbox(
                                    "Change Application Status",
                                    ["offer", "accepted", "rejected", "withdrawn"],
                                    index=0,
                                    key=f"quick_status_{app_id}"
                                )
                            
                            with col2:
                                if st.button("Update Status", key=f"update_btn_{app_id}"):
                                    if self.update_application_status(app_id, table_source, new_status):
                                        st.success(f"Status updated to {new_status}!")
                                        st.rerun()
                            
                            st.markdown("---")
                            st.markdown("**Convert to Detailed Offer (Optional):**")
                            
                            with st.form(f"offer_form_{app_id}"):
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    base_salary = st.number_input("Base Salary (€)", min_value=0, key=f"salary_{app_id}")
                                    location = st.text_input("Location", value=app.get('location', ''), key=f"loc_{app_id}")
                                
                                with col2:
                                    bonus = st.number_input("Bonus (€)", min_value=0, key=f"bonus_{app_id}")
                                    remote_policy = st.selectbox(
                                        "Remote Policy",
                                        ["On-site", "Hybrid", "Remote"],
                                        key=f"remote_{app_id}"
                                    )
                                
                                benefits = st.text_area("Benefits", key=f"benefits_{app_id}")
                                additional_notes = st.text_area("Additional Notes", key=f"notes_{app_id}")
                                
                                if st.form_submit_button("Create Detailed Offer"):
                                    if base_salary > 0:
                                        details = {
                                            'base_salary': base_salary,
                                            'bonus': bonus,
                                            'benefits': benefits,
                                            'location': location,
                                            'remote_policy': remote_policy,
                                            'notes': additional_notes
                                        }
                                        if self.add_offer_from_application(app_id, table_source, details):
                                            st.success("Detailed offer created successfully!")
                                            st.rerun()
                                    else:
                                        st.warning("Base salary is required to create a detailed offer.")
                    else:
                        st.success(f"✅ {title} at {company} - Already converted to detailed offer")
                except Exception as e:
                    st.error(f"Error processing application: {str(e)}")
                    continue
        else:
            st.info("No applications with 'offer' status found. Update your application status to 'offer' in the Applications section to see them here.")
        
        st.markdown("---")
        
        # Add new offer form (manual entry)
        with st.expander("➕ Add New Offer (Manual Entry)", expanded=False):
            st.markdown("**Create a new job offer manually**")
            with st.form("new_offer_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    company = st.text_input("Company *", help="Company name offering the position")
                    base_salary = st.number_input("Base Salary (€) *", min_value=0, help="Annual base salary")
                    location = st.text_input("Location", help="Job location or 'Remote'")
                
                with col2:
                    role = st.text_input("Role/Position *", help="Job title or position name")
                    bonus = st.number_input("Bonus (€)", min_value=0, help="Annual bonus amount")
                    remote_policy = st.selectbox(
                        "Remote Policy",
                        ["On-site", "Hybrid", "Remote"],
                        help="Work arrangement policy"
                    )
                
                benefits = st.text_area("Benefits", help="Healthcare, vacation, stock options, etc.")
                notes = st.text_area("Notes", help="Additional details about the offer")
                
                submitted = st.form_submit_button("Add Offer", type="primary")
                
                if submitted:
                    if company and role and base_salary > 0:
                        details = {
                            'base_salary': base_salary,
                            'bonus': bonus,
                            'benefits': benefits,
                            'location': location,
                            'remote_policy': remote_policy,
                            'notes': notes
                        }
                        if self.add_offer(company, role, details):
                            st.success("✅ Offer added successfully!")
                            st.rerun()
                    else:
                        st.warning("Company, Role, and Base Salary are required fields.")
        
        # Show existing offers and applications
        st.markdown("### 📋 Current Offers")
        
        # Status filter
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "Active", "Accepted", "Rejected", "Expired", "Offer"]
        )
        
        # Get and display offers
        offers = self.get_offers(status_filter.lower() if status_filter != "All" else None)
        
        # Get applications with different statuses
        applications = self.get_applications_by_status(status_filter.lower() if status_filter != "All" else None)
        

        
        # Combine offers and applications
        all_items = pd.concat([offers, applications], ignore_index=True) if not offers.empty and not applications.empty else (
            offers if not offers.empty else applications
        )
        
        if not all_items.empty:
            # Show comparison (only for offers with salary data)
            offers_with_salary = offers[offers['base_salary'].notna() & (offers['base_salary'] > 0)]
            if not offers_with_salary.empty:
                st.markdown("### 📊 Offer Comparison")
                self.show_offer_comparison(offers_with_salary)
            
            # Show detailed list
            st.markdown("### 📝 Offer & Application Details")
            for _, item in all_items.iterrows():
                try:
                    company = item.get('company', 'Unknown Company')
                    role = item.get('role', 'Unknown Role')
                    item_id = item.get('id')
                    status = item.get('status', 'active')
                    table_source = item.get('table_source', 'job_offers')
                    
                    with st.expander(f"{company} - {role} ({status.title()})"):
                        col1, col2, col3 = st.columns(3)
                        
                        # Show salary info only for detailed offers
                        if table_source == 'job_offers' and item.get('base_salary'):
                            with col1:
                                base_salary = item.get('base_salary', 0) or 0
                                st.metric("Base Salary", f"€{base_salary:,.2f}")
                            
                            with col2:
                                bonus = item.get('bonus', 0) or 0
                                if bonus:
                                    st.metric("Bonus", f"€{bonus:,.2f}")
                                else:
                                    st.metric("Bonus", "€0")
                            
                            with col3:
                                total = base_salary + bonus
                                st.metric("Total", f"€{total:,.2f}")
                        else:
                            # For applications, show basic info
                            with col1:
                                st.metric("Type", "Application")
                            
                            with col2:
                                st.metric("Source", table_source.replace('_', ' ').title())
                            
                            with col3:
                                st.metric("Status", status.title())
                        
                        location = item.get('location', 'Not specified')
                        remote_policy = item.get('remote_policy', 'Not specified')
                        st.markdown(f"**Location:** {location}")
                        if remote_policy and remote_policy != 'Not specified':
                            st.markdown(f"**Remote Policy:** {remote_policy}")
                        
                        benefits = item.get('benefits')
                        if benefits:
                            st.markdown("**Benefits:**")
                            st.markdown(benefits)
                        
                        notes = item.get('notes')
                        if notes:
                            st.markdown("**Notes:**")
                            st.markdown(notes)
                        
                        # Status update section
                        st.markdown("---")
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            if table_source == 'job_offers':
                                # For detailed offers
                                status_options = ["active", "accepted", "rejected", "expired"]
                                current_index = status_options.index(status) if status in status_options else 0
                                new_status = st.selectbox(
                                    "Update Status",
                                    status_options,
                                    index=current_index,
                                    key=f"status_{item_id}"
                                )
                            else:
                                # For applications
                                status_options = ["offer", "accepted", "rejected", "withdrawn"]
                                current_index = status_options.index(status) if status in status_options else 0
                                new_status = st.selectbox(
                                    "Update Status",
                                    status_options,
                                    index=current_index,
                                    key=f"status_{item_id}"
                                )
                        
                        with col2:
                            if st.button("Update", key=f"update_{item_id}"):
                                if table_source == 'job_offers':
                                    if self.update_offer_status(item_id, new_status):
                                        st.success("Status updated!")
                                        st.rerun()
                                else:
                                    if self.update_application_status(item_id, table_source, new_status):
                                        st.success("Status updated!")
                                        st.rerun()
                except Exception as e:
                    st.error(f"Error displaying offer: {str(e)}")
                    continue
        else:
            st.info("No offers or applications found. Add your first offer using the form above or update application statuses to see them here.") 