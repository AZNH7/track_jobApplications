"""
Redis Cache Manager for Job Tracker
Provides persistent, shared caching across sessions and users
"""

import redis
import json
import pickle
import time
import logging
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
import streamlit as st

logger = logging.getLogger(__name__)

class RedisCacheManager:
    """Redis-based cache manager for improved performance and persistence"""
    
    def __init__(self, host: str = 'localhost', port: int = 6379, 
                 db: int = 0, password: str = None, 
                 default_ttl: int = 3600):
        """Initialize Redis cache manager"""
        self.default_ttl = default_ttl
        self.redis_client = None
        self._connect_redis(host, port, db, password)
        
    def _connect_redis(self, host: str, port: int, db: int, password: str):
        """Connect to Redis with error handling"""
        try:
            self.redis_client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=False,  # Keep binary for pickle
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            # Test connection
            self.redis_client.ping()
            logger.info(f"✅ Connected to Redis at {host}:{port}")
        except Exception as e:
            logger.warning(f"❌ Redis connection failed: {e}")
            self.redis_client = None
    
    def _serialize_data(self, data: Any) -> bytes:
        """Serialize data for Redis storage"""
        try:
            return pickle.dumps(data)
        except Exception as e:
            logger.error(f"Serialization error: {e}")
            return pickle.dumps(str(data))
    
    def _deserialize_data(self, data: bytes) -> Any:
        """Deserialize data from Redis storage"""
        try:
            return pickle.loads(data)
        except Exception as e:
            logger.error(f"Deserialization error: {e}")
            return None
    
    def _get_cache_key(self, key: str, prefix: str = "jobtracker") -> str:
        """Generate consistent cache key"""
        return f"{prefix}:{key}"
    
    def set(self, key: str, data: Any, ttl: int = None, prefix: str = "jobtracker") -> bool:
        """Set data in Redis cache"""
        if not self.redis_client:
            return False
            
        try:
            cache_key = self._get_cache_key(key, prefix)
            serialized_data = self._serialize_data(data)
            ttl = ttl or self.default_ttl
            
            result = self.redis_client.setex(cache_key, ttl, serialized_data)
            logger.debug(f"Cache SET: {cache_key} (TTL: {ttl}s)")
            return bool(result)
        except Exception as e:
            logger.error(f"Redis SET error: {e}")
            return False
    
    def get(self, key: str, prefix: str = "jobtracker") -> Optional[Any]:
        """Get data from Redis cache"""
        if not self.redis_client:
            return None
            
        try:
            cache_key = self._get_cache_key(key, prefix)
            data = self.redis_client.get(cache_key)
            
            if data is not None:
                logger.debug(f"Cache HIT: {cache_key}")
                return self._deserialize_data(data)
            else:
                logger.debug(f"Cache MISS: {cache_key}")
                return None
        except Exception as e:
            logger.error(f"Redis GET error: {e}")
            return None
    
    def delete(self, key: str, prefix: str = "jobtracker") -> bool:
        """Delete data from Redis cache"""
        if not self.redis_client:
            return False
            
        try:
            cache_key = self._get_cache_key(key, prefix)
            result = self.redis_client.delete(cache_key)
            logger.debug(f"Cache DELETE: {cache_key}")
            return bool(result)
        except Exception as e:
            logger.error(f"Redis DELETE error: {e}")
            return False
    
    def exists(self, key: str, prefix: str = "jobtracker") -> bool:
        """Check if key exists in cache"""
        if not self.redis_client:
            return False
            
        try:
            cache_key = self._get_cache_key(key, prefix)
            return bool(self.redis_client.exists(cache_key))
        except Exception as e:
            logger.error(f"Redis EXISTS error: {e}")
            return False
    
    def get_ttl(self, key: str, prefix: str = "jobtracker") -> int:
        """Get remaining TTL for a key"""
        if not self.redis_client:
            return -1
            
        try:
            cache_key = self._get_cache_key(key, prefix)
            return self.redis_client.ttl(cache_key)
        except Exception as e:
            logger.error(f"Redis TTL error: {e}")
            return -1
    
    def clear_pattern(self, pattern: str = "jobtracker:*") -> int:
        """Clear all keys matching pattern"""
        if not self.redis_client:
            return 0
            
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                deleted = self.redis_client.delete(*keys)
                logger.info(f"Cleared {deleted} cache entries matching '{pattern}'")
                return deleted
            return 0
        except Exception as e:
            logger.error(f"Redis CLEAR error: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.redis_client:
            return {"status": "disconnected"}
            
        try:
            info = self.redis_client.info()
            keys = self.redis_client.keys("jobtracker:*")
            
            return {
                "status": "connected",
                "total_keys": len(keys),
                "memory_used": info.get('used_memory_human', 'N/A'),
                "connected_clients": info.get('connected_clients', 0),
                "uptime": info.get('uptime_in_seconds', 0),
                "hit_rate": info.get('keyspace_hits', 0) / max(info.get('keyspace_misses', 1), 1)
            }
        except Exception as e:
            logger.error(f"Redis STATS error: {e}")
            return {"status": "error", "error": str(e)}
    
    def cache_function_result(self, func_name: str, args: tuple, kwargs: dict, 
                            result: Any, ttl: int = None) -> bool:
        """Cache function result with automatic key generation"""
        # Create cache key from function name and arguments
        key_parts = [func_name]
        if args:
            key_parts.append(str(hash(args)))
        if kwargs:
            key_parts.append(str(hash(frozenset(kwargs.items()))))
        
        cache_key = "_".join(key_parts)
        return self.set(cache_key, result, ttl, "function_cache")
    
    def get_function_result(self, func_name: str, args: tuple, kwargs: dict) -> Optional[Any]:
        """Get cached function result"""
        key_parts = [func_name]
        if args:
            key_parts.append(str(hash(args)))
        if kwargs:
            key_parts.append(str(hash(frozenset(kwargs.items()))))
        
        cache_key = "_".join(key_parts)
        return self.get(cache_key, "function_cache")

# Global Redis cache manager instance
_redis_cache = None

def get_redis_cache() -> RedisCacheManager:
    """Get global Redis cache manager instance"""
    global _redis_cache
    if _redis_cache is None:
        # Get Redis config from environment or use defaults
        import os
        host = os.getenv('REDIS_HOST', 'localhost')
        port = int(os.getenv('REDIS_PORT', '6379'))
        password = os.getenv('REDIS_PASSWORD')
        db = int(os.getenv('REDIS_DB', '0'))
        
        _redis_cache = RedisCacheManager(host, port, db, password)
    return _redis_cache

def redis_cache_decorator(ttl: int = 3600):
    """Decorator for caching function results in Redis"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            cache = get_redis_cache()
            
            # Try to get from cache
            cached_result = cache.get_function_result(func.__name__, args, kwargs)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.cache_function_result(func.__name__, args, kwargs, result, ttl)
            return result
        
        return wrapper
    return decorator 