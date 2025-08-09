"""
Performance View for Job Tracker
Demonstrates Redis cache integration and performance monitoring
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time
import logging

from utils.performance_monitor import get_performance_monitor
from database_manager_with_redis import get_enhanced_db_manager
from core.redis_cache_manager import get_redis_cache

logger = logging.getLogger(__name__)

class PerformanceView:
    """Performance monitoring and cache management view"""
    
    def __init__(self):
        self.performance_monitor = get_performance_monitor()
        self.redis_cache = get_redis_cache()
        self.db_manager = get_enhanced_db_manager()
    
    def show(self):
        """Display the performance view"""
        st.title("🚀 Performance & Cache Management")
        
        # Check Redis connection
        redis_status = self.redis_cache.get_stats()
        
        if redis_status.get('status') == 'disconnected':
            st.error("❌ Redis is not connected. Performance monitoring will be limited.")
            st.info("To enable Redis caching, make sure Redis is running and accessible.")
        else:
            st.success("✅ Redis is connected and ready for caching!")
        
        # Performance tabs
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 Performance Dashboard", 
            "⚡ Cache Management", 
            "🔧 Performance Tests",
            "📈 Database Stats"
        ])
        
        with tab1:
            self.show_performance_dashboard()
        
        with tab2:
            self.show_cache_management()
        
        with tab3:
            self.show_performance_tests()
        
        with tab4:
            self.show_database_stats()
    
    def show_performance_dashboard(self):
        """Show performance monitoring dashboard"""
        self.performance_monitor.show_performance_dashboard()
    
    def show_cache_management(self):
        """Show cache management interface"""
        st.header("⚡ Cache Management")
        
        # Redis stats
        redis_stats = self.redis_cache.get_stats()
        
        if redis_stats.get('status') == 'connected':
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Keys", redis_stats.get('total_keys', 0))
            
            with col2:
                st.metric("Memory Used", redis_stats.get('memory_used', 'N/A'))
            
            with col3:
                st.metric("Connected Clients", redis_stats.get('connected_clients', 0))
            
            with col4:
                hit_rate = redis_stats.get('hit_rate', 0)
                st.metric("Hit Rate", f"{hit_rate:.1f}%")
            
            # Cache operations
            st.subheader("Cache Operations")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🔄 Refresh Cache Stats"):
                    st.rerun()
                
                if st.button("🗑️ Clear All Cache"):
                    deleted = self.redis_cache.clear_pattern("jobtracker:*")
                    st.success(f"Cleared {deleted} cache entries")
                    st.rerun()
            
            with col2:
                cache_pattern = st.text_input("Cache Pattern to Clear", "jobtracker:*")
                if st.button("🗑️ Clear Pattern"):
                    deleted = self.redis_cache.clear_pattern(cache_pattern)
                    st.success(f"Cleared {deleted} cache entries matching '{cache_pattern}'")
                    st.rerun()
            
            # Cache test
            st.subheader("Cache Test")
            
            test_key = st.text_input("Test Key", "test_key")
            test_value = st.text_input("Test Value", "test_value")
            test_ttl = st.number_input("TTL (seconds)", min_value=1, max_value=3600, value=300)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("💾 Set Cache"):
                    success = self.redis_cache.set(test_key, test_value, test_ttl)
                    if success:
                        st.success("Cache set successfully!")
                    else:
                        st.error("Failed to set cache")
            
            with col2:
                if st.button("📖 Get Cache"):
                    value = self.redis_cache.get(test_key)
                    if value is not None:
                        st.success(f"Cache value: {value}")
                    else:
                        st.warning("Cache key not found")
            
            with col3:
                if st.button("❌ Delete Cache"):
                    success = self.redis_cache.delete(test_key)
                    if success:
                        st.success("Cache deleted successfully!")
                    else:
                        st.warning("Cache key not found or already deleted")
        else:
            st.warning("Redis is not connected. Cache management features are unavailable.")
    
    def show_performance_tests(self):
        """Show performance testing interface"""
        st.header("🔧 Performance Tests")
        
        st.info("Run these tests to measure the performance impact of Redis caching.")
        
        # Test configuration
        st.subheader("Test Configuration")
        
        col1, col2 = st.columns(2)
        
        with col1:
            num_queries = st.number_input("Number of Queries", min_value=1, max_value=100, value=10)
            query_type = st.selectbox("Query Type", ["job_listings", "applications", "statistics"])
        
        with col2:
            cache_enabled = st.checkbox("Enable Cache", value=True)
            test_duration = st.number_input("Test Duration (seconds)", min_value=1, max_value=60, value=30)
        
        # Run performance test
        if st.button("🚀 Run Performance Test"):
            self.run_performance_test(num_queries, query_type, cache_enabled, test_duration)
    
    def run_performance_test(self, num_queries: int, query_type: str, cache_enabled: bool, duration: int):
        """Run a performance test"""
        st.subheader("Test Results")
        
        # Clear previous cache if needed
        if not cache_enabled:
            self.redis_cache.clear_pattern("jobtracker:*")
        
        # Test queries
        start_time = time.time()
        results = []
        
        with st.spinner(f"Running {num_queries} queries..."):
            for i in range(num_queries):
                query_start = time.time()
                
                try:
                    if query_type == "job_listings":
                        result = self.db_manager.get_job_listings_cached(limit=100, offset=i * 100)
                    elif query_type == "applications":
                        result = self.db_manager.get_applications_cached()
                    elif query_type == "statistics":
                        result = self.db_manager.get_job_statistics_cached()
                    
                    query_time = time.time() - query_start
                    results.append({
                        'query_number': i + 1,
                        'execution_time': query_time,
                        'cache_hit': cache_enabled and i > 0,  # First query is always a miss
                        'result_size': len(str(result)) if result else 0
                    })
                    
                except Exception as e:
                    st.error(f"Query {i + 1} failed: {e}")
                    break
        
        total_time = time.time() - start_time
        
        # Display results
        if results:
            df = pd.DataFrame(results)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Time", f"{total_time:.3f}s")
            
            with col2:
                avg_time = df['execution_time'].mean()
                st.metric("Avg Query Time", f"{avg_time:.3f}s")
            
            with col3:
                cache_hits = len(df[df['cache_hit'] == True])
                hit_rate = (cache_hits / len(df)) * 100
                st.metric("Cache Hit Rate", f"{hit_rate:.1f}%")
            
            # Performance chart
            st.subheader("Query Performance")
            
            import plotly.express as px
            
            fig = px.line(df, x='query_number', y='execution_time', 
                         color='cache_hit', title='Query Execution Times')
            st.plotly_chart(fig, use_container_width=True)
            
            # Results table
            st.subheader("Detailed Results")
            st.dataframe(df, use_container_width=True)
    
    def show_database_stats(self):
        """Show database performance statistics"""
        st.header("📈 Database Performance Statistics")
        
        try:
            db_stats = self.db_manager.get_performance_stats()
            
            if db_stats:
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Queries", db_stats.get('total_queries', 0))
                
                with col2:
                    st.metric("Cache Hits", db_stats.get('cache_hits', 0))
                
                with col3:
                    hit_rate = db_stats.get('cache_hit_rate', 0)
                    st.metric("Cache Hit Rate", f"{hit_rate:.1f}%")
                
                with col4:
                    st.metric("Slow Queries", db_stats.get('slow_queries', 0))
                
                # Redis stats if available
                if 'redis_stats' in db_stats:
                    st.subheader("Redis Statistics")
                    redis_stats = db_stats['redis_stats']
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Redis Keys", redis_stats.get('total_keys', 0))
                    
                    with col2:
                        st.metric("Memory Used", redis_stats.get('memory_used', 'N/A'))
                    
                    with col3:
                        st.metric("Connected Clients", redis_stats.get('connected_clients', 0))
                    
                    with col4:
                        uptime_hours = redis_stats.get('uptime', 0) / 3600
                        st.metric("Uptime", f"{uptime_hours:.1f}h")
                
                # Performance recommendations
                st.subheader("💡 Performance Insights")
                
                insights = []
                
                if db_stats.get('cache_hit_rate', 0) < 50:
                    insights.append("🔴 **Low cache hit rate**: Consider increasing cache TTL or adding more cacheable queries")
                
                if db_stats.get('slow_queries', 0) > 0:
                    insights.append("🟡 **Slow queries detected**: Review and optimize slow queries")
                
                if db_stats.get('timeouts', 0) > 0:
                    insights.append("🟠 **Query timeouts**: Consider increasing timeout values or optimizing queries")
                
                if db_stats.get('cache_hit_rate', 0) > 80:
                    insights.append("🟢 **Excellent cache performance**: Cache is working very well!")
                
                if not insights:
                    insights.append("✅ **Good performance**: No immediate optimizations needed")
                
                for insight in insights:
                    st.write(insight)
            
            else:
                st.warning("No database statistics available.")
                
        except Exception as e:
            st.error(f"Error retrieving database statistics: {e}")

def show_performance_page():
    """Show the performance page"""
    view = PerformanceView()
    view.show() 