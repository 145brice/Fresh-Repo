"""
Scrapers package for contractor leads SaaS

All scrapers now include:
- Auto-recovery with retry logic
- Comprehensive logging
- Health monitoring
- Partial results saving
- Exponential backoff on failures
"""

from .nashville import NashvillePermitScraper
from .austin import AustinPermitScraper
from .houston import HoustonPermitScraper
from .sanantonio import SanAntonioPermitScraper
from .charlotte import CharlottePermitScraper
from .chattanooga import ChattanoogaPermitScraper
from .phoenix import PhoenixPermitScraper

__all__ = [
    'NashvillePermitScraper',
    'AustinPermitScraper',
    'HoustonPermitScraper',
    'SanAntonioPermitScraper',
    'CharlottePermitScraper',
    'ChattanoogaPermitScraper',
    'PhoenixPermitScraper',
]
