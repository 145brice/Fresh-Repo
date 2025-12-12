"""
Base Selenium Scraper with Auto-Fix Capabilities
Handles cities without public APIs by scraping their web portals
"""
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
import time
import csv
import os
from .utils import setup_logger, ScraperHealthCheck

class SeleniumScraperBase:
    """
    Base class for Selenium-based web scrapers with auto-recovery
    """

    def __init__(self, city_name, url, logger_name=None):
        self.city_name = city_name
        self.url = url
        self.permits = []
        self.seen_permit_ids = set()
        self.logger = setup_logger(logger_name or city_name.lower().replace(' ', ''))
        self.health_check = ScraperHealthCheck(city_name.lower().replace(' ', ''))
        self.driver = None

        # Selectors to try for common permit data (auto-fix attempts)
        self.selector_attempts = {
            'permit_number': [
                ('css', 'td.permit-number'),
                ('css', '.permitNumber'),
                ('css', '[data-field="permit"]'),
                ('xpath', '//td[contains(@class, "permit")]'),
                ('xpath', '//div[contains(text(), "Permit")]//following-sibling::*'),
            ],
            'address': [
                ('css', 'td.address'),
                ('css', '.permitAddress'),
                ('css', '[data-field="address"]'),
                ('xpath', '//td[contains(@class, "address")]'),
                ('xpath', '//div[contains(text(), "Address")]//following-sibling::*'),
            ],
            'date': [
                ('css', 'td.date'),
                ('css', '.permitDate'),
                ('css', '[data-field="date"]'),
                ('xpath', '//td[contains(@class, "date")]'),
                ('xpath', '//div[contains(text(), "Date")]//following-sibling::*'),
            ]
        }

    def _init_driver(self):
        """Initialize headless Chrome driver with proper options"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')

            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(30)
            self.logger.info("Chrome driver initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize Chrome driver: {e}")
            return False

    def _close_driver(self):
        """Safely close the driver"""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("Chrome driver closed")
            except Exception as e:
                self.logger.warning(f"Error closing driver: {e}")

    def _try_find_element(self, selector_list, timeout=5):
        """
        Try multiple selectors to find an element (auto-fix capability)
        Returns element if found, None otherwise
        """
        for selector_type, selector in selector_list:
            try:
                if selector_type == 'css':
                    element = WebDriverWait(self.driver, timeout).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                elif selector_type == 'xpath':
                    element = WebDriverWait(self.driver, timeout).until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                else:
                    continue

                self.logger.info(f"Found element with {selector_type}: {selector}")
                return element

            except (TimeoutException, NoSuchElementException):
                continue

        return None

    def _try_find_elements(self, selector_list, timeout=5):
        """
        Try multiple selectors to find elements (auto-fix capability)
        Returns list of elements if found, empty list otherwise
        """
        for selector_type, selector in selector_list:
            try:
                if selector_type == 'css':
                    elements = WebDriverWait(self.driver, timeout).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
                    )
                elif selector_type == 'xpath':
                    elements = WebDriverWait(self.driver, timeout).until(
                        EC.presence_of_all_elements_located((By.XPATH, selector))
                    )
                else:
                    continue

                if elements:
                    self.logger.info(f"Found {len(elements)} elements with {selector_type}: {selector}")
                    return elements

            except (TimeoutException, NoSuchElementException):
                continue

        return []

    def _safe_get_text(self, element):
        """Safely extract text from element"""
        try:
            return element.text.strip() if element else 'N/A'
        except:
            return 'N/A'

    def scrape_permits(self, max_permits=5000, days_back=90):
        """
        Base scrape method - should be overridden by subclasses
        """
        raise NotImplementedError("Subclass must implement scrape_permits method")

    def save_to_csv(self, filename=None):
        """Save permits to CSV file"""
        if not self.permits:
            self.logger.warning("No permits to save")
            return

        if filename is None:
            today = datetime.now().strftime('%Y-%m-%d')
            city_slug = self.city_name.lower().replace(' ', '')
            filename = f'leads/{city_slug}/{today}/{today}_{city_slug}.csv'

        os.makedirs(os.path.dirname(filename), exist_ok=True)

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            if self.permits:
                writer = csv.DictWriter(f, fieldnames=list(self.permits[0].keys()))
                writer.writeheader()
                writer.writerows(self.permits)

        self.logger.info(f"Saved {len(self.permits)} permits to {filename}")
        print(f"✅ Saved {len(self.permits)} permits to {filename}")

    def run(self):
        """Main execution with error handling and auto-recovery"""
        try:
            permits = self.scrape_permits()
            if permits:
                self.save_to_csv()
                self.health_check.record_success(len(permits))
                return permits
            else:
                self.logger.warning(f"No permits scraped for {self.city_name}")
                self.health_check.record_failure("No permits found")
                return []
        except Exception as e:
            self.logger.error(f"Fatal error in scraper: {e}", exc_info=True)
            self.health_check.record_failure(str(e))
            return []
        finally:
            self._close_driver()
