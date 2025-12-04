"""
Atlanta GA Permit Scraper using Selenium
Scrapes from Accela Citizen Access portal
"""
from datetime import datetime, timedelta
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
from .selenium_base import SeleniumScraperBase

class AtlantaSeleniumScraper(SeleniumScraperBase):
    def __init__(self):
        super().__init__(
            city_name='Atlanta',
            url='https://aca-prod.accela.com/ATLANTA_GA/Cap/CapHome.aspx?module=Building&customglobalsearch=true'
        )

        # Accela-specific selectors (multiple attempts for auto-fix)
        self.selector_attempts.update({
            'search_button': [
                ('css', 'input[type="submit"][value="Search"]'),
                ('css', 'input[type="submit"][value="search"]'),
                ('css', '#ctl00_PlaceHolderMain_btnNewSearch'),
                ('xpath', '//input[@type="submit" and contains(@value, "Search")]'),
            ],
            'results_table': [
                ('css', 'table.ACA_GridView'),
                ('css', 'table[id*="GridView"]'),
                ('css', 'table.grid'),
                ('xpath', '//table[contains(@class, "Grid")]'),
            ],
            'result_rows': [
                ('css', 'table.ACA_GridView tr'),
                ('css', 'table[id*="GridView"] tr'),
                ('xpath', '//table[contains(@class, "Grid")]//tr'),
            ],
            'next_page': [
                ('css', 'a[title="Next Page"]'),
                ('css', 'a.aca_pagination_NextRow'),
                ('xpath', '//a[contains(@title, "Next")]'),
            ]
        })

    def scrape_permits(self, max_permits=5000, days_back=90):
        """Scrape Atlanta permits using Selenium with auto-recovery"""
        self.logger.info("🏗️  Atlanta GA Construction Permits Scraper (Selenium)")
        print(f"🏗️  Atlanta GA Construction Permits Scraper (Selenium)")
        print(f"=" * 60)
        print(f"📅 Date Range: {(datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}")
        print(f"🌐 Using Selenium to scrape Accela portal...")

        if not self._init_driver():
            self.logger.error("Failed to initialize driver")
            return []

        try:
            # Navigate to the search page
            self.logger.info(f"Loading {self.url}")
            print(f"\n🔍 Loading Atlanta permit portal...")
            self.driver.get(self.url)
            time.sleep(3)  # Wait for page to load

            # Try to find and interact with search form
            print(f"📝 Filling out search form...")

            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)

            # Attempt to fill in date fields (Accela typically has from/to date inputs)
            date_from_selectors = [
                ('css', 'input[id*="txtFrom"]'),
                ('css', 'input[id*="DateFrom"]'),
                ('css', 'input[name*="from"]'),
                ('xpath', '//input[contains(@id, "From") and contains(@id, "Date")]'),
            ]

            date_to_selectors = [
                ('css', 'input[id*="txtTo"]'),
                ('css', 'input[id*="DateTo"]'),
                ('css', 'input[name*="to"]'),
                ('xpath', '//input[contains(@id, "To") and contains(@id, "Date")]'),
            ]

            # Try to find and fill date fields
            date_from_field = self._try_find_element(date_from_selectors, timeout=10)
            date_to_field = self._try_find_element(date_to_selectors, timeout=5)

            if date_from_field:
                try:
                    date_from_field.clear()
                    date_from_field.send_keys(start_date.strftime('%m/%d/%Y'))
                    self.logger.info(f"Set from date: {start_date.strftime('%m/%d/%Y')}")
                except Exception as e:
                    self.logger.warning(f"Could not set from date: {e}")

            if date_to_field:
                try:
                    date_to_field.clear()
                    date_to_field.send_keys(end_date.strftime('%m/%d/%Y'))
                    self.logger.info(f"Set to date: {end_date.strftime('%m/%d/%Y')}")
                except Exception as e:
                    self.logger.warning(f"Could not set to date: {e}")

            # Click search button
            search_button = self._try_find_element(self.selector_attempts['search_button'], timeout=10)
            if search_button:
                print(f"🔎 Submitting search...")
                search_button.click()
                time.sleep(5)  # Wait for results to load
            else:
                self.logger.warning("Could not find search button, proceeding anyway")

            # Extract permits from results
            page_num = 1
            while len(self.permits) < max_permits:
                print(f"\n📄 Processing page {page_num}...")

                # Try more specific selectors for Accela data rows
                # Accela uses specific CSS classes for data rows
                data_row_selectors = [
                    ('css', 'table.ACA_GridView tr.ACA_TabRow_Odd'),
                    ('css', 'table.ACA_GridView tr.ACA_TabRow_Even'),
                    ('css', 'table.ACA_GridView tr[class*="TabRow"]'),
                    ('xpath', '//table[contains(@class, "ACA_GridView")]//tr[contains(@class, "TabRow")]'),
                ]

                # Try to find data rows directly
                data_rows = []
                for selector_type, selector in data_row_selectors:
                    try:
                        if selector_type == 'css':
                            from selenium.webdriver.support.ui import WebDriverWait
                            from selenium.webdriver.support import expected_conditions as EC
                            rows = WebDriverWait(self.driver, 10).until(
                                EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
                            )
                        elif selector_type == 'xpath':
                            rows = WebDriverWait(self.driver, 10).until(
                                EC.presence_of_all_elements_located((By.XPATH, selector))
                            )

                        if rows and len(rows) > 0:
                            data_rows = rows
                            self.logger.info(f"Found {len(rows)} data rows with {selector_type}: {selector}")
                            break
                    except Exception:
                        continue

                if not data_rows:
                    self.logger.warning("No data rows found")
                    # Fallback: try to find any table and look for links (permits usually have links)
                    try:
                        permit_links = self.driver.find_elements(By.CSS_SELECTOR, 'table.ACA_GridView a[href*="Detail"]')
                        if permit_links:
                            self.logger.info(f"Found {len(permit_links)} permit links")
                            # Extract permit numbers from links
                            for link in permit_links[:max_permits]:
                                try:
                                    permit_text = link.text.strip()
                                    if permit_text and permit_text not in self.seen_permit_ids:
                                        self.seen_permit_ids.add(permit_text)
                                        # Get parent row to extract other data
                                        parent_row = link.find_element(By.XPATH, './ancestor::tr')
                                        cells = parent_row.find_elements(By.TAG_NAME, 'td')

                                        self.permits.append({
                                            'permit_number': permit_text,
                                            'address': self._safe_get_text(cells[1]) if len(cells) > 1 else 'N/A',
                                            'type': self._safe_get_text(cells[2]) if len(cells) > 2 else 'N/A',
                                            'value': '$0.00',
                                            'issued_date': self._safe_get_text(cells[3]) if len(cells) > 3 else 'N/A',
                                            'status': self._safe_get_text(cells[4]) if len(cells) > 4 else 'N/A'
                                        })
                                except Exception as e:
                                    self.logger.warning(f"Error extracting from link: {e}")
                                    continue

                            print(f"✓ Extracted {len(permit_links)} permits using link fallback (Total: {len(self.permits)})")
                    except Exception as e:
                        self.logger.error(f"Fallback extraction failed: {e}")
                    break

                # Process data rows
                permits_on_page = 0
                for row in data_rows:
                    if len(self.permits) >= max_permits:
                        break

                    try:
                        cells = row.find_elements(By.TAG_NAME, 'td')
                        if len(cells) < 3:
                            continue

                        # Look for permit number in first cell (usually a link)
                        permit_link = cells[0].find_elements(By.TAG_NAME, 'a')
                        if permit_link:
                            permit_number = permit_link[0].text.strip()
                        else:
                            permit_number = self._safe_get_text(cells[0])

                        # Validate this looks like a permit number (not pagination, etc)
                        if not permit_number or len(permit_number) < 5 or '<' in permit_number or '>' in permit_number:
                            continue

                        # Avoid duplicates
                        if permit_number in self.seen_permit_ids:
                            continue

                        self.seen_permit_ids.add(permit_number)
                        self.permits.append({
                            'permit_number': permit_number,
                            'address': self._safe_get_text(cells[1]) if len(cells) > 1 else 'N/A',
                            'type': self._safe_get_text(cells[2]) if len(cells) > 2 else 'N/A',
                            'value': '$0.00',  # Value typically not in search results
                            'issued_date': self._safe_get_text(cells[3]) if len(cells) > 3 else 'N/A',
                            'status': self._safe_get_text(cells[4]) if len(cells) > 4 else 'N/A'
                        })
                        permits_on_page += 1

                    except Exception as e:
                        self.logger.warning(f"Error processing row: {e}")
                        continue

                print(f"✓ Extracted {permits_on_page} permits from page {page_num} (Total: {len(self.permits)})")

                # Try to find next page button
                next_button = self._try_find_element(self.selector_attempts['next_page'], timeout=5)

                if next_button:
                    try:
                        next_button.click()
                        page_num += 1
                        time.sleep(3)  # Wait for next page to load
                    except Exception as e:
                        self.logger.info(f"No more pages: {e}")
                        break
                else:
                    self.logger.info("No next page button found")
                    break

            print(f"\n✅ Scraping complete! Total permits: {len(self.permits)}")
            self.health_check.record_success(len(self.permits))
            return self.permits

        except Exception as e:
            self.logger.error(f"Fatal error in scraper: {e}", exc_info=True)
            self.health_check.record_failure(str(e))
            print(f"❌ Fatal error: {e}")
            return []

        finally:
            self._close_driver()

def scrape_permits():
    return AtlantaSeleniumScraper().scrape_permits()

def save_to_csv(permits):
    scraper = AtlantaSeleniumScraper()
    scraper.permits = permits
    scraper.save_to_csv()
