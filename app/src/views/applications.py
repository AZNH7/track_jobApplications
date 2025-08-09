"""
Applications management view for Job Tracker
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo

from core.base_tracker import BaseJobTracker
from utils.ui_components import UIComponents
from utils.data_loader import DataLoader

class ApplicationsView(BaseJobTracker):
    def __init__(self):
        super().__init__()
        self.ui = UIComponents()
        self.data_loader = DataLoader(self.db_manager)
    
    def get_status_badge(self, status):
        """Returns an HTML badge for the given status."""
        status_map = {
            "saved": ("📄", "#D3D3D3", "black"),
            "applied": ("➡️", "#ADD8E6", "black"),
            "interview": ("💬", "#FFFFE0", "black"),
            "rejected": ("❌", "#FFB6C1", "black"),
            "offer": ("✅", "#90EE90", "black"),
            "withdrawn": ("👋", "#D3D3D3", "black")
        }
        icon, bg_color, text_color = status_map.get(status.lower(), ("❓", "#FFFFFF", "black"))

        badge_style = f"background-color: {bg_color}; color: {text_color}; padding: 2px 10px; border-radius: 15px; font-size: 14px; display: inline-block; margin-left: 10px;"
        return f'<span style="{badge_style}">{icon} {status.title()}</span>'

    def show(self):
        """Show job applications management interface"""
        self.ui.show_header("Job Applications", "📝")
        
        # Load applications data
        applications_df = self.data_loader.load_applications_data()
        
        if applications_df.empty:
            st.info("No job applications found.")
            return
        
        # Status filter
        st.markdown("### 🔎 Filters")
        filter_cols = st.columns(3)

        with filter_cols[0]:
            status_filter = st.selectbox(
                "Filter by Status",
                ["All", "saved", "applied", "interview", "rejected", "offer", "withdrawn"],
                index=0,
                key="status_filter"
            )

        with filter_cols[1]:
            start_date = st.date_input("Start Date", value=None, key="start_date_filter")

        with filter_cols[2]:
            end_date = st.date_input("End Date", value=None, key="end_date_filter")
        
        # Filter data
        filtered_data = applications_df
        if status_filter != "All":
            filtered_data = filtered_data[filtered_data['status'] == status_filter]

        if start_date and end_date:
            # Convert date columns to datetime objects, coercing errors
            filtered_data['applied_date'] = pd.to_datetime(filtered_data['applied_date'], errors='coerce', utc=True)
            filtered_data['email_date'] = pd.to_datetime(filtered_data['email_date'], errors='coerce', utc=True)

            # Convert filter dates to datetime objects
            start_datetime = pd.to_datetime(start_date, utc=True)
            end_datetime = pd.to_datetime(end_date, utc=True) + pd.Timedelta(days=1)

            # Create a boolean mask for filtering
            date_mask = (
                (filtered_data['applied_date'].notna() & (filtered_data['applied_date'] >= start_datetime) & (filtered_data['applied_date'] < end_datetime)) |
                (filtered_data['email_date'].notna() & (filtered_data['email_date'] >= start_datetime) & (filtered_data['email_date'] < end_datetime))
            )
            filtered_data = filtered_data[date_mask]

        # Show metrics
        st.markdown("### 📊 Application Metrics")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total = len(filtered_data)
            self.ui.show_metric_card("Total Applications", total)
        
        with col2:
            active = len(filtered_data[filtered_data['status'].isin(['saved', 'applied', 'interview'])])
            self.ui.show_metric_card("Active Applications", active)
        
        with col3:
            success_rate = len(filtered_data[filtered_data['status'] == 'offer']) / total if total > 0 else 0
            self.ui.show_metric_card("Success Rate", f"{success_rate:.1%}")
        
        # Show applications
        st.markdown("### 📋 Applications")
        
        for _, app in filtered_data.iterrows():
            position = app.get('position', app.get('title', 'No Title'))
            company = app.get('company', 'No Company')
            status = app.get('status', 'saved')

            title_html = f"**{position}** at **{company}** {self.get_status_badge(status)}"
            st.markdown(title_html, unsafe_allow_html=True)

            with st.expander("View Details", expanded=False):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    # Show source indicator
                    table_source = app.get('table_source', 'job_applications')
                    source_icon = "📧" if table_source == 'applications' or pd.notna(app.get('email_date')) else "💼"
                    source_text = "Email Tracked" if table_source == 'applications' else "Manual Entry"
                    if pd.notna(app.get('email_date')):
                        source_text += " (Merged)"

                    # Format email date if available
                    email_date_info = ""
                    email_date = app.get('email_date')

                    if pd.notna(email_date):
                        try:
                            if hasattr(email_date, 'astimezone') and email_date.tzinfo:
                                german_tz = ZoneInfo('Europe/Berlin')
                                email_date_local = email_date.astimezone(german_tz)
                                email_date_info = f"**Email Date:** {email_date_local.strftime('%Y-%m-%d %H:%M')} (CET/CEST)"
                            elif hasattr(email_date, 'strftime'):
                                email_date_info = f"**Email Date:** {email_date.strftime('%Y-%m-%d %H:%M')}"
                            else:
                                email_date_info = f"**Email Date:** {str(email_date)}"
                        except Exception as e:
                            email_date_info = f"**Email Date:** Error formatting date: {str(e)}"
                    elif app.get('email_subject'):
                        email_date_info = f"**Email Date:** Not available (subject: {app.get('email_subject', '')[:30]}...)"

                    # Format applied date
                    applied_date = app.get('applied_date')
                    applied_date_str = "Not yet"
                    if applied_date and not pd.isna(applied_date):
                        try:
                            if hasattr(applied_date, 'strftime'):
                                applied_date_str = applied_date.strftime('%Y-%m-%d')
                            else:
                                applied_date_str = str(applied_date)
                        except:
                            applied_date_str = str(applied_date)
                    
                    st.markdown(f"""
                    **Applied:** {applied_date_str}  
                    **Source:** {source_icon} {source_text}  
                    {email_date_info}
                    """)

                    notes = st.text_area(
                        "Notes",
                        value=app.get('notes', '') or "",
                        key=f"notes_{app['id']}"
                    )
                    
                    if st.button("Save Notes", key=f"save_notes_{app['id']}"):
                        self.update_application_status(app['id'], status, notes, table_source=app.get('table_source', 'job_applications'))
                        st.rerun()

                with col2:
                    st.markdown("**Actions**")
                    status_options = ['saved', 'applied', 'interview', 'rejected', 'offer', 'withdrawn']
                    current_status_idx = status_options.index(status) if status in status_options else 0
                    
                    new_status = st.selectbox(
                        "Status",
                        status_options,
                        key=f"status_{app['id']}",
                        index=current_status_idx,
                        format_func=lambda x: x.title()
                    )
                    
                    if new_status.lower() != status:
                        table_source = app.get('table_source', 'job_applications')
                        self.update_application_status(app['id'], new_status.lower(), table_source=table_source)
                        st.rerun()
                    
                    # Add URL button if URL is available
                    if app.get('url'):
                        st.link_button("🔗 View Job", app['url'], use_container_width=True)
                    
                    # Add merge button for saved applications
                    if app.get('status') == 'saved':
                        if st.button("🔗 Find & Merge Email", key=f"merge_{app['id']}", use_container_width=True):
                            self.find_and_merge_application_emails(app)
                        
                        # Add unsave button for saved jobs
                        if st.button("📤 Unsave Job", key=f"unsave_{app['id']}", use_container_width=True, type="secondary"):
                            self.unsave_job(app)
                        
                        # Add info about unsave vs remove
                        st.info("💡 **Unsave** moves job back to Job Browser. **Remove** deletes it permanently.")
                    
                    # Remove button (for all statuses)
                    if st.button("🗑️ Remove", key=f"remove_{app['id']}", use_container_width=True, type="primary"):
                        table_source = app.get('table_source', 'job_applications')
                        self.remove_application(app['id'], table_source)
    
    def update_application_status(self, application_id, status, notes=None, table_source='job_applications'):
        """Update application status and notes"""
        try:
            self.db_manager.update_application(application_id, status, notes, table_source)
            return True
        except Exception as e:
            st.error(f"Error updating application: {str(e)}")
            return False
    
    def remove_application(self, app_id, table_source='job_applications'):
        """Remove an application from the database."""
        try:
            self.db_manager.delete_application(app_id, table_source)
            st.success("Application removed successfully!")
            st.rerun()
        except Exception as e:
            st.error(f"Error removing application: {e}")

    def unsave_job(self, app):
        """Unsave a job - remove it from applications and make it available again."""
        try:
            app_id = app.get('id')
            job_url = app.get('url')
            
            if not job_url:
                st.error("Cannot unsave job: No URL found")
                return
            
            # Remove from job_applications table
            self.db_manager.delete_application(app_id, 'job_applications')
            
            # Also remove from ignored_jobs if it's there (to make it available again)
            try:
                self.db_manager.execute_query(
                    "DELETE FROM ignored_jobs WHERE url = %s",
                    (job_url,)
                )
            except Exception as e:
                # Ignore errors here - job might not be in ignored_jobs
                pass
            
            st.success(f"✅ Job unsaved successfully! '{app.get('position', 'Unknown')}' at '{app.get('company', 'Unknown')}' is now available again in the Job Browser.")
            st.rerun()
            
        except Exception as e:
            st.error(f"Error unsaving job: {e}")

    def find_and_merge_application_emails(self, app):
        """Find matching emails for a saved application and merge them"""
        try:
            company = app.get('company', '').strip()
            position = app.get('position', app.get('title', '')).strip()
            
            if not company:
                st.warning("⚠️ Cannot search for emails: Missing company name")
                return
            
            # Search for emails with similar company and position
            search_query = """
                SELECT id, subject, sender, date, company, position_title, category
                FROM email_analysis 
                WHERE (
                    LOWER(company) LIKE LOWER(%s) OR 
                    LOWER(sender) LIKE LOWER(%s)
                ) AND (
                    LOWER(position_title) LIKE LOWER(%s) OR
                    LOWER(subject) LIKE LOWER(%s) OR
                    LOWER(subject) LIKE LOWER(%s)
                )
                ORDER BY date DESC
                LIMIT 10
            """
            
            # Create search patterns
            company_pattern = f"%{company}%"
            position_pattern = f"%{position}%" if position else "%"
            company_sender_pattern = f"%{company.split()[0] if company.split() else company}%"
            
            matching_emails = self.db_manager.execute_query(
                search_query, 
                (company_pattern, company_sender_pattern, position_pattern, position_pattern, company_pattern),
                fetch='all'
            )
            
            if matching_emails:
                st.success(f"🔍 Found {len(matching_emails)} potentially matching emails!")
                
                # Display matching emails for selection
                st.markdown("**Select emails to merge with this application:**")
                
                selected_emails = []
                for email in matching_emails:
                    # Format email date
                    email_date = email[3]  # date column
                    if email_date:
                        if hasattr(email_date, 'astimezone'):
                            german_tz = ZoneInfo('Europe/Berlin')
                            email_date_local = email_date.astimezone(german_tz)
                            date_str = email_date_local.strftime('%Y-%m-%d %H:%M')
                        else:
                            date_str = str(email_date)
                    else:
                        date_str = "Unknown date"
                    
                    if st.checkbox(
                        f"📧 {date_str} - **{email[5] or 'N/A'}** at **{email[4] or 'N/A'}** from *{email[2]}*",
                        key=f"email_select_{email[0]}_{app['id']}",
                        help=f"Subject: {email[1]}"
                    ):
                        selected_emails.append(email)
                
                if selected_emails:
                    if st.button(f"🔗 Merge {len(selected_emails)} emails with application", key=f"confirm_merge_{app['id']}"):
                        self.merge_emails_with_application(app, selected_emails)
                        st.rerun()
                else:
                    st.info("Select one or more emails to merge with this application")
            else:
                st.info(f"🔍 No matching emails found for '{company}' - '{position}'")
                st.markdown("**Search tips:**")
                st.markdown("- Make sure the company name matches the email sender")
                st.markdown("- Check if emails were analyzed in the Email Analyzer section")
                
        except Exception as e:
            st.error(f"Error searching for emails: {str(e)}")
    
    def merge_emails_with_application(self, app, selected_emails):
        """Merge selected emails with the application"""
        try:
            # Get the most recent email for date and subject
            latest_email = None
            if selected_emails:
                latest_email = max(selected_emails, key=lambda email: email[3] or datetime.min)

            if not latest_email:
                st.error("No email selected to merge.")
                return

            latest_email_date = latest_email[3]
            latest_email_subject = latest_email[1]

            # Update application status to 'applied' and set dates and notes
            update_query = """
                UPDATE job_applications 
                SET status = 'applied', 
                    applied_date = %s,
                    email_date = %s,
                    email_subject = %s,
                    notes = COALESCE(notes, '') || %s,
                    last_updated = NOW()
                WHERE id = %s
            """
            
            # Create notes about merged emails
            email_subjects = [email[1] for email in selected_emails]
            merge_notes = f"\n\nMerged with {len(selected_emails)} emails:\n" + "\n".join([f"- {subj[:100]}" for subj in email_subjects])
            
            self.db_manager.execute_query(
                update_query, 
                (latest_email_date, latest_email_date, latest_email_subject, merge_notes, app['id'])
            )
            
            st.success(f"✅ Successfully merged {len(selected_emails)} emails with application!")
            st.success(f"📝 Application status updated to 'Applied' with date: {latest_email_date.strftime('%Y-%m-%d') if latest_email_date else 'Unknown'}")
            
        except Exception as e:
            st.error(f"Error merging emails: {str(e)}")
            import traceback
            st.code(traceback.format_exc()) 