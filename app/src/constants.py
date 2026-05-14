"""
Application-wide constants.

Centralises magic numbers, status literals, and table names that were previously
scattered across the codebase. Import from here instead of using bare strings or
inline numbers so that a single change propagates everywhere.
"""


# ---------------------------------------------------------------------------
# Scraper / session timing
# ---------------------------------------------------------------------------

# Seconds of consecutive-403 activity before the scraper session is refreshed.
SESSION_403_WINDOW_SECS: int = 300

# Maximum age (seconds) of a scraper session before a preventive refresh.
SESSION_MAX_AGE_SECS: int = 1800  # 30 minutes

# Default inter-request delay (seconds) when no domain-specific rule exists.
DEFAULT_REQUEST_DELAY_SECS: float = 1.5

# Per-domain rate-limit delays (seconds).
RATE_LIMIT_LINKEDIN_SECS: float = 5.0
RATE_LIMIT_JOBRAPIDO_SECS: float = 2.0


# ---------------------------------------------------------------------------
# Database connection pool
# ---------------------------------------------------------------------------

DB_POOL_MIN_CONNS: int = 1
DB_POOL_MAX_CONNS: int = 10

# Seconds before a new TCP connection to Postgres is declared failed.
DB_CONNECT_TIMEOUT_SECS: int = 10

# Milliseconds; PostgreSQL kills any query that runs longer than this.
DB_STATEMENT_TIMEOUT_MS: int = 30_000


# ---------------------------------------------------------------------------
# LLM / worker concurrency
# ---------------------------------------------------------------------------

# Thread-pool workers used for parallel LLM batch processing.
LLM_BATCH_WORKERS: int = 4

# Thread-pool workers used inside EnhancedJobProcessor for parallel analysis.
PROCESSOR_BATCH_WORKERS: int = 3

# Default Ollama request timeout (seconds).  Must match job_tracker_config.json.
OLLAMA_DEFAULT_TIMEOUT_SECS: int = 300


# ---------------------------------------------------------------------------
# Session-state caps  (see core/session_state.py)
# ---------------------------------------------------------------------------

SESSION_MAX_LOG_ENTRIES: int = 100
SESSION_MAX_TEST_RESULTS: int = 50


# ---------------------------------------------------------------------------
# Application / job status literals
# ---------------------------------------------------------------------------

class ApplicationStatus:
    """Status values stored in the job_applications table."""
    SAVED = "saved"
    APPLIED = "applied"
    INTERVIEW = "interview"
    OFFERED = "offered"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class JobOfferStatus:
    """Status values stored in the job_offers table."""
    ACTIVE = "active"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    PENDING = "pending"


# ---------------------------------------------------------------------------
# Database table names
# ---------------------------------------------------------------------------

class TableName:
    """Canonical table-name strings.

    Use these instead of bare literals so that a table rename only requires
    one change here rather than a codebase-wide search-and-replace.
    """
    JOB_LISTINGS = "job_listings"
    JOB_APPLICATIONS = "job_applications"
    JOB_DETAILS = "job_details"
    JOB_OFFERS = "job_offers"
    FILTERED_JOBS = "filtered_jobs"
    IGNORED_JOBS = "ignored_jobs"
    SAVED_SEARCHES = "saved_searches"
