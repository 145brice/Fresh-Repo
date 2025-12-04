"""
Atlanta GA Permit Scraper using Selenium - GIS Portal Version
Scrapes from Atlanta GIS Building Permit Tracker
"""
from datetime import datetime, timedelta
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
from .selenium_base import SeleniumScraperBase

class AtlantaGISSeleniumScraper(SeleniumScraperBase):
    def __init__(self):
        super().__init__(
            city_name='Atlanta',
            url='https://gis.atlantaga.gov/buildingpermittracker/?page=Search-All-Permits'
        )

    def scrape_permits(self, max_permits=5000, days_back=90):
        """Scrape Atlanta permits from GIS portal using Selenium"""
        self.logger.info("🏗️  Atlanta GA Construction Permits Scraper (GIS Portal)")
        print(f"🏗️  Atlanta GA Construction Permits Scraper (GIS Portal - Selenium)")
        print(f"=" * 60)
        print(f"📅 Date Range: {(datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}")
        print(f"🌐 Using Selenium to scrape GIS permit tracker...")

        if not self._init_driver():
            self.logger.error("Failed to initialize driver")
            return []

        try:
            # Navigate to the search page
            self.logger.info(f"Loading {self.url}")
            print(f"\n🔍 Loading Atlanta GIS permit tracker...")
            self.driver.get(self.url)
            time.sleep(5)  # Wait for page and data to load

            print(f"📊 Extracting permit data...")

            # GIS portals often use dynamic tables - try common selectors
            table_selectors = [
                ('css', 'table#permits'),
                ('css', 'table.table'),
                ('css', 'table[role="grid"]'),
                ('css', 'div.ag-root table'),  # AG Grid
                ('css', 'table.display'),  # DataTables
                ('xpath', '//table[contains(@class, "data") or contains(@class, "grid")]'),
            ]

            # Wait for table to load
            table = None
            for selector_type, selector in table_selectors:
                try:
                    if selector_type == 'css':
                        table = WebDriverWait(self.driver, 15).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                    elif selector_type == 'xpath':
                        table = WebDriverWait(self.driver, 15).until(
                            EC.presence_of_element_located((By.XPATH, selector))
                        )

                    if table:
                        self.logger.info(f"Found table with {selector_type}: {selector}")
                        print(f"✓ Found permits table")
                        break
                except (TimeoutException, NoSuchElementException):
                    continue

            if not table:
                self.logger.warning("No permit table found, trying to find any data rows")

                # Fallback: look for any table rows with data
                all_rows_selectors = [
                    ('css', 'tr[data-id]'),  # Rows with data-id attribute
                    ('css', 'tbody tr'),  # Standard table body rows
                    ('css', 'div[role="row"]'),  # AG Grid rows
                ]

                rows = []
                for selector_type, selector in all_rows_selectors:
                    try:
                        if selector_type == 'css':
                            rows = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if rows and len(rows) > 0:
                            self.logger.info(f"Found {len(rows)} rows with {selector_type}: {selector}")
                            break
                    except:
                        continue

                if not rows:
                    print(f"❌ Could not find permit data on page")
                    return []

                # Extract from rows directly
                print(f"✓ Found {len(rows)} potential permit rows")

                for row in rows[:max_permits]:
                    try:
                        # Try to extract text from cells
                        cells = row.find_elements(By.TAG_NAME, 'td')
                        if not cells:
                            cells = row.find_elements(By.CSS_SELECTOR, 'div[role="gridcell"]')  # AG Grid

                        if len(cells) >= 3:
                            # Extract whatever data we can find
                            permit_id = self._safe_get_text(cells[0])

                            # Basic validation
                            if permit_id and len(permit_id) >= 3 and permit_id not in self.seen_permit_ids:
                                self.seen_permit_ids.add(permit_id)
                                self.permits.append({
                                    'permit_number': permit_id,
                                    'address': self._safe_get_text(cells[1]) if len(cells) > 1 else 'N/A',
                                    'type': self._safe_get_text(cells[2]) if len(cells) > 2 else 'N/A',
                                    'value': self._safe_get_text(cells[3]) if len(cells) > 3 else '$0.00',
                                    'issued_date': self._safe_get_text(cells[4]) if len(cells) > 4 else 'N/A',
                                    'status': self._safe_get_text(cells[5]) if len(cells) > 5 else 'N/A'
                                })

                                if len(self.permits) % 10 == 0:
                                    print(f"✓ Extracted {len(self.permits)} permits so far...")

                    except Exception as e:
                        self.logger.warning(f"Error processing row: {e}")
                        continue

            else:
                # Extract from table
                tbody = table.find_element(By.TAG_NAME, 'tbody')
                rows = tbody.find_elements(By.TAG_NAME, 'tr')

                self.logger.info(f"Found {len(rows)} rows in table")
                print(f"✓ Found {len(rows)} permit records")

                for row in rows[:max_permits]:
                    try:
                        cells = row.find_elements(By.TAG_NAME, 'td')

                        if len(cells) >= 2:
                            permit_id = self._safe_get_text(cells[0])

                            # Basic validation and deduplication
                            if permit_id and len(permit_id) >= 3 and permit_id not in self.seen_permit_ids:
                                self.seen_permit_ids.add(permit_id)
                                self.permits.append({
                                    'permit_number': permit_id,
                                    'address': self._safe_get_text(cells[1]) if len(cells) > 1 else 'N/A',
                                    'type': self._safe_get_text(cells[2]) if len(cells) > 2 else 'N/A',
                                    'value': self._safe_get_text(cells[3]) if len(cells) > 3 else '$0.00',
                                    'issued_date': self._safe_get_text(cells[4]) if len(cells) > 4 else 'N/A',
                                    'status': self._safe_get_text(cells[5]) if len(cells) > 5 else 'N/A'
                                })

                                if len(self.permits) % 100 == 0:
                                    print(f"✓ Extracted {len(self.permits)} permits so far...")

                    except Exception as e:
                        self.logger.warning(f"Error processing row: {e}")
                        continue

            print(f"\n✅ Scraping complete! Total permits: {len(self.permits)}")

            if len(self.permits) > 0:
                self.health_check.record_success(len(self.permits))
            else:
                self.health_check.record_failure("No permits extracted")

            return self.permits

        except Exception as e:
            self.logger.error(f"Fatal error in scraper: {e}", exc_info=True)
            self.health_check.record_failure(str(e))
            print(f"❌ Fatal error: {e}")
            return []

        finally:
            self._close_driver()

def scrape_permits():
    return AtlantaGISSeleniumScraper().scrape_permits()

def save_to_csv(permits):
    scraper = AtlantaGISSeleniumScraper()
    scraper.permits = permits
    scraper.save_to_csv()
