"""Cleveland, OH - Accela Portal Scraper"""
from .accela_base import AccelaScraperBase

class ClevelandPermitScraper(AccelaScraperBase):
    def __init__(self):
        super().__init__(city_name='Cleveland', accela_domain='COC')

def scrape_permits():
    return ClevelandPermitScraper().scrape_permits()

def save_to_csv(permits):
    scraper = ClevelandPermitScraper()
    scraper.permits = permits
    scraper.save_to_csv()
