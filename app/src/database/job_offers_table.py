"""
Job Offers Table

Handles all operations related to the job_offers table.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from .base_table import BaseTable


class JobOffersTable(BaseTable):
    """Handles job_offers table operations."""
    
    def create_table(self, cursor) -> None:
        """Create the job_offers table."""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS job_offers (
                id SERIAL PRIMARY KEY,
                company TEXT,
                role TEXT,
                base_salary NUMERIC,
                bonus NUMERIC,
                benefits TEXT,
                location TEXT,
                remote_policy VARCHAR(50),
                status VARCHAR(50) DEFAULT 'active',
                notes TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                application_id INTEGER,
                table_source VARCHAR(50) DEFAULT 'applications'
            )
        ''')
    
    def create_indexes(self, cursor) -> None:
        """Create indexes for job_offers table."""
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_offer_status ON job_offers(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_offer_company ON job_offers(company)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_offer_created_at ON job_offers(created_at)')
    
    def insert_offer(self, offer_data: Dict[str, Any]) -> Optional[int]:
        """Insert a new job offer."""
        try:
            query = """
                INSERT INTO job_offers (
                    company, role, base_salary, bonus, benefits, location,
                    remote_policy, status, notes, application_id, table_source
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """
            
            params = (
                offer_data.get('company'),
                offer_data.get('role'),
                offer_data.get('base_salary'),
                offer_data.get('bonus'),
                offer_data.get('benefits'),
                offer_data.get('location'),
                offer_data.get('remote_policy'),
                offer_data.get('status', 'active'),
                offer_data.get('notes'),
                offer_data.get('application_id'),
                offer_data.get('table_source', 'applications')
            )
            
            result = self.execute_query(query, params, fetch='one')
            return result[0] if result else None
            
        except Exception as e:
            self.log_error("insert_offer", e)
            return None
    
    def get_all_offers(self) -> List[Dict[str, Any]]:
        """Get all job offers."""
        try:
            query = "SELECT * FROM job_offers ORDER BY created_at DESC"
            results = self.execute_query(query, fetch='all')
            return [dict(row) for row in results] if results else []
            
        except Exception as e:
            self.log_error("get_all_offers", e)
            return []
    
    def get_offers_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get offers by status."""
        try:
            query = "SELECT * FROM job_offers WHERE status = %s ORDER BY created_at DESC"
            results = self.execute_query(query, (status,), fetch='all')
            return [dict(row) for row in results] if results else []
            
        except Exception as e:
            self.log_error("get_offers_by_status", e)
            return []
    
    def get_offers_by_company(self, company: str) -> List[Dict[str, Any]]:
        """Get offers by company."""
        try:
            query = "SELECT * FROM job_offers WHERE company ILIKE %s ORDER BY created_at DESC"
            results = self.execute_query(query, (f'%{company}%',), fetch='all')
            return [dict(row) for row in results] if results else []
            
        except Exception as e:
            self.log_error("get_offers_by_company", e)
            return []
    
    def update_offer(self, offer_id: int, update_data: Dict[str, Any]) -> bool:
        """Update a job offer."""
        try:
            query = """
                UPDATE job_offers 
                SET company = %s, role = %s, base_salary = %s, bonus = %s,
                    benefits = %s, location = %s, remote_policy = %s, 
                    status = %s, notes = %s
                WHERE id = %s
            """
            
            params = (
                update_data.get('company'),
                update_data.get('role'),
                update_data.get('base_salary'),
                update_data.get('bonus'),
                update_data.get('benefits'),
                update_data.get('location'),
                update_data.get('remote_policy'),
                update_data.get('status'),
                update_data.get('notes'),
                offer_id
            )
            
            self.execute_query(query, params)
            return True
            
        except Exception as e:
            self.log_error("update_offer", e)
            return False
    
    def delete_offer(self, offer_id: int) -> bool:
        """Delete a job offer."""
        try:
            query = "DELETE FROM job_offers WHERE id = %s"
            self.execute_query(query, (offer_id,))
            return True
            
        except Exception as e:
            self.log_error("delete_offer", e)
            return False
    
    def get_offer_stats(self) -> Dict[str, Any]:
        """Get job offer statistics."""
        try:
            query = """
                SELECT 
                    COUNT(*) as total_offers,
                    COUNT(*) FILTER (WHERE status = 'active') as active_offers,
                    COUNT(*) FILTER (WHERE status = 'accepted') as accepted_offers,
                    COUNT(*) FILTER (WHERE status = 'rejected') as rejected_offers,
                    AVG(base_salary) as avg_base_salary,
                    AVG(bonus) as avg_bonus,
                    COUNT(DISTINCT company) as unique_companies
                FROM job_offers
            """
            result = self.execute_query(query, fetch='one')
            
            if result:
                return {
                    'total_offers': result[0] or 0,
                    'active_offers': result[1] or 0,
                    'accepted_offers': result[2] or 0,
                    'rejected_offers': result[3] or 0,
                    'avg_base_salary': float(result[4]) if result[4] else 0,
                    'avg_bonus': float(result[5]) if result[5] else 0,
                    'unique_companies': result[6] or 0
                }
            
            return {}
            
        except Exception as e:
            self.log_error("get_offer_stats", e)
            return {}
