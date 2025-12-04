"""
Scrapers package for contractor leads SaaS

All scrapers now include:
- Auto-recovery with retry logic
- Comprehensive logging
- Health monitoring
- Partial results saving
- Exponential backoff on failures
"""

# Original 7 cities
from .nashville import NashvillePermitScraper
from .austin import AustinPermitScraper
from .houston import HoustonPermitScraper
from .sanantonio import SanAntonioPermitScraper
from .charlotte import CharlottePermitScraper
from .chattanooga import ChattanoogaPermitScraper
from .phoenix import PhoenixPermitScraper

# New 13 cities
from .atlanta import AtlantaPermitScraper
from .seattle import SeattlePermitScraper
from .sandiego import SanDiegoPermitScraper
from .indianapolis import IndianapolisPermitScraper
from .columbus import ColumbusPermitScraper
from .chicago import ChicagoPermitScraper
from .boston import BostonPermitScraper
from .philadelphia import PhiladelphiaPermitScraper
from .richmond import RichmondPermitScraper
from .milwaukee import MilwaukeePermitScraper
from .omaha import OmahaPermitScraper
from .knoxville import KnoxvillePermitScraper
from .birmingham import BirminghamPermitScraper

# New HTML table scrapers
from .snohomish import SnohomishPermitScraper
from .maricopa import MaricopaPermitScraper
from .mecklenburg import MecklenburgPermitScraper

# Additional Accela-based scrapers
from .clarkcounty import ClarkCountyPermitScraper
from .cleveland import ClevelandPermitScraper
from .fortcollins import FortCollinsPermitScraper
from .santabarbara import SantaBarbaraPermitScraper
from .virginiabeach import VirginiaBeachPermitScraper

# New HTML table scrapers (additional)
from .tulsa import TulsaPermitScraper
from .coloradosprings import ColoradoSpringsPermitScraper
from .raleigh import RaleighPermitScraper
from .oklahomacity import OklahomaCityPermitScraper
from .albuquerque import AlbuquerquePermitScraper

__all__ = [
    'NashvillePermitScraper',
    'AustinPermitScraper',
    'HoustonPermitScraper',
    'SanAntonioPermitScraper',
    'CharlottePermitScraper',
    'ChattanoogaPermitScraper',
    'PhoenixPermitScraper',
    'AtlantaPermitScraper',
    'SeattlePermitScraper',
    'SanDiegoPermitScraper',
    'IndianapolisPermitScraper',
    'ColumbusPermitScraper',
    'ChicagoPermitScraper',
    'BostonPermitScraper',
    'PhiladelphiaPermitScraper',
    'RichmondPermitScraper',
    'MilwaukeePermitScraper',
    'OmahaPermitScraper',
    'KnoxvillePermitScraper',
    'BirminghamPermitScraper',
    'SnohomishPermitScraper',
    'MaricopaPermitScraper',
    'MecklenburgPermitScraper',
    'ClarkCountyPermitScraper',
    'ClevelandPermitScraper',
    'FortCollinsPermitScraper',
    'SantaBarbaraPermitScraper',
    'VirginiaBeachPermitScraper',
    'TulsaPermitScraper',
    'ColoradoSpringsPermitScraper',
    'RaleighPermitScraper',
    'OklahomaCityPermitScraper',
    'AlbuquerquePermitScraper',
]
