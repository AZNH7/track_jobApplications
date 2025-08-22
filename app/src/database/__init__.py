"""
Database package for job tracker application.

This package contains table definitions and database management utilities.
"""

from .base_table import BaseTable
from .job_listings_table import JobListingsTable
from .job_applications_table import JobApplicationsTable
from .job_details_table import JobDetailsTable
from .ignored_jobs_table import IgnoredJobsTable
from .filtered_jobs_table import FilteredJobsTable
from .job_offers_table import JobOffersTable
from .saved_searches_table import SavedSearchesTable
from .database_manager import DatabaseManager

__all__ = [
    'BaseTable',
    'JobListingsTable',
    'JobApplicationsTable', 
    'JobDetailsTable',
    'IgnoredJobsTable',
    'FilteredJobsTable',
    'JobOffersTable',
    'SavedSearchesTable',
    'DatabaseManager'
]
