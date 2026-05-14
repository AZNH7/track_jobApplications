# Codebase Guide for Claude

Last audited: 2026-05-14 | Last updated: 2026-05-14 (all 19 issues fixed; only #7 deferred)

## Project Summary

**Track Job Applications** — Streamlit web app that scrapes German job sites, stores results in PostgreSQL, and uses a local Ollama LLM to analyze/rank jobs.

- **Entry point:** `app/src/app.py` → radio navigation → 8 views
- **Config:** `app/job_tracker_config.json` (singleton via `config_manager.py`)
- **Infra:** Docker Compose — 13 services (app + postgres + redis + 5× FlareSolverr + nginx balancer)
- **Ollama model:** `gpt-oss:latest` (configured in `job_tracker_config.json` → `llm.model`)

---

## Architecture Map

```
app/src/
├── app.py                          # Streamlit entry point
├── config_manager.py               # Singleton config loader (job_tracker_config.json)
├── ollama_client.py                # Ollama HTTP client, cross-platform host resolution
├── ollama_job_analyzer.py          # LLM job analysis & tagging
├── enhanced_job_processor.py       # Batch LLM processing (ThreadPoolExecutor x4)
│
├── core/
│   ├── base_tracker.py             # Orchestrator: wires DB + config + Ollama + scraper
│   └── session_state.py            # Streamlit session_state initialization
│
├── database/
│   ├── database_manager.py         # Connection pool (psycopg2, 1–10 conns), table init
│   ├── base_table.py               # Abstract base for all table managers
│   ├── job_listings_table.py       # Main jobs table (upsert on URL conflict)
│   ├── job_applications_table.py
│   ├── job_details_table.py
│   ├── job_offers_table.py
│   ├── ignored_jobs_table.py
│   ├── filtered_jobs_table.py
│   └── saved_searches_table.py
│
├── scrapers/
│   ├── job_scraper_orchestrator.py # Coordinates all 7 scrapers
│   ├── base_scraper.py             # Session mgmt, 403 tracking, 30-min refresh
│   ├── rate_limit_manager.py       # Per-domain delays (LinkedIn 5s, default 1.5s)
│   ├── browser_automation.py       # Selenium / Pyppeteer
│   ├── indeed_scraper.py
│   ├── linkedin_scraper.py
│   ├── stepstone_scraper.py
│   ├── xing_scraper.py
│   ├── stellenanzeigen_scraper.py
│   ├── meinestadt_scraper.py
│   ├── jobrapido_scraper.py
│   └── utils.py
│
├── views/
│   ├── base_view.py                # Abstract base: cache TTL (300s), session helpers
│   ├── main_dashboard.py
│   ├── enhanced_job_search.py
│   ├── job_browser.py
│   ├── job_offers.py
│   ├── applications.py
│   ├── data_management.py
│   ├── platform_config.py
│   └── settings_view.py
│
├── services/
│   ├── job_grouping_service.py     # LLM-based grouping (fallback: rule-based)
│   ├── job_details_cache.py        # Redis-backed details cache
│   └── saved_search_service.py
│
├── utils/
│   ├── data_loader.py              # DB → Pandas DataFrame
│   ├── ui_components.py            # Custom CSS, headers, spinners
│   ├── thread_manager.py
│   └── platform_utils.py
│
└── components/
    ├── quick_insights_widget.py
    ├── enhanced_insights.py
    └── persistent_search_results.py
```

---

## Known Issues (by priority)

### Critical — silent failures / crashes

| # | Issue | Location |
|---|-------|----------|
| 1 | ~~**Bare `except:` clauses**~~ **FIXED 2026-05-14** — replaced with typed exceptions: `json.JSONDecodeError`/`ValueError` for JSON parsing, `AttributeError`/`TypeError` for DOM traversal, `ValueError`/`TypeError` for date parsing, `Exception` in `finally` cleanup blocks | `ollama_job_analyzer.py`, `stepstone_scraper.py`, `job_scraper_orchestrator.py`, `job_details_cache.py`, `data_management.py`, `applications.py`, `job_browser.py` |
| 2 | ~~**DB schema defined twice**~~ **FIXED 2026-05-14** — removed all table DDL from `01-init.sql` (was creating stale stubs that blocked `IF NOT EXISTS` in ORM); Python ORM is now single source of truth. Also added `UNIQUE(job_listing_id)` to `filtered_jobs` (required by existing `ON CONFLICT` clause that was silently broken) | `01-init.sql`, `filtered_jobs_table.py` |
| 3 | ~~**No connection timeout**~~ **FIXED 2026-05-14** — switched from `SimpleConnectionPool` (not thread-safe) to `ThreadedConnectionPool`; added `connect_timeout=10` and `statement_timeout=30000ms` to DSN; removed unused `timeout` parameter; `get_connection()` now rolls back on exception and catches `PoolError` explicitly | `database_manager.py` |
| 4 | ~~**LLM timeout inconsistency**~~ **FIXED 2026-05-14** — `ollama_client.py` default was `120`, now `300` (matches config); stale default model `llama3:8b`/`llama3.2:latest` corrected to `gpt-oss:latest` in both `ollama_client.py` and `base_tracker.py` | `ollama_client.py`, `base_tracker.py` |
| 5 | ~~**No retry/fallback when all scrapers fail**~~ **FIXED 2026-05-14** — `search_all_platforms` and `search_parallel` now track `failed_platforms` separately; when all platforms error the message clearly states "All N platforms failed" vs "no jobs found" vs "N platforms errored" | `job_scraper_orchestrator.py` |

### High — reliability / security

| # | Issue | Location |
|---|-------|----------|
| 6 | ~~**No input sanitization**~~ **FIXED 2026-05-14** — keywords stripped of control chars and capped at 200 chars; location similarly sanitised; selected platforms validated against known list before being passed to scrapers | `enhanced_job_search.py` |
| 7 | Ollama host resolution is ~60 lines of fragile multi-strategy fallback; hard to debug | `ollama_client.py` |
| 8 | ~~**`print()` instead of logging**~~ **FIXED 2026-05-14** — 517 `print()` calls converted across all 13 scraper files + `enhanced_job_search.py`; `self.logger = logging.getLogger(__name__)` added to `BaseScraper`, `JobScraperOrchestrator`, `RateLimitManager`; module-level `_logger` for `JobFilters` (static methods); `❌`→error, `⚠️`→warning, everything else→info. Log level now controlled by `LOG_LEVEL` env var | All scraper files |
| 9 | ~~**LinkedIn credential exposure risk**~~ **FIXED 2026-05-14** — `.env` is already excluded from git via `.gitignore`; strengthened security warning in `env.template` to make the git boundary explicit; fixed stale `OLLAMA_TIMEOUT=120` → `300` in template | `app/env.template` |

### Medium — maintainability

| # | Issue | Location |
|---|-------|----------|
| 10 | ~~**No cross-platform dedup**~~ **FIXED 2026-05-14** — added `content_hash TEXT` column (MD5 of `lower(title)\|lower(company)`); `insert_job` checks hash before insert and returns existing ID on match; partial-unique index (`WHERE content_hash IS NOT NULL`) prevents false dedup of jobs with missing data; `ALTER TABLE … ADD COLUMN IF NOT EXISTS` migrates existing DBs | `job_listings_table.py` |
| 11 | ~~**Session state memory leak**~~ **FIXED 2026-05-14** — added `trim_session_state()` to `SessionStateManager`; caps `search_log` and `email_log_messages` at 100 entries, `platform_test_results` at 50 entries (evicts oldest); called on every render from `app.py` | `core/session_state.py`, `app.py` |
| 12 | ~~**No search checkpoint**~~ **FIXED 2026-05-14** — added `_save_jobs_checkpoint()` to orchestrator; called inside the `as_completed` loop in `search_optimized` so each platform's results are persisted to DB immediately on completion; `search_optimized` now also tracks and reports `failed_platforms` | `job_scraper_orchestrator.py` |
| 13 | ~~**FlareSolverr balancer not sticky**~~ **FIXED 2026-05-14** — added `ip_hash` directive to nginx upstream block; each client IP now consistently routes to the same FlareSolverr instance, preserving Cloudflare challenge cookies across requests | `app/nginx-flaresolverr.conf` |
| 14 | ~~**Config baked into Docker image**~~ **FIXED 2026-05-14** — added `./job_tracker_config.json:/app/job_tracker_config.json` volume mount in `docker-compose.yml`; file is read-write so the Settings view can persist changes; the baked-in copy acts as a fallback if the mount is absent | `app/docker-compose.yml` |

### Low / code quality

| # | Issue | Notes |
|---|-------|-------|
| 15 | ~~**No test files anywhere in the repo**~~ **FIXED 2026-05-14** — created `tests/__init__.py` and `tests/test_core.py` with 33 unit tests across 4 classes: `TestContentHash` (11 tests for `_compute_content_hash`), `TestTrimSessionState` (7 tests), `TestInputSanitization` (9 tests for sanitisation regex), `TestConstants` (6 smoke tests for `constants.py`). All tests stub heavy deps (streamlit, psycopg2, pandas, etc.) so they run without Docker. | `tests/` |
| 16 | ~~**Inconsistent import styles**~~ **FIXED 2026-05-14** — removed redundant `sys.path` manipulations from `ollama_job_analyzer.py`, `job_details_cache.py`, `job_grouping_service.py`; all three were inserting `/app/src` which is already set by `PYTHONPATH` in the Dockerfile and `docker-compose.yml` | `ollama_job_analyzer.py`, `job_details_cache.py`, `job_grouping_service.py` |
| 17 | ~~**Magic numbers scattered throughout**~~ **FIXED 2026-05-14** — created `app/src/constants.py` with all numeric constants (`SESSION_403_WINDOW_SECS=300`, `SESSION_MAX_AGE_SECS=1800`, `DB_POOL_MAX_CONNS=10`, `LLM_BATCH_WORKERS=4`, `OLLAMA_DEFAULT_TIMEOUT_SECS=300`, etc.); wired into `base_scraper.py`, `database_manager.py`, `enhanced_job_processor.py`, `session_state.py` | `constants.py` (new), 4 consumers |
| 18 | ~~**No type hints on function signatures**~~ **FIXED 2026-05-14** — added `-> None` return type to all void methods in `base_table.py` (`__init__`, `log_error`, `log_info`) and `session_state.py` (all 4 static methods); fixed `limit: int = None` → `limit: Optional[int] = None` in `job_listings_table.py` | `base_table.py`, `session_state.py`, `job_listings_table.py` |
| 19 | ~~**Hardcoded status strings / table names**~~ **FIXED 2026-05-14** — `constants.py` adds `ApplicationStatus` enum-like class (`SAVED`, `APPLIED`, `INTERVIEW`, `OFFERED`, `REJECTED`, `WITHDRAWN`), `JobOfferStatus` class, and `TableName` class with all 7 table name strings | `constants.py` (new) |

---

## Key Behaviors & Gotchas

- **Ollama host resolution order:** `host.docker.internal` (Windows Docker) → `localhost:11434` → IP fallback. Set `OLLAMA_HOST` env var to override.
- **FlareSolverr** is used only by specific scrapers (configured per-platform in `job_tracker_config.json` → `flaresolverr`). 5 instances load-balanced via Nginx.
- **Upsert strategy:** `job_listings_table.py` uses `ON CONFLICT (url) DO UPDATE` — URL is the deduplication key within a single platform.
- **Rate limits:** LinkedIn 5.0s, JobRapido 2.0s, default 1.5s. Adaptive backoff on 429 responses (`rate_limit_manager.py`).
- **Session refresh:** `base_scraper.py` refreshes sessions after 30 min or after consecutive 403s.
- **Batch LLM processing:** `enhanced_job_processor.py` uses `ThreadPoolExecutor(max_workers=4)` — not async.
- **Cache TTL:** View-level cache is 300s (`base_view.py`). Redis used for job details cache.

---

## Quick Debug Checklist

1. **App won't start** → check `docker-compose logs job-tracker`; verify `.env` exists with correct DB credentials
2. **Scrapers returning nothing** → check FlareSolverr health (`docker-compose ps`); check `rate_limit_manager.py` delays
3. **Ollama not responding** → verify model is pulled (`ollama list`); check `OLLAMA_HOST` env var; review `ollama_client.py` host resolution logic
4. **DB errors** → check pool exhaustion; look for unclosed connections in `database_manager.py`
5. **LLM timeouts** → confirm config `llm.ollama_timeout` matches actual usage in `ollama_job_analyzer.py`
