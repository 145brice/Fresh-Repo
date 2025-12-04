"""
Generic Accela Citizen Access Scraper
Works for any city using Accela portal
"""
from datetime import datetime, timedelta
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
from .selenium_base import SeleniumScraperBase

class AccelaScraperBase(SeleniumScraperBase):
    """
    Base scraper for Accela Citizen Access portals
    All Accela cities use same portal structure
    """

    def __init__(self, city_name, accela_domain):
        """
        city_name: "Houston", "Cleveland", etc.
        accela_domain: "HOUSTON", "CLEVELAND", etc. (from Accela URL)
        """
        url = f'https://aca-prod.accela.com/{accela_domain}/Default.aspx'
        super().__init__(city_name=city_name, url=url)
        self.accela_domain = accela_domain

    def scrape_permits(self, max_permits=5000, days_back=90):
        """Scrape permits from Accela portal"""
        self.logger.info(f"🏗️  {self.city_name} Construction Permits Scraper (Accela)")
        print(f"🏗️  {self.city_name} Construction Permits Scraper (Accela)")
        print(f"=" * 60)
        print(f"📅 Date Range: {(datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}")
        print(f"🌐 Scraping Accela portal...")

        if not self._init_driver():
            self.logger.error("Failed to initialize driver")
            return []

        try:
            # Load Accela portal
            self.logger.info(f"Loading {self.url}")
            print(f"\n🔍 Loading Accela portal...")
            self.driver.get(self.url)
            time.sleep(3)

            # Navigate to building permits search
            # Try to find and click building/permits link
            building_links = [
                ('xpath', '//a[contains(text(), "Building")]'),
                ('xpath', '//a[contains(text(), "Permits")]'),
                ('css', 'a[href*="Building"]'),
                ('css', 'a[href*="Permit"]'),
            ]

            for selector_type, selector in building_links:
                try:
                    if selector_type == 'xpath':
                        link = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                    else:
                        link = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )

                    link.click()
                    time.sleep(2)
                    print(f"✓ Navigated to permits section")
                    break
                except:
                    continue

            # Try direct search URL (common Accela pattern)
            search_url = f'https://aca-prod.accela.com/{self.accela_domain}/Cap/CapHome.aspx?module=Building'
            self.driver.get(search_url)
            time.sleep(3)
            print(f"✓ Loaded permit search page")

            # Fill date range if available
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)

            # Try to find search button and click
            search_selectors = [
                ('css', 'input[value="Search"]'),
                ('css', 'input[type="submit"][value*="Search"]'),
                ('id', 'ctl00_PlaceHolderMain_btnNewSearch'),
            ]

            for selector_type, selector in search_selectors:
                try:
                    if selector_type == 'css':
                        btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                    else:
                        btn = self.driver.find_element(By.ID, selector)

                    btn.click()
                    time.sleep(4)
                    print(f"✓ Submitted search")
                    break
                except:
                    continue

            # Extract permits from results table
            # Accela uses consistent table classes across all cities
            permit_links = self.driver.find_elements(By.CSS_SELECTOR, 'table.ACA_GridView a[href*="Detail"]')

            if not permit_links:
                # Try alternate selector
                permit_links = self.driver.find_elements(By.CSS_SELECTOR, 'table[id*="GridView"] a')

            if permit_links:
                print(f"✓ Found {len(permit_links)} permit records")

                for link in permit_links[:max_permits]:
                    try:
                        permit_number = link.text.strip()

                        # Validate permit number
                        if not permit_number or len(permit_number) < 5:
                            continue

                        if permit_number in self.seen_permit_ids:
                            continue

                        # Get parent row for additional data
                        parent_row = link.find_element(By.XPATH, './ancestor::tr')
                        cells = parent_row.find_elements(By.TAG_NAME, 'td')

                        self.seen_permit_ids.add(permit_number)
                        self.permits.append({
                            'permit_number': permit_number,
                            'address': self._safe_get_text(cells[1]) if len(cells) > 1 else 'N/A',
                            'type': self._safe_get_text(cells[2]) if len(cells) > 2 else 'N/A',
                            'value': '$0.00',
                            'issued_date': self._safe_get_text(cells[3]) if len(cells) > 3 else 'N/A',
                            'status': self._safe_get_text(cells[4]) if len(cells) > 4 else 'N/A'
                        })

                        if len(self.permits) % 10 == 0:
                            print(f"✓ Extracted {len(self.permits)} permits...")

                    except Exception as e:
                        self.logger.warning(f"Error extracting permit: {e}")
                        continue

            print(f"\n✅ Scraping complete! Total permits: {len(self.permits)}")

            if len(self.permits) > 0:
                self.health_check.record_success(len(self.permits))
            else:
                self.health_check.record_failure("No permits extracted")

            return self.permits

        except Exception as e:
            self.logger.error(f"Fatal error: {e}", exc_info=True)
            self.health_check.record_failure(str(e))
            print(f"❌ Fatal error: {e}")
            return []

        finally:
            self._close_driver()
