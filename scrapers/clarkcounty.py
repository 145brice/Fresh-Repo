"""Clark County, NV - Accela Portal Scraper"""
from .accela_base import AccelaScraperBase

class ClarkCountyPermitScraper(AccelaScraperBase):
    def __init__(self):
        super().__init__(city_name='Clark County', accela_domain='CLARKCO')

def scrape_permits():
    return ClarkCountyPermitScraper().scrape_permits()

def save_to_csv(permits):
    scraper = ClarkCountyPermitScraper()
    scraper.permits = permits
    scraper.save_to_csv()
