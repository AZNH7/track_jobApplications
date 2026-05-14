"""
Unit tests for pure functions and logic that can run without Docker / DB.

Run with:
    pip install pytest
    pytest tests/
"""

import re
import sys
import types
import hashlib
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

# ---------------------------------------------------------------------------
# Make app/src importable without a running Docker environment
# ---------------------------------------------------------------------------
SRC = Path(__file__).parent.parent / "app" / "src"
sys.path.insert(0, str(SRC))


# ---------------------------------------------------------------------------
# Helpers — stub heavy optional dependencies so imports don't fail
# ---------------------------------------------------------------------------

def _stub_module(name: str) -> types.ModuleType:
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    return mod


for _dep in ("streamlit", "psycopg2", "psycopg2.pool", "psycopg2.extras",
             "pandas", "bs4", "requests", "tenacity", "langdetect",
             "PyPDF2", "pdfplumber", "selenium", "webdriver_manager",
             "selenium_stealth", "undetected_chromedriver", "pyppeteer",
             "cloudscraper"):
    if _dep not in sys.modules:
        _stub_module(_dep)

# psycopg2.pool.PoolError needs to be a real exception class
import psycopg2.pool as _pool  # noqa: E402
if not hasattr(_pool, "PoolError"):
    _pool.PoolError = type("PoolError", (Exception,), {})


# ===========================================================================
# #10 — content_hash deduplication
# ===========================================================================

class TestContentHash(unittest.TestCase):
    """Tests for JobListingsTable._compute_content_hash (pure static method)."""

    @classmethod
    def setUpClass(cls):
        # Import only what we need; skip DB connection entirely
        from database.job_listings_table import JobListingsTable
        # Wrap in staticmethod so self.fn(a, b) doesn't bind self as first arg
        cls.fn = staticmethod(JobListingsTable._compute_content_hash)

    def test_same_title_company_produces_same_hash(self):
        h1 = self.fn("Python Developer", "Acme Corp")
        h2 = self.fn("Python Developer", "Acme Corp")
        self.assertEqual(h1, h2)

    def test_case_insensitive(self):
        h1 = self.fn("python developer", "acme corp")
        h2 = self.fn("PYTHON DEVELOPER", "ACME CORP")
        self.assertEqual(h1, h2)

    def test_whitespace_stripped(self):
        h1 = self.fn("  Python Developer  ", "  Acme Corp  ")
        h2 = self.fn("Python Developer", "Acme Corp")
        self.assertEqual(h1, h2)

    def test_different_company_different_hash(self):
        h1 = self.fn("Python Developer", "Acme Corp")
        h2 = self.fn("Python Developer", "Beta GmbH")
        self.assertNotEqual(h1, h2)

    def test_different_title_different_hash(self):
        h1 = self.fn("Python Developer", "Acme Corp")
        h2 = self.fn("Java Developer", "Acme Corp")
        self.assertNotEqual(h1, h2)

    def test_empty_title_returns_none(self):
        self.assertIsNone(self.fn("", "Acme Corp"))

    def test_none_title_returns_none(self):
        self.assertIsNone(self.fn(None, "Acme Corp"))

    def test_empty_company_returns_none(self):
        self.assertIsNone(self.fn("Python Developer", ""))

    def test_none_company_returns_none(self):
        self.assertIsNone(self.fn("Python Developer", None))

    def test_returns_md5_hex_string(self):
        h = self.fn("Python Developer", "Acme Corp")
        self.assertIsNotNone(h)
        self.assertEqual(len(h), 32)
        self.assertRegex(h, r'^[0-9a-f]{32}$')

    def test_cross_platform_match(self):
        """Same job scraped from Indeed and LinkedIn should hash identically."""
        indeed_hash = self.fn("Senior Python Developer", "Acme Corp")
        linkedin_hash = self.fn("Senior Python Developer", "Acme Corp")
        self.assertEqual(indeed_hash, linkedin_hash)


# ===========================================================================
# #11 — session state trimming
# ===========================================================================

class _FakeSessionState:
    """Minimal st.session_state stand-in that supports both attribute and dict-style access."""
    def __init__(self, data: dict):
        object.__setattr__(self, '_data', data)

    def get(self, key, default=None):
        return self._data.get(key, default)

    def __setattr__(self, key, value):
        self._data[key] = value

    def __getattr__(self, key):
        try:
            return self._data[key]
        except KeyError:
            raise AttributeError(key)

    def __contains__(self, key):
        return key in self._data


class TestTrimSessionState(unittest.TestCase):
    """Tests for SessionStateManager.trim_session_state."""

    def _make_session(self, log_size=0, email_size=0, test_results_size=0):
        """Return a mock st.session_state dict-like object."""
        state = {
            "search_log": list(range(log_size)),
            "email_log_messages": list(range(email_size)),
            "platform_test_results": {f"k{i}": i for i in range(test_results_size)},
        }
        return state

    def _run_trim(self, state: dict):
        """Patch st.session_state and call trim_session_state."""
        with patch("core.session_state.st") as mock_st:
            mock_st.session_state = _FakeSessionState(state)
            from core.session_state import SessionStateManager
            SessionStateManager.trim_session_state()
        return state

    def test_search_log_trimmed_when_over_limit(self):
        state = self._run_trim(self._make_session(log_size=200))
        self.assertLessEqual(len(state["search_log"]), 100)

    def test_search_log_keeps_newest_entries(self):
        entries = list(range(150))
        state = {"search_log": entries, "email_log_messages": [], "platform_test_results": {}}
        with patch("core.session_state.st") as mock_st:
            mock_st.session_state = _FakeSessionState(state)
            from core.session_state import SessionStateManager
            SessionStateManager.trim_session_state()
        self.assertEqual(state["search_log"], list(range(50, 150)))

    def test_search_log_unchanged_when_under_limit(self):
        state = self._run_trim(self._make_session(log_size=50))
        self.assertEqual(len(state["search_log"]), 50)

    def test_email_log_trimmed(self):
        state = self._run_trim(self._make_session(email_size=200))
        self.assertLessEqual(len(state["email_log_messages"]), 100)

    def test_platform_test_results_trimmed(self):
        state = self._run_trim(self._make_session(test_results_size=80))
        self.assertLessEqual(len(state["platform_test_results"]), 50)

    def test_platform_test_results_unchanged_when_under_limit(self):
        state = self._run_trim(self._make_session(test_results_size=30))
        self.assertEqual(len(state["platform_test_results"]), 30)

    def test_missing_keys_do_not_raise(self):
        """trim_session_state must be safe if a key hasn't been initialised yet."""
        with patch("core.session_state.st") as mock_st:
            mock_st.session_state = _FakeSessionState({})
            from core.session_state import SessionStateManager
            SessionStateManager.trim_session_state()  # should not raise


# ===========================================================================
# #6 — input sanitisation (regex logic extracted from enhanced_job_search.py)
# ===========================================================================

def _sanitize_text(value: str, max_len: int = 200) -> str:
    """Mirror of the sanitisation applied in enhanced_job_search.py."""
    return re.sub(r'[\x00-\x1f\x7f]', '', value)[:max_len]


class TestInputSanitization(unittest.TestCase):
    """Tests for keyword / location sanitisation before scraping."""

    def test_normal_text_passes_through(self):
        self.assertEqual(_sanitize_text("Python Developer"), "Python Developer")

    def test_control_chars_stripped(self):
        self.assertEqual(_sanitize_text("Python\x00Developer"), "PythonDeveloper")

    def test_newline_stripped(self):
        self.assertEqual(_sanitize_text("Python\nDeveloper"), "PythonDeveloper")

    def test_tab_stripped(self):
        self.assertEqual(_sanitize_text("Python\tDeveloper"), "PythonDeveloper")

    def test_del_char_stripped(self):
        self.assertEqual(_sanitize_text("Python\x7fDeveloper"), "PythonDeveloper")

    def test_truncated_at_max_len(self):
        long_input = "A" * 300
        self.assertEqual(len(_sanitize_text(long_input)), 200)

    def test_empty_string(self):
        self.assertEqual(_sanitize_text(""), "")

    def test_unicode_preserved(self):
        self.assertEqual(_sanitize_text("Entwickler München"), "Entwickler München")

    def test_only_control_chars_returns_empty(self):
        self.assertEqual(_sanitize_text("\x00\x01\x02"), "")


# ===========================================================================
# #17 — constants module sanity
# ===========================================================================

class TestConstants(unittest.TestCase):
    """Smoke tests ensuring constants.py exports the expected names and types."""

    @classmethod
    def setUpClass(cls):
        import constants
        cls.c = constants

    def test_session_timeout_positive(self):
        self.assertGreater(self.c.SESSION_403_WINDOW_SECS, 0)
        self.assertGreater(self.c.SESSION_MAX_AGE_SECS, 0)

    def test_db_pool_range_valid(self):
        self.assertGreater(self.c.DB_POOL_MAX_CONNS, self.c.DB_POOL_MIN_CONNS)

    def test_worker_counts_positive(self):
        self.assertGreater(self.c.LLM_BATCH_WORKERS, 0)
        self.assertGreater(self.c.PROCESSOR_BATCH_WORKERS, 0)

    def test_application_status_strings_non_empty(self):
        from constants import ApplicationStatus
        for attr in ("SAVED", "APPLIED", "INTERVIEW", "OFFERED", "REJECTED"):
            val = getattr(ApplicationStatus, attr)
            self.assertIsInstance(val, str)
            self.assertTrue(val)

    def test_table_names_non_empty(self):
        from constants import TableName
        for attr in ("JOB_LISTINGS", "JOB_APPLICATIONS", "JOB_OFFERS",
                     "FILTERED_JOBS", "IGNORED_JOBS", "SAVED_SEARCHES"):
            val = getattr(TableName, attr)
            self.assertIsInstance(val, str)
            self.assertTrue(val)

    def test_session_log_caps_reasonable(self):
        self.assertGreater(self.c.SESSION_MAX_LOG_ENTRIES, 0)
        self.assertGreater(self.c.SESSION_MAX_TEST_RESULTS, 0)


if __name__ == "__main__":
    unittest.main()
