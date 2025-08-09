import psycopg2
from psycopg2.pool import SimpleConnectionPool
from psycopg2.extras import DictCursor
import threading
import time
from contextlib import contextmanager
from typing import Optional, Any, List, Dict, Union, Tuple, cast
import logging
import os
from sqlalchemy import create_engine
from dotenv import load_dotenv
import json
from datetime import datetime, timezone

# Thread-local storage for database manager instance
_db_manager_local = threading.local()

class PostgreSQLManager:
    """
    PostgreSQL database manager with connection pooling
    Provides robust concurrent access with proper transaction handling
    """
    
    def __init__(self, host: str = None, port: int = None, dbname: str = None, user: str = None, password: str = None, env: str = 'docker'):
        """Initialize database connection"""
        self.env = env
        
        # Get configuration
        from config_manager import get_config_manager
        config_manager = get_config_manager()
        db_config = config_manager.get_setting('database', {})
        
        # Read from environment variables first, then config, then provided defaults
        actual_host = os.getenv('POSTGRES_HOST', host or db_config.get('host', 'localhost'))
        actual_port = int(os.getenv('POSTGRES_PORT', str(port or db_config.get('port', 5432))))
        actual_dbname = os.getenv('POSTGRES_DB', dbname or db_config.get('database', 'jobtracker'))
        actual_user = os.getenv('POSTGRES_USER', user or db_config.get('user', 'jobtracker'))
        actual_password = os.getenv('POSTGRES_PASSWORD', password or db_config.get('password', 'jobtracker'))
        
        self.connection_params = {
            'host': actual_host,
            'port': actual_port,
            'dbname': actual_dbname,
            'user': actual_user,
            'password': actual_password
        }
        self.connection_pool: Optional[psycopg2.pool.ThreadedConnectionPool] = None
        self.logger = logging.getLogger(__name__)
        self._create_connection_pool()
        self.ensure_tables_exist()
        self._sqlalchemy_engine = None
        
    def ensure_tables_exist(self) -> bool:
        """Ensure all required tables exist in the database and run migrations"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    conn.rollback()  # Reset any aborted transaction
                    
                    self._create_tables(cursor)
                    self._run_migrations(cursor)  # New migration function
                    conn.commit()
            self.logger.info("✅ Database tables and migrations are up to date.")
            return True
        except Exception as e:
            self.logger.error(f"Error ensuring tables exist: {e}", exc_info=True)
            try:
                with self.get_connection() as conn:
                    conn.rollback()
            except:
                pass
            return False

    def _get_schema_version(self, cursor) -> int:
        """Get the current schema version from the database"""
        try:
            cursor.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
            version = cursor.fetchone()
            return version[0] if version else 0
        except psycopg2.errors.UndefinedTable:
            # If table doesn't exist, schema is at version 0
            return 0
            
    def _set_schema_version(self, cursor, version: int):
        """Set the new schema version"""
        cursor.execute("INSERT INTO schema_version (version, migrated_at) VALUES (%s, %s)", (version, datetime.now(timezone.utc)))

    def _run_migrations(self, cursor):
        """Run all pending database migrations"""
        # First, ensure the schema_version table exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                migrated_at TIMESTAMP WITH TIME ZONE NOT NULL
            );
        """)

        current_version = self._get_schema_version(cursor)
        
        # --- Migration Registry ---
        migrations = {
            1: self._migrate_v1_add_missing_columns,
        }
        
        self.logger.info(f"Current database schema version: {current_version}")

        for version, migration_func in sorted(migrations.items()):
            if current_version < version:
                self.logger.info(f"Applying migration for version {version}...")
                migration_func(cursor)
                self._set_schema_version(cursor, version)
                self.logger.info(f"✅ Migrated to version {version}")

    def execute_query(self, query: str, params: Optional[Union[Tuple, List, Dict]] = None, 
                     fetch: Optional[str] = None) -> Optional[Union[List, Dict, Tuple]]:
        """Execute a database query"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor if fetch else None) as cur:
                    cur.execute(query, params)
                    
                    if fetch == 'all':
                        return cur.fetchall()
                    if fetch == 'one':
                        return cur.fetchone()
                    
                    conn.commit()
                    return None
        except Exception as e:
            self.logger.error(f"Error executing query: {e}")
            raise

    def batch_insert_emails(self, batch_data: List[Dict[str, Any]]) -> int:
        """Insert a batch of email data into the database"""
        if not batch_data:
            return 0
        
        inserted_count = 0
        for data in batch_data:
            try:
                query = """
                    INSERT INTO email_analysis (
                        id, date, subject, sender, company, category, 
                        body_preview, application_id, position_title, email_hash
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    ) ON CONFLICT (email_hash) DO NOTHING
                """
                params = (
                    str(data.get('id', '')),
                    data.get('internalDate') or data.get('date'),  # Use internalDate if available, fallback to date
                    str(data.get('subject', '')),
                    str(data.get('sender', '')),
                    str(data.get('company', '')),
                    str(data.get('category', '')),
                    str(data.get('body_preview', '')),
                    str(data.get('application_id', '')),
                    str(data.get('position_title', '')),
                    str(data.get('email_hash', data.get('hash', '')))
                )
                self.execute_query(query, params)
                inserted_count += 1
            except Exception as e:
                self.logger.error(f"Error inserting email data: {e}")
                continue
        
        return inserted_count

    def close(self) -> None:
        """Close all database connections"""
        if self.connection_pool:
            self.connection_pool.closeall()
            self.connection_pool = None

    def get_cached_job_details(self, job_url: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached job details from the database.
        Returns None if not found, if cache is invalid, or if it's a 403 error.
        """
        try:
            query = '''
                SELECT 
                    title, company, location, salary, description, requirements,
                    benefits, contact_info, application_url, external_url,
                    html_content, scraped_date, last_accessed, access_count,
                    is_valid, error_message, cache_metadata
                FROM job_details 
                WHERE job_url = %s AND is_valid = TRUE
            '''
            
            result = self.execute_query(query, (job_url,), fetch='one')
            
            if result:
                # Check if this is a 403 error - don't return cached 403 errors
                error_message = result.get('error_message', '') or ''
                if '403' in error_message or 'forbidden' in error_message.lower():
                    print(f"   ❌ Skipping cached 403 error for: {job_url}")
                    return None
                
                # Update access count and last accessed time
                self._update_job_details_access(job_url)
                
                # Convert to dictionary
                details = dict(result)
                print(f"   📋 Retrieved cached job details for: {job_url}")
                return details
            else:
                print(f"   ❌ No cached job details found for: {job_url}")
                return None
                
        except Exception as e:
            print(f"   ❌ Error retrieving cached job details: {e}")
            return None
    
    def cache_job_details(self, job_url: str, details: Dict[str, Any], is_valid: bool = True, error_message: str = None) -> bool:
        """
        Cache job details in the database.
        Returns True if successfully cached, False otherwise.
        """
        try:
            # Special handling for 403 errors - cache them as invalid but with longer retention
            is_403_error = error_message and ('403' in error_message or 'forbidden' in error_message.lower())
            
            query = '''
                INSERT INTO job_details (
                    job_url, title, company, location, salary, description,
                    requirements, benefits, contact_info, application_url,
                    external_url, html_content, is_valid, error_message,
                    scraped_date, last_accessed, access_count, cache_metadata
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                ) ON CONFLICT (job_url) DO UPDATE SET
                    title = EXCLUDED.title,
                    company = EXCLUDED.company,
                    location = EXCLUDED.location,
                    salary = EXCLUDED.salary,
                    description = EXCLUDED.description,
                    requirements = EXCLUDED.requirements,
                    benefits = EXCLUDED.benefits,
                    contact_info = EXCLUDED.contact_info,
                    application_url = EXCLUDED.application_url,
                    external_url = EXCLUDED.external_url,
                    html_content = EXCLUDED.html_content,
                    is_valid = EXCLUDED.is_valid,
                    error_message = EXCLUDED.error_message,
                    scraped_date = EXCLUDED.scraped_date,
                    last_accessed = EXCLUDED.last_accessed,
                    access_count = job_details.access_count + 1,
                    updated_at = CURRENT_TIMESTAMP,
                    cache_metadata = EXCLUDED.cache_metadata
            '''
            
            # Validate and truncate location field to fit VARCHAR(200) constraint
            location = details.get('location', '')
            if location and len(location) > 200:
                location = location[:197] + "..."  # Truncate to 200 chars with ellipsis
                print(f"   ⚠️ Truncated location field from {len(details.get('location', ''))} to 200 characters")
            
            # Ensure proper metadata and timestamps
            current_time = datetime.now()
            scraped_date = details.get('scraped_date') or current_time
            last_accessed = details.get('last_accessed') or current_time
            
            # Add enhanced metadata if not present
            cache_metadata = details.get('cache_metadata')
            if not cache_metadata:
                cache_metadata = {
                    'cached_at': current_time.isoformat(),
                    'platform': 'unknown',
                    'content_length': len(details.get('description', '')),
                    'has_html': bool(details.get('html_content')),
                    'cache_version': '2.0'
                }
            
            params = (
                job_url,
                details.get('title'),
                details.get('company'),
                location,
                details.get('salary'),
                details.get('description'),
                details.get('requirements'),
                details.get('benefits'),
                details.get('contact_info'),
                details.get('application_url'),
                details.get('external_url'),
                details.get('html_content'),
                is_valid,
                error_message,
                scraped_date,
                last_accessed,
                1,  # Initial access count
                json.dumps(cache_metadata)
            )
            
            self.execute_query(query, params)
            
            if is_403_error:
                print(f"   💾 Cached 403 error for: {job_url} (will be skipped on retrieval)")
            else:
                print(f"   💾 Cached job details for: {job_url}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Error caching job details: {e}")
            return False
    
    def _migrate_v1_add_missing_columns(self, cursor):
        """Migration V1: The original function to add all missing columns for backward compatibility"""
        # This function now contains all the logic from the old `_add_missing_columns`
        # --- Migration: Rename title to position_title in job_applications ---
        try:
            # Check if 'title' column exists and 'position_title' does not
            cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='job_applications' AND column_name='title'")
            title_exists = cursor.fetchone()
            cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='job_applications' AND column_name='position_title'")
            position_title_exists = cursor.fetchone()

            if title_exists and not position_title_exists:
                self.logger.info("Attempting to migrate 'title' to 'position_title' in 'job_applications' table...")
                cursor.execute("ALTER TABLE job_applications RENAME COLUMN title TO position_title;")
                self.logger.info("Successfully renamed 'title' to 'position_title'.")
                # Commit this change immediately
                cursor.connection.commit()
        except psycopg2.Error as e:
            self.logger.warning(f"Did not rename 'title' column (this might be expected): {e}")
            # We must rollback the failed transaction block before proceeding.
            cursor.connection.rollback()
        # --- End Migration ---
        
        try:
            # Columns for job_listings
            job_listings_columns = {
                'job_url': 'TEXT',
                'title': 'VARCHAR(255)',
                'company': 'VARCHAR(255)',
                'location': 'VARCHAR(255)',
                'description': 'TEXT',
                'scraped_date': 'TIMESTAMP WITH TIME ZONE',
                'source': 'VARCHAR(100)',
                'status': 'VARCHAR(50)',
                'salary': 'VARCHAR(255)',
                'job_type': 'VARCHAR(100)',
                'experience_level': 'VARCHAR(100)',
                'is_deleted': 'BOOLEAN DEFAULT FALSE',
                'html_content': 'TEXT'
            }
            self._add_columns_to_table(cursor, 'job_listings', job_listings_columns)
            
            # Columns for applications
            applications_columns = {
                'job_listing_id': 'INTEGER REFERENCES job_listings(id) ON DELETE SET NULL',
                'company': 'VARCHAR(255)',
                'position': 'VARCHAR(255)',
                'status': 'VARCHAR(50)',
                'applied_date': 'DATE',
                'notes': 'TEXT',
                'last_updated': 'TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP',
                'source': 'VARCHAR(255)',
                'email_subject': 'VARCHAR(512)',
                'email_date': 'TIMESTAMP WITH TIME ZONE'
            }
            self._add_columns_to_table(cursor, 'applications', applications_columns)

            # Columns for job_applications
            job_applications_columns = {
                'email_date': 'TIMESTAMP WITH TIME ZONE',
                'email_subject': 'VARCHAR(512)',
                'last_updated': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
            }
            self._add_columns_to_table(cursor, 'job_applications', job_applications_columns)
            
            # Columns for job_details
            job_details_columns = {
                'job_url': 'TEXT PRIMARY KEY',
                'title': 'VARCHAR(255)',
                'company': 'VARCHAR(255)',
                'location': 'VARCHAR(200)',
                'salary': 'VARCHAR(255)',
                'description': 'TEXT',
                'requirements': 'TEXT',
                'benefits': 'TEXT',
                'contact_info': 'TEXT',
                'application_url': 'TEXT',
                'external_url': 'TEXT',
                'html_content': 'TEXT',
                'scraped_date': 'TIMESTAMP WITH TIME ZONE',
                'last_accessed': 'TIMESTAMP WITH TIME ZONE',
                'access_count': 'INTEGER DEFAULT 0',
                'is_valid': 'BOOLEAN DEFAULT TRUE',
                'error_message': 'TEXT',
                'updated_at': 'TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP',
                'cache_metadata': 'JSONB'
            }
            self._add_columns_to_table(cursor, 'job_details', job_details_columns)

            self.logger.info("All tables and columns verified for migration v1.")
        except Exception as e:
            self.logger.error(f"Error in migration v1: {e}")
            raise

    def _update_job_details_access(self, job_url: str) -> None:
        """Update access count and last accessed time for cached job details."""
        try:
            query = '''
                UPDATE job_details 
                SET access_count = access_count + 1,
                    last_accessed = CURRENT_TIMESTAMP
                WHERE job_url = %s
            '''
            self.execute_query(query, (job_url,))
        except Exception as e:
            print(f"   ⚠️ Error updating job details access: {e}")
    
    def get_cached_job_details_stats(self) -> Dict[str, Any]:
        """Get statistics about cached job details."""
        try:
            query = '''
                SELECT 
                    COUNT(*) as total_cached,
                    COUNT(CASE WHEN is_valid = TRUE THEN 1 END) as valid_cached,
                    COUNT(CASE WHEN is_valid = FALSE THEN 1 END) as invalid_cached,
                    AVG(access_count) as avg_access_count,
                    MAX(last_accessed) as last_access,
                    MIN(scraped_date) as oldest_cache,
                    MAX(scraped_date) as newest_cache
                FROM job_details
            '''
            
            result = self.execute_query(query, fetch='one')
            if result:
                return dict(result)
            return {}
            
        except Exception as e:
            print(f"   ❌ Error getting cache stats: {e}")
            return {}
    
    def clear_old_job_details(self, days_old: int = 30) -> int:
        """
        Clear job details older than specified days.
        Returns number of records deleted.
        """
        try:
            query = '''
                DELETE FROM job_details 
                WHERE scraped_date < CURRENT_TIMESTAMP - INTERVAL '%s days'
            '''
            
            result = self.execute_query(query, (days_old,))
            print(f"   🗑️ Cleared job details older than {days_old} days")
            return 1  # Placeholder, actual count would need different approach
            
        except Exception as e:
            print(f"   ❌ Error clearing old job details: {e}")
            return 0
    
    def invalidate_job_details(self, job_url: str, error_message: str = None) -> bool:
        """
        Mark cached job details as invalid (e.g., if the URL is no longer accessible).
        """
        try:
            query = '''
                UPDATE job_details 
                SET is_valid = FALSE, 
                    error_message = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE job_url = %s
            '''
            
            self.execute_query(query, (error_message, job_url))
            print(f"   ⚠️ Invalidated cached job details for: {job_url}")
            return True
            
        except Exception as e:
            print(f"   ❌ Error invalidating job details: {e}")
            return False

    def save_job_listing(self, job: Dict) -> bool:
        """
        Save a single job listing to the database.
        Returns True if the job was inserted, False if it was skipped due to conflict.
        """
        try:
            # Extensive logging for job insertion
            print(f"💾 Attempting to save job listing:")
            print(f"   🏢 Title: {job.get('title', 'N/A')}")
            print(f"   🏭 Company: {job.get('company', 'N/A')}")
            print(f"   🌐 URL: {job.get('url', 'N/A')}")
            print(f"   📍 Location: {job.get('location', 'N/A')}")
            print(f"   📅 Scraped Date: {job.get('scraped_date', 'N/A')}")
            print(f"   🤖 LLM Filtered: {job.get('llm_filtered', False)}")
            print(f"   📊 Relevance Score: {job.get('llm_relevance_score', 0)}")

            query = '''
                INSERT INTO job_listings 
                (title, company, location, salary, url, source, scraped_date, posted_date, description, language,
                 job_snippet, llm_assessment, llm_filtered, llm_quality_score, llm_relevance_score, llm_reasoning)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (url) DO NOTHING
                RETURNING id
            '''
            
            # Validate and truncate fields to fit database constraints
            location = job.get('location', '')
            if location and len(location) > 200:
                location = location[:197] + "..."  # Truncate to 200 chars with ellipsis
                print(f"   ⚠️ Truncated location field from {len(job.get('location', ''))} to 200 characters")
            
            company = job.get('company', '')
            if company and len(company) > 200:
                company = company[:197] + "..."  # Truncate to 200 chars with ellipsis
                print(f"   ⚠️ Truncated company field from {len(job.get('company', ''))} to 200 characters")
            
            title = job.get('title', '')
            if title and len(title) > 500:
                title = title[:497] + "..."  # Truncate to 500 chars with ellipsis
                print(f"   ⚠️ Truncated title field from {len(job.get('title', ''))} to 500 characters")
            
            salary = job.get('salary', '')
            if salary and len(salary) > 100:
                salary = salary[:97] + "..."  # Truncate to 100 chars with ellipsis
                print(f"   ⚠️ Truncated salary field from {len(job.get('salary', ''))} to 100 characters")
            
            params = (
                title,
                company,
                location,
                salary,
                job.get('url'),
                job.get('source'),
                job.get('scraped_date'),
                job.get('posted_date'),
                job.get('description'),
                job.get('language'),
                job.get('job_snippet'),
                str(job.get('llm_assessment', {})) if job.get('llm_assessment') else None,
                job.get('llm_filtered', False),
                job.get('llm_quality_score', 0),
                job.get('llm_relevance_score', 0),
                job.get('llm_reasoning', '')
            )
            
            # Validate parameters before insertion
            for i, param in enumerate(params):
                if param is None:
                    print(f"   ⚠️ Parameter {i} is None: {param}")
            
            result = self.execute_query(query, params, fetch='one')
            
            if result is not None:
                print(f"   ✅ Job successfully saved with ID: {result}")
                return True
            else:
                print(f"   ❌ Job not saved (likely duplicate): {job.get('url', 'Unknown URL')}")
                return False
            
        except Exception as e:
            print(f"❌ Error saving job listing: {e}")
            self.logger.error(f"Error saving job listing: {e}")
            return False
    
    def _get_database_url(self) -> str:
        """Get database URL from environment variables"""
        # Check for full DATABASE_URL first
        db_url = os.getenv('DATABASE_URL')
        if db_url:
            return db_url
        
        # Determine host based on environment
        if self.env == 'local':
            host = 'localhost'
        else:
            host = os.getenv('POSTGRES_HOST', 'postgres')
            
        # Build from individual components
        port = os.getenv('POSTGRES_PORT', '5432')
        database = os.getenv('POSTGRES_DB', 'jobtracker')
        user = os.getenv('POSTGRES_USER', 'jobtracker')
        password = os.getenv('POSTGRES_PASSWORD', 'secure_password_2024')
        
        return f"postgresql://{user}:{password}@{host}:{port}/{database}"
    
    def _create_connection_pool(self):
        """Create PostgreSQL connection pool"""
        try:
            self.connection_pool = psycopg2.pool.ThreadedConnectionPool(
                2, 10, self._get_database_url(), options="-c statement_timeout=30000"  # 30 second statement timeout
            )
            self.logger.info("✅ PostgreSQL connection pool created successfully")
        except Exception as e:
            self.logger.error(f"❌ Failed to create connection pool: {e}")
            raise
    
    def _initialize_database(self):
        """Initialize database with all required tables"""
        max_retries = 3
        retry_delay = 2.0
        
        for attempt in range(max_retries):
            try:
                with self.get_connection() as conn:
                    with conn.cursor() as cursor:
                        self._create_tables(cursor)
                        self._add_missing_columns(cursor)
                        conn.commit()
                    self.logger.info("✅ Database tables initialized successfully")
                    return
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    self.logger.warning(f"Database initialization attempt {attempt + 1} failed, retrying in {retry_delay}s: {e}")
                    time.sleep(retry_delay)
                    retry_delay *= 1.5
                    continue
                else:
                    self.logger.error(f"❌ Failed to initialize database after {attempt + 1} attempts: {e}")
                    raise
    
    def _create_tables(self, cursor):
        """Create all required tables"""
        
        # Create job_listings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS job_listings (
                id SERIAL PRIMARY KEY,
                title VARCHAR(500),
                company VARCHAR(200),
                location VARCHAR(200),
                salary VARCHAR(100),
                url TEXT UNIQUE,
                source VARCHAR(50),
                scraped_date TIMESTAMP,
                posted_date TIMESTAMP,
                description TEXT,
                language VARCHAR(10),
                job_snippet TEXT,
                llm_assessment TEXT,
                llm_filtered BOOLEAN DEFAULT FALSE,
                llm_quality_score FLOAT DEFAULT 0,
                llm_relevance_score FLOAT DEFAULT 0,
                llm_reasoning TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create job_details table for caching detailed job information
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS job_details (
                id SERIAL PRIMARY KEY,
                job_url TEXT UNIQUE,
                title VARCHAR(500),
                company VARCHAR(200),
                location VARCHAR(200),
                salary VARCHAR(100),
                description TEXT,
                requirements TEXT,
                benefits TEXT,
                contact_info TEXT,
                application_url TEXT,
                external_url TEXT,
                html_content TEXT,
                scraped_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                access_count INTEGER DEFAULT 1,
                is_valid BOOLEAN DEFAULT TRUE,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create email_analysis table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS email_analysis (
                id VARCHAR(255) PRIMARY KEY,
                date TIMESTAMP,
                subject TEXT,
                sender TEXT,
                company TEXT,
                category TEXT,
                body_preview TEXT,
                application_id TEXT,
                position_title TEXT,
                email_hash TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create applications table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS applications (
                id SERIAL PRIMARY KEY,
                company TEXT,
                position TEXT,
                status TEXT,
                applied_date TIMESTAMP,
                source TEXT,
                notes TEXT,
                email_subject TEXT,
                email_date TIMESTAMP WITH TIME ZONE,
                job_id INTEGER,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create ignored_jobs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ignored_jobs (
                id SERIAL PRIMARY KEY,
                job_listing_id INTEGER REFERENCES job_listings(id) ON DELETE CASCADE,
                reason TEXT,
                ignored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_job_listings_url ON job_listings(url)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_job_listings_source ON job_listings(source)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_job_listings_scraped_date ON job_listings(scraped_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_job_details_url ON job_details(job_url)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_job_details_last_accessed ON job_details(last_accessed)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_email_analysis_hash ON email_analysis(email_hash)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_applications_job_id ON applications(job_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ignored_jobs_job_id ON ignored_jobs(job_listing_id)')
        
        # Create job_applications table for tracking applications
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
        
        # Create filtered_jobs table for jobs that are filtered out automatically or ignored
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS filtered_jobs (
                id SERIAL PRIMARY KEY,
                job_listing_id INTEGER REFERENCES job_listings(id) ON DELETE CASCADE,
                filter_reason TEXT,
                filtered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create job_offers table
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
                application_id INTEGER REFERENCES applications(id) ON DELETE SET NULL
            )
        ''')
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_offer_status ON job_offers(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_offer_company ON job_offers(company)")
        
        self.logger.info("✅ All tables and indexes created successfully")
    
    def _add_missing_columns(self, cursor):
        """This method is now deprecated. Use _run_migrations instead."""
        # The content of this function has been moved to `_migrate_v1_add_missing_columns`
        pass
        
    @contextmanager
    def get_connection(self, timeout: float = 30.0):
        """
        Get a connection from the pool.

        Args:
            timeout (float): Max time to wait for a connection. Defaults to 30.0.
        """
        if not self.connection_pool:
            self._create_connection_pool()
        
        conn = None
        start_time = time.time()
        
        # This loop will wait for a connection to become available
        while True:
            try:
                # Try to get a connection without blocking indefinitely
                conn = self.connection_pool.getconn()
                break
            except psycopg2.pool.PoolError as e:
                if time.time() - start_time > timeout:
                    raise TimeoutError(f"Could not get a connection from the pool within {timeout} seconds") from e
                # Wait a bit before retrying
                time.sleep(0.1)

        try:
            yield conn
        finally:
            if conn:
                self.connection_pool.putconn(conn)

    def _add_columns_to_table(self, cursor, table_name: str, columns: Dict[str, str]) -> None:
        """
        Helper to add multiple columns to a table.
        Takes a dictionary of column names and their data types.
        """
        for col_name, col_type in columns.items():
            try:
                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {col_name} {col_type};")
                self.logger.info(f"Added column {col_name} to {table_name}")
            except psycopg2.Error as e:
                self.logger.warning(f"Could not add column {col_name} to {table_name}: {e}")
                # If the column already exists, we can continue.
                if "already exists" in str(e).lower():
                    self.logger.info(f"Column {col_name} already exists in {table_name}")
                else:
                    # For other errors, we might want to rollback or re-evaluate
                    cursor.connection.rollback()
                    raise

    def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """
        Execute multiple queries in a single transaction
        """
        max_retries = 3
        retry_delay = 0.5
        
        for attempt in range(max_retries):
            try:
                with self.get_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.executemany(query, params_list)
                        result = cursor.rowcount
                        conn.commit()
                        return result
                        
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                if attempt < max_retries - 1:
                    self.logger.warning(f"Database connection error during batch operation, retrying in {retry_delay}s")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    self.logger.error(f"Database batch error after {attempt + 1} attempts: {e}")
                    raise
            except Exception as e:
                self.logger.error(f"Unexpected batch database error: {e}")
                raise
    
    def cleanup_filtered_jobs_from_ignored(self) -> int:
        """
        Remove filtered jobs (llm_filtered = true) from the ignored_jobs table.
        This ensures filtered jobs and ignored jobs remain separate.
        Returns the number of jobs cleaned up.
        """
        try:
            query = """
                DELETE FROM ignored_jobs 
                WHERE url IN (
                    SELECT url FROM job_listings 
                    WHERE llm_filtered = true
                )
            """
            
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    cleaned_count = cursor.rowcount
                    conn.commit()
                    
            if cleaned_count > 0:
                self.logger.info(f"🧹 Cleaned up {cleaned_count} filtered jobs from ignored_jobs table")
            
            return cleaned_count
            
        except Exception as e:
            self.logger.error(f"Error cleaning up filtered jobs from ignored: {e}")
            return 0

    def batch_insert_jobs(self, jobs_data: List[Dict], batch_size: int = 500) -> int:
        """
        Insert jobs in batches with excellent performance
        Optimized for speed with larger batch sizes and better error handling
        """
        if not jobs_data:
            return 0
            
        total_inserted = 0
        
        # Use larger batch size for better performance
        for i in range(0, len(jobs_data), batch_size):
            batch = jobs_data[i:i + batch_size]
            
            # Prepare batch data with better error handling
            batch_params = []
            for job in batch:
                try:
                    batch_params.append((
                        job.get('title', ''),
                        job.get('company', ''),
                        job.get('location', ''),
                        job.get('salary', ''),
                        job.get('url', ''),
                        job.get('source', ''),
                        job.get('scraped_date'),
                        job.get('posted_date'),
                        job.get('description', ''),
                        job.get('language', ''),
                        job.get('job_snippet', ''),
                        str(job.get('llm_assessment', {})) if job.get('llm_assessment') else None,
                        job.get('llm_filtered', False),
                        job.get('llm_quality_score', 0),
                        job.get('llm_relevance_score', 0),
                        job.get('llm_reasoning', '')
                    ))
                except Exception as e:
                    self.logger.warning(f"Skipping malformed job data: {e}")
                    continue
            
            if not batch_params:
                continue
            
            # Insert batch using ON CONFLICT for upsert behavior
            query = '''
                INSERT INTO job_listings 
                (title, company, location, salary, url, source, scraped_date, posted_date, description, language,
                 job_snippet, llm_assessment, llm_filtered, llm_quality_score, llm_relevance_score, llm_reasoning)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (url) DO NOTHING
            '''
            
            try:
                inserted = self.execute_many(query, batch_params)
                total_inserted += inserted
                
                # Log progress less frequently for better performance
                if (i // batch_size + 1) % 5 == 0:
                    self.logger.info(f"Inserted batch {i//batch_size + 1}: {inserted} jobs")
                    
            except Exception as e:
                self.logger.error(f"Error inserting job batch {i//batch_size + 1}: {e}")
                # Continue with next batch instead of failing completely
                continue
        
        self.logger.info(f"Total jobs inserted: {total_inserted}")
        
        # Clean up filtered jobs from ignored_jobs table to maintain separation
        if total_inserted > 0:
            cleaned_count = self.cleanup_filtered_jobs_from_ignored()
            if cleaned_count > 0:
                self.logger.info(f"🧹 Maintained separation: {cleaned_count} filtered jobs removed from ignored list")
        
        return total_inserted
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get database health status"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT version(), current_database(), current_user;")
                    version, database, user = cursor.fetchone()
                    
                    cursor.execute("SELECT COUNT(*) FROM job_listings;")
                    job_count = cursor.fetchone()[0]
                    
                    cursor.execute("SELECT COUNT(*) FROM email_analysis;")
                    email_count = cursor.fetchone()[0]
                    
                    cursor.execute("SELECT COUNT(*) FROM job_applications;")
                    application_count = cursor.fetchone()[0]
                    
                    return {
                        'status': 'healthy',
                        'database': database,
                        'user': user,
                        'version': version,
                        'job_listings': job_count,
                        'email_analysis': email_count,
                        'job_applications': application_count,
                        'pool_size': f"{self.connection_pool.closed}/{self.connection_pool.maxconn}"
                    }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }
    
    def close_all_connections(self):
        """Close all connections in the pool"""
        try:
            if hasattr(self, 'connection_pool'):
                self.connection_pool.closeall()
                self.logger.info("✅ All database connections closed")
        except Exception as e:
            self.logger.error(f"Error closing connections: {e}")
    
    def get_sqlalchemy_engine(self):
        """Get SQLAlchemy engine for pandas compatibility"""
        if self._sqlalchemy_engine is None:
            self._sqlalchemy_engine = create_engine(self._get_database_url())
        return self._sqlalchemy_engine
    
    def clear_job_data(self, clear_applications: bool = False) -> Dict[str, int]:
        """
        Clear job data while properly handling foreign key constraints
        
        Args:
            clear_applications: If True, also clear job applications and ignored jobs. If False, only clear job_listings that are not referenced.
            
        Returns:
            Dictionary with counts of deleted records
        """
        result = {'job_listings_deleted': 0, 'job_applications_deleted': 0, 'ignored_jobs_deleted': 0}
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    if clear_applications:
                        # Clear applications, ignored jobs, and listings (in correct order due to foreign keys)
                        self.logger.info("Clearing all job applications, ignored jobs, and listings...")
                        
                        # First delete job applications
                        cursor.execute("DELETE FROM job_applications")
                        result['job_applications_deleted'] = cursor.rowcount
                        
                        # Then delete ignored jobs (they reference job_listings)
                        cursor.execute("DELETE FROM ignored_jobs")
                        result['ignored_jobs_deleted'] = cursor.rowcount
                        
                        # Finally delete all job listings
                        cursor.execute("DELETE FROM job_listings")
                        result['job_listings_deleted'] = cursor.rowcount
                        
                    else:
                        # Only clear job listings that are not referenced by applications or ignored jobs
                        self.logger.info("Clearing unreferenced job listings only...")
                        
                        # Delete ignored jobs that reference job listings we want to delete
                        cursor.execute("""
                            DELETE FROM ignored_jobs 
                            WHERE job_listing_id NOT IN (
                                SELECT DISTINCT job_listing_id 
                                FROM job_applications 
                                WHERE job_listing_id IS NOT NULL
                            ) AND job_listing_id IS NOT NULL
                        """)
                        result['ignored_jobs_deleted'] = cursor.rowcount
                        
                        # Then delete job listings that are not referenced by applications
                        cursor.execute("""
                            DELETE FROM job_listings 
                            WHERE id NOT IN (
                                SELECT DISTINCT job_listing_id 
                                FROM job_applications 
                                WHERE job_listing_id IS NOT NULL
                            )
                        """)
                        result['job_listings_deleted'] = cursor.rowcount
                    
                    conn.commit()
                    
                    self.logger.info(f"Successfully cleared: {result['job_listings_deleted']} job listings, {result['job_applications_deleted']} applications, {result['ignored_jobs_deleted']} ignored jobs")
                    
        except Exception as e:
            self.logger.error(f"Error clearing job data: {e}")
            raise
        
        return result
    
    def clear_email_data(self) -> int:
        """
        Clear all email analysis data
        
        Returns:
            Number of deleted email records
        """
        try:
            # Get the count first
            count_query = "SELECT COUNT(*) FROM email_analysis"
            count_result = self.execute_query(count_query, fetch='one')
            deleted_count = count_result[0] if count_result else 0
            
            # Then delete
            self.execute_query("DELETE FROM email_analysis")
            
            self.logger.info(f"Successfully cleared {deleted_count} email records")
            return deleted_count
                    
        except Exception as e:
            self.logger.error(f"Error clearing email data: {e}")
            raise
    
    def get_location_analysis(self) -> Dict[str, Any]:
        """
        Analyze job locations in the database to identify potential issues
        
        Returns:
            Dictionary with location analysis results
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Get location counts
                    cursor.execute("""
                        SELECT location, COUNT(*) as count, source
                        FROM job_listings 
                        WHERE location IS NOT NULL 
                        GROUP BY location, source
                        ORDER BY count DESC
                    """)
                    location_results = cursor.fetchall()
                    
                    # Get suspicious locations
                    suspicious_keywords = [
                        'belgium', 'netherlands', 'france', 'austria', 'switzerland', 'poland',
                        'brussels', 'antwerp', 'amsterdam', 'paris', 'vienna', 'zurich', 'warsaw',
                        'usa', 'united states', 'canada', 'uk', 'london', 'new york', 'toronto'
                    ]
                    
                    suspicious_condition = " OR ".join([f"LOWER(location) LIKE '%{keyword}%'" for keyword in suspicious_keywords])
                    
                    cursor.execute(f"""
                        SELECT id, title, company, location, source, scraped_date
                        FROM job_listings 
                        WHERE {suspicious_condition}
                        ORDER BY scraped_date DESC
                        LIMIT 20
                    """)
                    suspicious_jobs = cursor.fetchall()
                    
                    # Get total stats
                    cursor.execute("SELECT COUNT(*) FROM job_listings")
                    total_jobs = cursor.fetchone()[0]
                    
                    cursor.execute("SELECT COUNT(DISTINCT location) FROM job_listings WHERE location IS NOT NULL")
                    unique_locations = cursor.fetchone()[0]
                    
                    return {
                        'total_jobs': total_jobs,
                        'unique_locations': unique_locations,
                        'location_counts': location_results,
                        'suspicious_jobs': suspicious_jobs,
                        'suspicious_count': len(suspicious_jobs)
                    }
                    
        except Exception as e:
            self.logger.error(f"Error analyzing locations: {e}")
            raise

    def get_applications(self, status: str = None) -> List[Dict]:
        """
        Get job applications from both applications and job_applications tables
        
        Args:
            status: Optional status to filter by (e.g., 'saved', 'applied', 'interview', 'offer', 'rejected')
            
        Returns:
            List of job applications as dictionaries
        """
        try:
            # Query both tables and combine results
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
                    'applications' as table_source
                FROM applications
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
                    url,
                    'job_applications' as table_source
                FROM job_applications
            """
            
            params = []
            if status:
                applications_query += " WHERE status = %s"
                job_applications_query += " WHERE status = %s"
                params.append(status)
            
            applications_query += " ORDER BY last_updated DESC"
            job_applications_query += " ORDER BY last_updated DESC"
            
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                    # Get applications from applications table
                    cursor.execute(applications_query, tuple(params))
                    applications_results = cursor.fetchall()
                    
                    # Get applications from job_applications table
                    cursor.execute(job_applications_query, tuple(params))
                    job_applications_results = cursor.fetchall()

            # Convert DictRow objects to standard dictionaries
            applications = [dict(row) for row in applications_results]
            job_applications = [dict(row) for row in job_applications_results]
            
            # Combine and sort by last_updated
            all_applications = applications + job_applications
            all_applications.sort(key=lambda x: x.get('last_updated', ''), reverse=True)
            
            return all_applications
            
        except Exception as e:
            self.logger.error(f"Error getting applications: {e}")
            raise

    def update_application(self, application_id: int, status: str, notes: str = None, table_source: str = 'job_applications') -> bool:
        """
        Update application status and notes in the specified table
        
        Args:
            application_id: ID of the application to update
            status: New status value (must be one of: 'saved', 'applied', 'interview', 'rejected', 'offer', 'withdrawn')
            notes: Optional notes to update
            table_source: Which table to update ('applications' or 'job_applications')
            
        Returns:
            True if update was successful, False otherwise
        """
        try:
            # Validate status
            valid_statuses = ['saved', 'applied', 'interview', 'rejected', 'offer', 'withdrawn']
            if status.lower() not in valid_statuses:
                raise ValueError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
            
            # Determine which table to update
            if table_source == 'applications':
                table_name = 'applications'
                id_column = 'id'
            else:
                table_name = 'job_applications'
                id_column = 'id'
            
            # Build query based on whether notes are provided
            if notes is not None:
                query = f"""
                    UPDATE {table_name} 
                    SET status = %s, notes = %s
                    WHERE {id_column} = %s
                """
                params = (status.lower(), notes, application_id)
            else:
                query = f"""
                    UPDATE {table_name} 
                    SET status = %s
                    WHERE {id_column} = %s
                """
                params = (status.lower(), application_id)
            
            self.execute_query(query, params)
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating application {application_id} in {table_source}: {e}")
            raise

    def update_application_status_by_job_id(self, job_listing_id: int, new_status: str) -> bool:
        """Update the status of an application by job_listing_id"""
        try:
            query = "UPDATE job_applications SET status = %s WHERE job_listing_id = %s"
            self.execute_query(query, (new_status, job_listing_id))
            return True
        except Exception as e:
            self.logger.error(f"Error updating application status by job ID: {e}")
            return False
    
    def get_ignored_jobs(self):
        """Get ignored jobs with job listing details"""
        try:
            query = """
                SELECT 
                    ij.id,
                    ij.job_listing_id,
                    ij.url,
                    ij.reason,
                    ij.ignored_at,
                    jl.title,
                    jl.company,
                    jl.location
                FROM ignored_jobs ij
                LEFT JOIN job_listings jl ON ij.job_listing_id = jl.id
                ORDER BY ij.ignored_at DESC
            """
            
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                    cursor.execute(query)
                    results = cursor.fetchall()
            
            # Convert to pandas DataFrame
            import pandas as pd
            return pd.DataFrame([dict(row) for row in results])
            
        except Exception as e:
            self.logger.error(f"Error getting ignored jobs: {e}")
            import pandas as pd
            return pd.DataFrame()
    
    def unignore_job(self, ignored_job_id: int) -> bool:
        """Remove a job from the ignored list"""
        try:
            query = "DELETE FROM ignored_jobs WHERE id = %s"
            self.execute_query(query, (ignored_job_id,))
            return True
        except Exception as e:
            self.logger.error(f"Error unignoring job: {e}")
            return False

    def delete_application(self, application_id: int, table_source: str = 'job_applications') -> bool:
        """
        Delete an application from the specified table
        
        Args:
            application_id: ID of the application to delete
            table_source: Which table to delete from ('applications' or 'job_applications')
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            # Determine which table to delete from
            if table_source == 'applications':
                table_name = 'applications'
                id_column = 'id'
            else:
                table_name = 'job_applications'
                id_column = 'id'
            
            query = f"DELETE FROM {table_name} WHERE {id_column} = %s"
            self.execute_query(query, (application_id,))
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting application {application_id} from {table_source}: {e}")
            raise

def get_db_manager(env: str = 'docker') -> PostgreSQLManager:
    """
    Get a thread-safe instance of the PostgreSQLManager.
    
    Args:
        env: The environment ('docker' or 'local'). 
             'local' will force connection to localhost.
             
    Returns:
        An instance of PostgreSQLManager.
    """
    global _db_manager_local
    
    # Check if an instance already exists for this thread
    if not hasattr(_db_manager_local, 'instance') or _db_manager_local.instance is None:
        try:
            # If not, create a new one
            _db_manager_local.instance = PostgreSQLManager(env=env)
        except Exception as e:
            logging.error(f"Error initializing database manager: {e}")
            raise
    
    # Return the existing instance
    return _db_manager_local.instance

class DatabaseHealth:
    pass

# Global database manager instance - This is the old pattern, we can remove it.
# _db_manager: Optional[PostgreSQLManager] = None
# _db_manager_lock = threading.Lock()
#
# def get_db_manager() -> PostgreSQLManager:
#     """Get a thread-safe instance of the PostgreSQLManager"""
#     global _db_manager
#     with _db_manager_lock:
#         if _db_manager is None:
#             try:
#                 _db_manager = PostgreSQLManager()
#             except Exception as e:
#                 logging.error(f"Error initializing database manager: {e}")
#                 raise
#         return _db_manager 