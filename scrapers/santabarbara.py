"""Santa Barbara, CA - Accela Portal Scraper"""
from .accela_base import AccelaScraperBase

class SantaBarbaraPermitScraper(AccelaScraperBase):
    def __init__(self):
        super().__init__(city_name='Santa Barbara', accela_domain='SANTABARBARA')

def scrape_permits():
    return SantaBarbaraPermitScraper().scrape_permits()

def save_to_csv(permits):
    scraper = SantaBarbaraPermitScraper()
    scraper.permits = permits
    scraper.save_to_csv()
