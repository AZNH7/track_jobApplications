"""
Performance Monitoring Utility
Tracks and compares database query performance with and without Redis caching
"""

import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import streamlit as st
from dataclasses import dataclass
from collections import defaultdict

logger = logging.getLogger(__name__)

@dataclass
class QueryMetrics:
    """Metrics for a single query execution"""
    query: str
    execution_time: float
    cache_hit: bool
    timestamp: datetime
    result_size: int
    error: Optional[str] = None

class PerformanceMonitor:
    """Monitor and analyze database query performance"""
    
    def __init__(self):
        self.query_history: List[QueryMetrics] = []
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'total_queries': 0
        }
        
    def record_query(self, query: str, execution_time: float, 
                    cache_hit: bool, result_size: int = 0, 
                    error: Optional[str] = None):
        """Record a query execution"""
        metrics = QueryMetrics(
            query=query,
            execution_time=execution_time,
            cache_hit=cache_hit,
            timestamp=datetime.now(),
            result_size=result_size,
            error=error
        )
        
        self.query_history.append(metrics)
        
        # Update cache stats
        self.cache_stats['total_queries'] += 1
        if cache_hit:
            self.cache_stats['hits'] += 1
        else:
            self.cache_stats['misses'] += 1
    
    def get_cache_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.cache_stats['total_queries']
        if total == 0:
            return 0.0
        return (self.cache_stats['hits'] / total) * 100
    
    def get_average_query_time(self, cache_hits_only: bool = False) -> float:
        """Calculate average query execution time"""
        if not self.query_history:
            return 0.0
        
        filtered_queries = [
            q for q in self.query_history 
            if q.cache_hit == cache_hits_only and q.error is None
        ]
        
        if not filtered_queries:
            return 0.0
        
        return sum(q.execution_time for q in filtered_queries) / len(filtered_queries)
    
    def get_slow_queries(self, threshold: float = 5.0) -> List[QueryMetrics]:
        """Get queries that took longer than threshold"""
        return [
            q for q in self.query_history 
            if q.execution_time > threshold and q.error is None
        ]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        if not self.query_history:
            return {"status": "No queries recorded"}
        
        # Calculate time-based metrics
        now = datetime.now()
        last_hour = [q for q in self.query_history if now - q.timestamp < timedelta(hours=1)]
        last_day = [q for q in self.query_history if now - q.timestamp < timedelta(days=1)]
        
        # Cache performance
        cache_hits = [q for q in self.query_history if q.cache_hit]
        cache_misses = [q for q in self.query_history if not q.cache_hit]
        
        summary = {
            'total_queries': len(self.query_history),
            'queries_last_hour': len(last_hour),
            'queries_last_day': len(last_day),
            'cache_hit_rate': self.get_cache_hit_rate(),
            'cache_hits': len(cache_hits),
            'cache_misses': len(cache_misses),
            'avg_query_time_all': self.get_average_query_time(),
            'avg_query_time_cache_hits': self.get_average_query_time(cache_hits_only=True),
            'avg_query_time_cache_misses': self.get_average_query_time(cache_hits_only=False),
            'slow_queries': len(self.get_slow_queries()),
            'errors': len([q for q in self.query_history if q.error]),
            'total_data_transferred': sum(q.result_size for q in self.query_history),
            'performance_improvement': self._calculate_performance_improvement()
        }
        
        return summary
    
    def _calculate_performance_improvement(self) -> Dict[str, float]:
        """Calculate performance improvement metrics"""
        cache_hits = [q for q in self.query_history if q.cache_hit and q.error is None]
        cache_misses = [q for q in self.query_history if not q.cache_hit and q.error is None]
        
        if not cache_misses:
            return {"time_saved": 0.0, "time_saved_percentage": 0.0}
        
        avg_cache_miss_time = sum(q.execution_time for q in cache_misses) / len(cache_misses)
        avg_cache_hit_time = sum(q.execution_time for q in cache_hits) / len(cache_hits) if cache_hits else 0
        
        time_saved_per_query = avg_cache_miss_time - avg_cache_hit_time
        total_time_saved = time_saved_per_query * len(cache_hits)
        
        return {
            "time_saved": total_time_saved,
            "time_saved_percentage": (time_saved_per_query / avg_cache_miss_time) * 100 if avg_cache_miss_time > 0 else 0
        }
    
    def show_performance_dashboard(self):
        """Display performance dashboard in Streamlit"""
        st.header("🚀 Performance Monitor")
        
        summary = self.get_performance_summary()
        
        if summary.get("status") == "No queries recorded":
            st.info("No queries have been recorded yet. Start using the application to see performance metrics.")
            return
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Cache Hit Rate", 
                f"{summary['cache_hit_rate']:.1f}%",
                f"{summary['cache_hits']} hits"
            )
        
        with col2:
            st.metric(
                "Avg Query Time", 
                f"{summary['avg_query_time_all']:.3f}s",
                f"{summary['queries_last_hour']} last hour"
            )
        
        with col3:
            st.metric(
                "Performance Improvement", 
                f"{summary['performance_improvement']['time_saved_percentage']:.1f}%",
                f"{summary['performance_improvement']['time_saved']:.1f}s saved"
            )
        
        with col4:
            st.metric(
                "Slow Queries", 
                summary['slow_queries'],
                f"{summary['errors']} errors"
            )
        
        # Detailed charts
        st.subheader("📊 Performance Trends")
        
        if len(self.query_history) > 1:
            # Query time distribution
            import plotly.express as px
            import pandas as pd
            
            # Prepare data for plotting
            df = pd.DataFrame([
                {
                    'timestamp': q.timestamp,
                    'execution_time': q.execution_time,
                    'cache_hit': 'Cache Hit' if q.cache_hit else 'Cache Miss',
                    'query_type': q.query.split()[0] if q.query else 'Unknown'
                }
                for q in self.query_history if q.error is None
            ])
            
            if not df.empty:
                # Execution time over time
                fig1 = px.line(df, x='timestamp', y='execution_time', 
                             color='cache_hit', title='Query Execution Time Over Time')
                st.plotly_chart(fig1, use_container_width=True)
                
                # Cache hit distribution
                cache_dist = df['cache_hit'].value_counts()
                fig2 = px.pie(values=cache_dist.values, names=cache_dist.index, 
                            title='Cache Hit Distribution')
                st.plotly_chart(fig2, use_container_width=True)
        
        # Slow queries table
        slow_queries = self.get_slow_queries()
        if slow_queries:
            st.subheader("🐌 Slow Queries (>5s)")
            
            slow_df = pd.DataFrame([
                {
                    'Query': q.query[:100] + '...' if len(q.query) > 100 else q.query,
                    'Execution Time': f"{q.execution_time:.3f}s",
                    'Cache Hit': 'Yes' if q.cache_hit else 'No',
                    'Timestamp': q.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    'Result Size': q.result_size
                }
                for q in slow_queries
            ])
            
            st.dataframe(slow_df, use_container_width=True)
        
        # Cache recommendations
        st.subheader("💡 Performance Recommendations")
        
        recommendations = []
        
        if summary['cache_hit_rate'] < 50:
            recommendations.append("🔴 **Low cache hit rate**: Consider increasing cache TTL or adding more cacheable queries")
        
        if summary['avg_query_time_cache_misses'] > 2.0:
            recommendations.append("🟡 **Slow cache misses**: Consider optimizing database queries or adding indexes")
        
        if summary['slow_queries'] > 0:
            recommendations.append("🟠 **Slow queries detected**: Review and optimize slow queries")
        
        if summary['performance_improvement']['time_saved_percentage'] > 50:
            recommendations.append("🟢 **Excellent cache performance**: Cache is working well!")
        
        if not recommendations:
            recommendations.append("✅ **Good performance**: No immediate optimizations needed")
        
        for rec in recommendations:
            st.write(rec)

# Global performance monitor instance
_performance_monitor = None

def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor

def monitor_query(func):
    """Decorator to monitor query performance"""
    def wrapper(*args, **kwargs):
        monitor = get_performance_monitor()
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Determine if it was a cache hit (this would need to be passed from the calling function)
            cache_hit = kwargs.get('cache_hit', False)
            result_size = len(str(result)) if result else 0
            
            monitor.record_query(
                query=func.__name__,
                execution_time=execution_time,
                cache_hit=cache_hit,
                result_size=result_size
            )
            
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            monitor.record_query(
                query=func.__name__,
                execution_time=execution_time,
                cache_hit=False,
                error=str(e)
            )
            raise
    
    return wrapper 