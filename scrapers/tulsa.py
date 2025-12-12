from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import csv
import os
from datetime import datetime
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from base_scraper import BaseScraper

class TulsaScraper(BaseScraper):
    def __init__(self):
        super().__init__('tulsa')
        self.base_url = "https://www.cityoftulsa.org/government/departments/development-services/permitting/"
        self.permits = []
        
        # Set up Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in background
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # Initialize WebDriver
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)

    def get_permits(self, max_permits=100):
        """Scrape Tulsa, OK building permits using Selenium"""
        self.logger.info("🏗️  Tulsa OK Construction Permits Scraper (Selenium)")
        print("🏗️  Tulsa OK Construction Permits Scraper (Selenium)")
        print("=" * 60)

        try:
            # Navigate to the page
            self.driver.get(self.base_url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Try to find permit table
            table_selectors = ['table.permit-table', 'table', 'table.resultsTable']
            table = None
            
            for selector in table_selectors:
                try:
                    table = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    break
                except TimeoutException:
                    continue
            
            if not table:
                self.logger.warning("No permit table found on Tulsa website")
                print("No permit table found on Tulsa website")
                return self.permits
            
            # Get table rows
            rows = table.find_elements(By.TAG_NAME, "tr")
            
            if len(rows) <= 1:
                self.logger.warning("No data rows found in Tulsa permit table")
                print("No data rows found in Tulsa permit table")
                return self.permits
            
            # Parse permit data
            for row in rows[1:max_permits+1]:  # Skip header, limit to max_permits
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) >= 4:
                    try:
                        permit_number = cols[0].text.strip()
                        address = cols[1].text.strip()
                        permit_type = cols[2].text.strip() if len(cols) > 2 else 'N/A'
                        description = f"Status: {cols[3].text.strip() if len(cols) > 3 else 'N/A'}"
                        
                        if permit_number and permit_number not in [p['permit_number'] for p in self.permits]:
                            self.permits.append({
                                'permit_number': permit_number,
                                'address': address,
                                'permit_type': permit_type,
                                'description': description,
                                'date': datetime.now().strftime('%Y-%m-%d'),  # No date available
                                'city': 'Tulsa'
                            })
                            
                    except Exception as e:
                        self.logger.warning(f"Error parsing Tulsa permit row: {e}")
                        continue
            
            self.logger.info(f"Successfully scraped {len(self.permits)} permits from Tulsa")
            print(f"Successfully scraped {len(self.permits)} permits from Tulsa")
            
        except Exception as e:
            self.logger.error(f"Error scraping Tulsa permits: {e}")
            print(f"Error scraping Tulsa permits: {e}")
        
        finally:
            # Clean up
            if self.driver:
                self.driver.quit()
        
        return self.permits

    def run(self):
        try:
            permits = self.get_permits()
            if permits:
                filepath = self.save_to_csv(permits)
                return permits, filepath
            return [], None
        except Exception as e:
            self.logger.error(f"Fatal error: {e}")
            return [], None

if __name__ == "__main__":
    scraper = TulsaScraper()
    permits, filepath = scraper.run()
    print(f"Scraped {len(permits)} permits, saved to {filepath}")