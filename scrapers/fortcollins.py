"""Fort Collins, CO - Accela Portal Scraper"""
from .accela_base import AccelaScraperBase

class FortCollinsPermitScraper(AccelaScraperBase):
    def __init__(self):
        super().__init__(city_name='Fort Collins', accela_domain='FCGOV')

def scrape_permits():
    return FortCollinsPermitScraper().scrape_permits()

def save_to_csv(permits):
    scraper = FortCollinsPermitScraper()
    scraper.permits = permits
    scraper.save_to_csv()
