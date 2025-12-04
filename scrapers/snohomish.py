import requests
from bs4 import BeautifulSoup
import time
import random
import csv
import os
from datetime import datetime

class SnohomishPermitScraper:
    def __init__(self):
        self.base_url = "https://snohomishcountywa.gov/Archive.aspx?AMID=13"
        self.permits = []

    def scrape_permits(self, max_permits=100):
        """Scrape Snohomish County, WA building permits from HTML table"""
        print("🏗️  Snohomish County WA Construction Permits Scraper")
        print("=" * 60)

        # Retry logic with exponential backoff
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.get(self.base_url, timeout=30)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, 'html.parser')

                # Try specific table selector first, fallback to general table
                table_selectors = ['table#permitGrid', 'table', 'table.permitTable']
                rows = None

                for selector in table_selectors:
                    rows = soup.select(f'{selector} tr')
                    if rows and len(rows) > 1:  # Has header + data
                        break

                if not rows or len(rows) <= 1:
                    print(f"Snohomish: No table rows found on attempt {attempt + 1}")
                    if attempt < max_retries - 1:
                        time.sleep(random.uniform(1, 3) * (2 ** attempt))  # Exponential backoff
                        continue
                    return self.permits

                for row in rows[1:]:  # Skip header
                    cols = row.select('td')
                    if len(cols) >= 5:
                        try:
                            permit = cols[0].get_text(strip=True)
                            address = cols[1].get_text(strip=True)
                            owner = cols[2].get_text(strip=True) if len(cols) > 2 else ''
                            permit_type = cols[3].get_text(strip=True) if len(cols) > 3 else ''
                            date = cols[4].get_text(strip=True) if len(cols) > 4 else ''
                            value = cols[5].get_text(strip=True) if len(cols) > 5 else ''

                            # Clean up value (remove $ and commas)
                            if value:
                                value = value.replace('$', '').replace(',', '').strip()
                                try:
                                    value = float(value)
                                except ValueError:
                                    value = 0.0

                            self.permits.append({
                                'permit_number': permit,
                                'address': address,
                                'type': permit_type,
                                'value': value,
                                'issued_date': date,
                                'status': 'issued',
                                'owner': owner
                            })
                        except Exception as e:
                            print(f"Snohomish: Error parsing row: {e}")
                            continue

                print(f"Snohomish: Successfully scraped {len(self.permits)} permits")
                return self.permits

            except requests.exceptions.RequestException as e:
                print(f"Snohomish: Request error on attempt {attempt + 1}: {e}")
            except Exception as e:
                print(f"Snohomish: Unexpected error on attempt {attempt + 1}: {e}")

            if attempt < max_retries - 1:
                time.sleep(random.uniform(1, 3) * (2 ** attempt))  # Exponential backoff

        print(f"Snohomish: Failed to scrape after {max_retries} attempts")
        return self.permits

    def save_to_csv(self, filename=None):
        if not self.permits:
            return
        if filename is None:
            today = datetime.now().strftime('%Y-%m-%d')
            filename = f'../leads/snohomish/{today}/{today}_snohomish.csv'
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(self.permits[0].keys()))
            writer.writeheader()
            writer.writerows(self.permits)
        print(f"✅ Saved {len(self.permits)} permits to {filename}")

    def run(self):
        """Main execution with error handling"""
        try:
            permits = self.scrape_permits()
            if permits:
                self.save_to_csv()
                print(f"✅ Scraped {len(permits)} permits for snohomish")
                return permits
            else:
                print(f"❌ No permits scraped for snohomish - will retry next run")
                return []
        except Exception as e:
            print(f"❌ Fatal error in snohomish scraper: {e}")
            return []