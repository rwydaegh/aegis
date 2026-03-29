"""
Performance utilities for Flanders base station extraction.
Includes caching mechanisms and optimization helpers.
"""

import functools
import pickle
import hashlib
from pathlib import Path
from typing import Any, Callable


class QueryCache:
    """Simple in-memory cache for SPARQL query results."""
    
    def __init__(self, max_size: int = 1000):
        """Initialize cache with max size limit."""
        self._cache = {}
        self._access_order = []
        self.max_size = max_size
    
    def _get_key(self, endpoint: str, query: str) -> str:
        """Generate cache key from endpoint and query."""
        cache_str = f"{endpoint}:{query}"
        return hashlib.md5(cache_str.encode()).hexdigest()
    
    def get(self, endpoint: str, query: str) -> Any:
        """Retrieve cached result if available."""
        key = self._get_key(endpoint, query)
        if key in self._cache:
            # Move to end for LRU tracking
            self._access_order.remove(key)
            self._access_order.append(key)
            return self._cache[key]
        return None
    
    def set(self, endpoint: str, query: str, result: Any):
        """Store result in cache with LRU eviction."""
        key = self._get_key(endpoint, query)
        
        if key in self._cache:
            self._access_order.remove(key)
        elif len(self._cache) >= self.max_size:
            # Evict least recently used
            lru_key = self._access_order.pop(0)
            del self._cache[lru_key]
        
        self._cache[key] = result
        self._access_order.append(key)
    
    def clear(self):
        """Clear entire cache."""
        self._cache.clear()
        self._access_order.clear()


# Global cache instance
_query_cache = QueryCache(max_size=500)


def cached_sparql_query(func: Callable) -> Callable:
    """
    Decorator for caching SPARQL query results.
    
    Usage:
        @cached_sparql_query
        def get_antennas(sparql_url, limit, offset):
            ...
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        # Try to get from cache
        query_hash = hashlib.md5(
            f"{self.sparql_url}_{args}_{kwargs}".encode()
        ).hexdigest()
        
        cached = _query_cache.get(self.sparql_url, query_hash)
        if cached is not None:
            return cached
        
        # Execute function
        result = func(self, *args, **kwargs)
        
        # Cache result if successful
        if result:
            _query_cache.set(self.sparql_url, query_hash, result)
        
        return result
    
    return wrapper


class PickleCache:
    """Persistent cache using pickle files."""
    
    @staticmethod
    def save(data: Any, filepath: str):
        """Save data to pickle file."""
        try:
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, 'wb') as f:
                pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
            print(f"Cache saved to {filepath}")
            return True
        except Exception as e:
            print(f"Error saving cache: {e}")
            return False
    
    @staticmethod
    def load(filepath: str) -> Any:
        """Load data from pickle file."""
        try:
            if not Path(filepath).exists():
                return None
            with open(filepath, 'rb') as f:
                data = pickle.load(f)
            return data
        except Exception as e:
            print(f"Error loading cache: {e}")
            return None


def batch_iterator(items: list, batch_size: int):
    """
    Generator that yields batches of items.
    
    Args:
        items: List of items to batch
        batch_size: Size of each batch
    
    Yields:
        Lists of size batch_size (last batch may be smaller)
    """
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]


def estimate_memory_usage(df_size: int, num_columns: int) -> str:
    """
    Estimate memory usage of a DataFrame in MB.
    
    Args:
        df_size: Number of rows
        num_columns: Number of columns
    
    Returns:
        Human-readable memory estimate
    """
    # Rough estimate: 8 bytes per numeric cell, 50 bytes per string cell
    estimated_bytes = (df_size * num_columns * 8) + (df_size * num_columns * 42)  # average
    estimated_mb = estimated_bytes / (1024 * 1024)
    return f"{estimated_mb:.1f} MB"


class Timer:
    """Simple context manager for timing operations."""
    
    def __init__(self, operation_name: str = "Operation"):
        """Initialize timer with operation name."""
        self.operation_name = operation_name
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        """Start timing."""
        import time
        self.start_time = time.time()
        return self
    
    def __exit__(self, *args):
        """Stop timing and print result."""
        import time
        self.end_time = time.time()
        elapsed = self.end_time - self.start_time
        print(f"{self.operation_name} completed in {elapsed:.2f} seconds")
    
    def elapsed(self) -> float:
        """Get elapsed time in seconds."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None
