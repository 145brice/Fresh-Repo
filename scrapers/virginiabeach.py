"""Virginia Beach, VA - Accela Portal Scraper"""
from .accela_base import AccelaScraperBase

class VirginiaBeachPermitScraper(AccelaScraperBase):
    def __init__(self):
        super().__init__(city_name='Virginia Beach', accela_domain='CVB')

def scrape_permits():
    return VirginiaBeachPermitScraper().scrape_permits()

def save_to_csv(permits):
    scraper = VirginiaBeachPermitScraper()
    scraper.permits = permits
    scraper.save_to_csv()
