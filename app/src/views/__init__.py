"""Views package for Job Tracker"""

from .base_view import BaseView
from .main_dashboard import MainDashboardView
from .applications import ApplicationsView
from .data_management import DataManagementView
from .job_browser import JobBrowserView
from .platform_config import PlatformConfigView
# Email features removed
from .job_offers import JobOffersView

from .enhanced_job_search import EnhancedJobSearchView
# Enhanced email analyzer removed

__all__ = [
    'BaseView',
    'MainDashboardView',
    'ApplicationsView',
    'DataManagementView',
    'JobBrowserView',
    'PlatformConfigView',
    'JobOffersView',

    'EnhancedJobSearchView'
] 