"""
Job Scrapers Package

This package contains modular job scrapers for different platforms and utilities.
"""

from .base_scraper import BaseScraper
from .indeed_scraper import IndeedScraper
from .linkedin_scraper import LinkedInScraper
from .stepstone_scraper import StepStoneScraper

from .xing_scraper import XingScraper
from .stellenanzeigen_scraper import StellenanzeigenScraper
from .meinestadt_scraper import MeinestadtScraper
from .jobrapido_scraper import JobrapidoScraper
from .job_scraper_orchestrator import JobScraperOrchestrator
from .browser_automation import BrowserAutomation

__all__ = [
    'BaseScraper',
    'IndeedScraper', 
    'LinkedInScraper',

    'StepStoneScraper',
    'XingScraper',
    'StellenanzeigenScraper',
    'MeinestadtScraper',
    'JobrapidoScraper',
    'JobScraperOrchestrator',
    'BrowserAutomation'
] 