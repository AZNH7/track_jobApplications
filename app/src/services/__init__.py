"""
Services package for job tracking functionality
"""

from .job_grouping_service import JobGroupingService, JobGroup
# Email services removed

__all__ = [
    'JobGroupingService',
    'JobGroup'
] 