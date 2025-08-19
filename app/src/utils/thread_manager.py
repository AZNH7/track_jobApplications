import threading
import streamlit as st
from contextlib import contextmanager
from typing import Optional

class ThreadContextManager:
    """
    Manages Streamlit thread context for background operations
    """
    _thread_local = threading.local()
    
    @classmethod
    @contextmanager
    def use_context(cls):
        """
        Context manager to ensure thread has proper Streamlit context
        """
        try:
            # Get current script run context if available
            ctx = st.runtime.get_instance()._get_script_run_ctx() if hasattr(st, 'runtime') else None
            if ctx is not None:
                cls._thread_local.context = ctx
            yield
        finally:
            # Clean up context
            if hasattr(cls._thread_local, 'context'):
                delattr(cls._thread_local, 'context')

    @classmethod
    def wrap_callback(cls, func):
        """
        Decorator to wrap functions that need Streamlit context
        """
        def wrapper(*args, **kwargs):
            with cls.use_context():
                return func(*args, **kwargs)
        return wrapper 