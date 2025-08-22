"""
Job Applications Table

Handles all operations related to the job_applications table.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from .base_table import BaseTable


class JobApplicationsTable(BaseTable):
    """Handles job_applications table operations."""
    
    def create_table(self, cursor) -> None:
        """Create the job_applications table."""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS job_applications (
                id SERIAL PRIMARY KEY,
                job_listing_id INTEGER,
                position_title TEXT NOT NULL,
                company TEXT NOT NULL,
                location TEXT,
                salary TEXT,
                url TEXT NOT NULL,
                source TEXT,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                applied_date TIMESTAMP,
                status TEXT DEFAULT 'saved',
                notes TEXT,
                priority INTEGER DEFAULT 3,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (job_listing_id) REFERENCES job_listings (id),
                UNIQUE(url)
            )
        ''')
    
    def create_indexes(self, cursor) -> None:
        """Create indexes for job_applications table."""
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_applications_job_id ON job_applications(job_listing_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_applications_status ON job_applications(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_applications_company ON job_applications(company)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_applications_added_date ON job_applications(added_date)')
    
    def insert_application(self, application_data: Dict[str, Any]) -> Optional[int]:
        """Insert a new job application."""
        try:
            query = """
                INSERT INTO job_applications (
                    job_listing_id, position_title, company, location, salary, 
                    url, source, added_date, applied_date, status, notes, priority
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (url) DO UPDATE SET
                    position_title = EXCLUDED.position_title,
                    company = EXCLUDED.company,
                    location = EXCLUDED.location,
                    salary = EXCLUDED.salary,
                    source = EXCLUDED.source,
                    status = EXCLUDED.status,
                    notes = EXCLUDED.notes,
                    priority = EXCLUDED.priority,
                    last_updated = CURRENT_TIMESTAMP
                RETURNING id
            """
            
            params = (
                application_data.get('job_listing_id'),
                application_data.get('position_title'),
                application_data.get('company'),
                application_data.get('location'),
                application_data.get('salary'),
                application_data.get('url'),
                application_data.get('source'),
                application_data.get('added_date', datetime.now()),
                application_data.get('applied_date'),
                application_data.get('status', 'saved'),
                application_data.get('notes'),
                application_data.get('priority', 3)
            )
            
            result = self.execute_query(query, params, fetch='one')
            return result[0] if result else None
            
        except Exception as e:
            self.log_error("insert_application", e)
            return None
    
    def get_all_applications(self) -> List[Dict[str, Any]]:
        """Get all job applications."""
        try:
            query = """
                SELECT * FROM job_applications 
                ORDER BY added_date DESC
            """
            results = self.execute_query(query, fetch='all')
            return [dict(row) for row in results] if results else []
            
        except Exception as e:
            self.log_error("get_all_applications", e)
            return []
    
    def get_applications_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get applications by status."""
        try:
            query = "SELECT * FROM job_applications WHERE status = %s ORDER BY added_date DESC"
            results = self.execute_query(query, (status,), fetch='all')
            return [dict(row) for row in results] if results else []
            
        except Exception as e:
            self.log_error("get_applications_by_status", e)
            return []
    
    def update_application_status(self, application_id: int, status: str, notes: str = None) -> bool:
        """Update application status."""
        try:
            query = """
                UPDATE job_applications 
                SET status = %s, notes = %s, last_updated = CURRENT_TIMESTAMP
                WHERE id = %s
            """
            self.execute_query(query, (status, notes, application_id))
            return True
            
        except Exception as e:
            self.log_error("update_application_status", e)
            return False
    
    def delete_application(self, application_id: int) -> bool:
        """Delete a job application."""
        try:
            query = "DELETE FROM job_applications WHERE id = %s"
            self.execute_query(query, (application_id,))
            return True
            
        except Exception as e:
            self.log_error("delete_application", e)
            return False
    
    def get_application_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Get application by URL."""
        try:
            query = "SELECT * FROM job_applications WHERE url = %s"
            result = self.execute_query(query, (url,), fetch='one')
            return dict(result) if result else None
            
        except Exception as e:
            self.log_error("get_application_by_url", e)
            return None
