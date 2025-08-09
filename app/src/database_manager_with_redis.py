"""
Enhanced Database Manager with Redis Caching
Combines PostgreSQL with Redis for optimal performance
"""

import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import DictCursor
import threading
import time
import logging
from contextlib import contextmanager
from typing import Optional, Any, List, Dict, Union, Tuple
import os
from datetime import datetime
import json
import hashlib

from core.redis_cache_manager import get_redis_cache, redis_cache_decorator

logger = logging.getLogger(__name__)

class EnhancedPostgreSQLManager:
    """
    Enhanced PostgreSQL manager with Redis caching for optimal performance.
    """
    
    def __init__(self, host: str = None, port: int = None, 
                 dbname: str = None, user: str = None, 
                 password: str = None, env: str = 'docker'):
        """Initialize enhanced database connection with Redis caching."""
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
        
        # Enhanced connection pool settings
        self.min_connections = 5
        self.max_connections = 30  # Increased for better concurrency
        self.connection_pool: Optional[ThreadedConnectionPool] = None
        self.logger = logging.getLogger(__name__)
        
        # Redis cache manager
        self.redis_cache = get_redis_cache()
        
        # Performance tracking
        self.query_stats = {
            'total_queries': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'slow_queries': 0,
            'timeouts': 0,
            'redis_available': self.redis_cache.redis_client is not None
        }
        
        self._create_enhanced_connection_pool()
        self.ensure_tables_exist()
    
    def _get_database_url(self) -> str:
        """Get enhanced database URL with optimized settings."""
        # Check for full DATABASE_URL first
        db_url = os.getenv('DATABASE_URL')
        if db_url:
            return db_url
        
        # Determine host based on environment
        host = self.connection_params['host']
        port = self.connection_params['port']
        database = self.connection_params['dbname']
        user = self.connection_params['user']
        password = self.connection_params['password']
        
        return f"postgresql://{user}:{password}@{host}:{port}/{database}"
    
    def _create_enhanced_connection_pool(self):
        """Create enhanced PostgreSQL connection pool with better settings."""
        try:
            # Enhanced connection options
            connection_options = (
                "-c statement_timeout=180000 "  # 3 minutes statement timeout
                "-c idle_in_transaction_session_timeout=300000 "  # 5 minutes idle timeout
                "-c lock_timeout=60000 "  # 1 minute lock timeout
                "-c work_mem=128MB "  # Increased work memory
                "-c maintenance_work_mem=256MB "  # Increased maintenance memory
                "-c effective_cache_size=2GB "  # Cache size hint
                "-c random_page_cost=1.1 "  # SSD optimization
                "-c tcp_keepalives_idle=600 "  # Keep connections alive
                "-c tcp_keepalives_interval=30 "
                "-c tcp_keepalives_count=3"
            )
            
            self.connection_pool = ThreadedConnectionPool(
                self.min_connections,
                self.max_connections,
                self._get_database_url(),
                options=connection_options
            )
            
            self.logger.info(f"✅ Enhanced PostgreSQL connection pool created "
                           f"({self.min_connections}-{self.max_connections} connections)")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to create enhanced connection pool: {e}")
            raise
    
    def _generate_cache_key(self, query: str, params: Tuple = None) -> str:
        """Generate consistent cache key for queries"""
        # Create a hash of the query and parameters
        query_str = f"{query}_{str(params) if params else ''}"
        return hashlib.md5(query_str.encode()).hexdigest()
    
    @contextmanager
    def get_enhanced_connection(self, timeout: float = 60.0):
        """Get a connection with enhanced timeout handling."""
        if not self.connection_pool:
            self._create_enhanced_connection_pool()
        
        conn = None
        start_time = time.time()
        
        try:
            # Get connection with timeout
            while True:
                try:
                    conn = self.connection_pool.getconn()
                    break
                except psycopg2.pool.PoolError as e:
                    if time.time() - start_time > timeout:
                        raise TimeoutError(f"Could not get connection within {timeout}s") from e
                    time.sleep(0.1)
            
            # Set connection-specific settings
            with conn.cursor() as cur:
                cur.execute("SET statement_timeout = '180s'")  # Per-connection timeout
                cur.execute("SET lock_timeout = '60s'")
                conn.commit()
            
            yield conn
            
        except Exception as e:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                try:
                    self.connection_pool.putconn(conn)
                except Exception as e:
                    self.logger.warning(f"Error returning connection to pool: {e}")
    
    def execute_cached_query(self, query: str, params: Tuple = None, 
                           fetch: str = None, timeout: float = 180.0,
                           cache_ttl: int = 300) -> Optional[Any]:
        """
        Execute query with Redis caching for improved performance.
        """
        start_time = time.time()
        self.query_stats['total_queries'] += 1
        
        # Generate cache key
        cache_key = self._generate_cache_key(query, params)
        
        # Try to get from Redis cache first
        if self.redis_cache.redis_client:
            cached_result = self.redis_cache.get(cache_key, "db_query")
            if cached_result is not None:
                self.query_stats['cache_hits'] += 1
                logger.debug(f"Cache HIT for query: {query[:50]}...")
                return cached_result
        
        self.query_stats['cache_misses'] += 1
        
        try:
            # Get configuration for timeout
            from config_manager import get_config_manager
            config_manager = get_config_manager()
            db_timeout = config_manager.get_value('database.connection_timeout', 30.0)
            
            with self.get_enhanced_connection(timeout=db_timeout) as conn:
                with conn.cursor(cursor_factory=DictCursor) as cursor:
                    # Execute query with timeout handling
                    cursor.execute(query, params)
                    
                    if fetch == 'one':
                        result = cursor.fetchone()
                    elif fetch == 'all':
                        result = cursor.fetchall()
                    else:
                        result = cursor.rowcount if cursor.rowcount >= 0 else None
                    
                    conn.commit()
                    
                    # Cache the result in Redis
                    if self.redis_cache.redis_client and result is not None:
                        self.redis_cache.set(cache_key, result, cache_ttl, "db_query")
                    
                    # Track performance
                    query_time = time.time() - start_time
                    if query_time > 5.0:  # Slow query threshold
                        self.query_stats['slow_queries'] += 1
                        self.logger.warning(f"Slow query detected: {query_time:.3f}s")
                    
                    return result
                    
        except psycopg2.OperationalError as e:
            if 'timeout' in str(e).lower() or 'canceling statement' in str(e).lower():
                self.query_stats['timeouts'] += 1
                self.logger.error(f"Query timeout after {time.time() - start_time:.1f}s: {e}")
                raise TimeoutError(f"Database query timed out: {e}")
            else:
                self.logger.error(f"Database operational error: {e}")
                raise
        except Exception as e:
            self.logger.error(f"Database query failed: {e}")
            raise
    
    @redis_cache_decorator(ttl=1800)  # Cache for 30 minutes
    def get_job_listings_cached(self, limit: int = 1000, offset: int = 0) -> List[Dict]:
        """Get job listings with Redis caching"""
        query = """
            SELECT * FROM job_listings 
            ORDER BY scraped_date DESC 
            LIMIT %s OFFSET %s
        """
        return self.execute_cached_query(query, (limit, offset), fetch='all', cache_ttl=1800)
    
    @redis_cache_decorator(ttl=900)  # Cache for 15 minutes
    def get_applications_cached(self) -> List[Dict]:
        """Get applications with Redis caching"""
        query = "SELECT * FROM applications ORDER BY application_date DESC"
        return self.execute_cached_query(query, fetch='all', cache_ttl=900)
    
    @redis_cache_decorator(ttl=3600)  # Cache for 1 hour
    def get_job_statistics_cached(self) -> Dict[str, Any]:
        """Get job statistics with Redis caching"""
        queries = {
            'total_jobs': "SELECT COUNT(*) FROM job_listings",
            'recent_jobs': "SELECT COUNT(*) FROM job_listings WHERE scraped_date >= NOW() - INTERVAL '7 days'",
            'total_applications': "SELECT COUNT(*) FROM applications",
            'recent_applications': "SELECT COUNT(*) FROM applications WHERE application_date >= NOW() - INTERVAL '7 days'",
            'companies': "SELECT COUNT(DISTINCT company) FROM job_listings",
            'locations': "SELECT COUNT(DISTINCT location) FROM job_listings"
        }
        
        stats = {}
        for key, query in queries.items():
            result = self.execute_cached_query(query, fetch='one', cache_ttl=3600)
            stats[key] = result[0] if result else 0
        
        return stats
    
    def invalidate_cache_pattern(self, pattern: str = "jobtracker:*") -> int:
        """Invalidate cache entries matching pattern"""
        return self.redis_cache.clear_pattern(pattern)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics"""
        db_stats = {
            'total_queries': self.query_stats['total_queries'],
            'cache_hits': self.query_stats['cache_hits'],
            'cache_misses': self.query_stats['cache_misses'],
            'cache_hit_rate': (self.query_stats['cache_hits'] / 
                              max(self.query_stats['total_queries'], 1)) * 100,
            'slow_queries': self.query_stats['slow_queries'],
            'timeouts': self.query_stats['timeouts'],
            'redis_available': self.query_stats['redis_available']
        }
        
        # Add Redis stats if available
        if self.redis_cache.redis_client:
            redis_stats = self.redis_cache.get_stats()
            db_stats.update({'redis_stats': redis_stats})
        
        return db_stats
    
    def ensure_tables_exist(self):
        """Ensure all required tables exist with proper indexes"""
        try:
            with self.get_enhanced_connection() as conn:
                with conn.cursor() as cursor:
                    # Create tables if they don't exist
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS job_listings (
                            id SERIAL PRIMARY KEY,
                            title VARCHAR(500),
                            company VARCHAR(200),
                            location VARCHAR(200),
                            salary VARCHAR(200),
                            description TEXT,
                            requirements TEXT,
                            benefits TEXT,
                            contact_info TEXT,
                            application_url TEXT,
                            external_url TEXT,
                            html_content TEXT,
                            scraped_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS applications (
                            id SERIAL PRIMARY KEY,
                            job_id INTEGER REFERENCES job_listings(id),
                            application_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            status VARCHAR(50) DEFAULT 'applied',
                            notes TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    
                    # Create indexes for better performance
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_job_listings_scraped_date 
                        ON job_listings(scraped_date DESC)
                    """)
                    
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_job_listings_company 
                        ON job_listings(company)
                    """)
                    
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_applications_date 
                        ON applications(application_date DESC)
                    """)
                    
                    conn.commit()
                    self.logger.info("✅ Database tables and indexes ensured")
                    
        except Exception as e:
            self.logger.error(f"❌ Error ensuring tables exist: {e}")
            raise
    
    def close(self):
        """Close database connections and cleanup"""
        if self.connection_pool:
            self.connection_pool.closeall()
            self.logger.info("✅ Database connections closed")

def get_enhanced_db_manager() -> EnhancedPostgreSQLManager:
    """Get enhanced database manager instance"""
    return EnhancedPostgreSQLManager() 