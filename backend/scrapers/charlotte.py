from datetime import datetime, timedelta
import requests
import csv
import time
import os
from .utils import retry_with_backoff, setup_logger, ScraperHealthCheck, save_partial_results

class CharlottePermitScraper:
    def __init__(self):
        # Charlotte uses Socrata Open Data API
        self.base_url = "https://data.charlottenc.gov/resource/4bkj-9djb.json"
        self.permits = []
        self.seen_permit_ids = set()
        self.logger = setup_logger('charlotte')
        self.health_check = ScraperHealthCheck('charlotte')
        
    @retry_with_backoff(max_retries=3, initial_delay=2, exceptions=(requests.RequestException,))
    def _fetch_batch(self, params):
        """Fetch a single batch with retry logic"""
        response = requests.get(self.base_url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def scrape_permits(self, max_permits=5000, days_back=90):
        """
        Scrape Charlotte building permits
        
        Args:
            max_permits: Maximum number of permits to retrieve (up to 5000)
            days_back: Number of days back to search (default 90)
        """
        print(f"🏗️  Charlotte NC Construction Permits Scraper")
        print(f"=" * 60)
        print(f"Fetching up to {max_permits} permits from last {days_back} days...")
        print()
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # Format dates for Socrata API (ISO format)
        start_date_str = start_date.strftime('%Y-%m-%dT00:00:00.000')
        end_date_str = end_date.strftime('%Y-%m-%dT23:59:59.999')
        
        print(f"Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        print()
        
        offset = 0
        batch_size = 1000
        total_fetched = 0
        consecutive_failures = 0
        max_consecutive_failures = 3

        self.logger.info(f"Starting scrape: max_permits={max_permits}, days_back={days_back}")

        while total_fetched < max_permits:
            try:
                params = {
                    '$where': f"issued_date >= '{start_date_str}' AND issued_date <= '{end_date_str}'",
                    '$order': 'issued_date DESC',
                    '$limit': min(batch_size, max_permits - total_fetched),
                    '$offset': offset
                }

                data = self._fetch_batch(params)

                if not data:
                    self.logger.info(f"No more data at offset {offset}")
                    break

                # Reset failure counter on success
                consecutive_failures = 0

                for record in data:
                    permit_id = record.get('permit_number') or record.get('permit_id') or str(record.get('id', ''))
                    if permit_id not in self.seen_permit_ids:
                        self.seen_permit_ids.add(permit_id)
                        self.permits.append({
                            'permit_number': permit_id,
                            'address': record.get('address') or 'N/A',
                            'type': record.get('permit_type') or 'N/A',
                            'value': self._parse_cost(record.get('cost') or 0),
                            'issued_date': self._format_date(record.get('issued_date')),
                            'status': record.get('status') or 'N/A'
                        })

                total_fetched += len(data)
                self.logger.debug(f"Fetched batch at offset {offset}: {len(data)} records")

                if len(data) < batch_size:
                    break
                offset += batch_size
                time.sleep(0.5)

            except requests.RequestException as e:
                consecutive_failures += 1
                self.logger.warning(f"Request error at offset {offset}: {e}")

                if consecutive_failures >= max_consecutive_failures:
                    self.logger.error(f"Too many consecutive failures ({consecutive_failures}), stopping")
                    if self.permits:
                        today = datetime.now().strftime('%Y-%m-%d')
                        filename = f'../leads/charlotte/{today}/{today}_charlotte_partial.csv'
                        save_partial_results(self.permits, filename, 'charlotte')
                    break

                offset += batch_size
                time.sleep(2)

            except Exception as e:
                consecutive_failures += 1
                self.logger.error(f"Unexpected error at offset {offset}: {e}", exc_info=True)

                if consecutive_failures >= max_consecutive_failures:
                    self.logger.error("Too many consecutive failures, stopping")
                    if self.permits:
                        today = datetime.now().strftime('%Y-%m-%d')
                        filename = f'../leads/charlotte/{today}/{today}_charlotte_partial.csv'
                        save_partial_results(self.permits, filename, 'charlotte')
                    break

                offset += batch_size
                time.sleep(2)
        
        print()
        print(f"=" * 60)

        if self.permits:
            self.logger.info(f"✅ Scraping Complete! Found {len(self.permits)} permits")
            self.health_check.record_success(len(self.permits))
            print(f"✅ Scraping Complete!")
            print(f"   Total Permits Found: {len(self.permits)}")
        else:
            self.logger.error("❌ No permits found")
            self.health_check.record_failure("No permits retrieved")
            print(f"❌ No permits found")

        print(f"=" * 60)
        print()

        return self.permits
    
    def _parse_cost(self, value):
        """Parse cost value from various formats"""
        if not value:
            return 0
        try:
            if isinstance(value, (int, float)):
                return float(value)
            return float(str(value).replace('$', '').replace(',', ''))
        except:
            return 0
    
    def _format_date(self, date_str):
        """Convert ISO date string to readable date"""
        if not date_str:
            return 'N/A'
        try:
            if 'T' in str(date_str):
                dt = datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
            else:
                dt = datetime.strptime(str(date_str), '%Y-%m-%d')
            return dt.strftime('%Y-%m-%d')
        except:
            return 'N/A'
    
    def save_to_csv(self, filename=None):
        """Save permits to CSV file"""
        if not self.permits:
            print("⚠️  No permits to save")
            return
        
        if filename is None:
            today = datetime.now().strftime('%Y-%m-%d')
            filename = f'../leads/charlotte/{today}/{today}_charlotte.csv'
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        print(f"💾 Saving to {filename}...")
        
        fieldnames = list(self.permits[0].keys())
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.permits)
        
        print(f"✅ Saved {len(self.permits)} permits to {filename}")

    def run(self):
        """Main execution with error handling and auto-recovery"""
        try:
            permits = self.scrape_permits()
            if permits:
                self.save_to_csv()
                self.logger.info(f"✅ Scraped {len(permits)} permits for charlotte")
                print(f"✅ Scraped {len(permits)} permits for charlotte")
                return permits
            else:
                self.logger.warning("❌ No permits scraped for charlotte")
                print(f"❌ No permits scraped for charlotte - will retry next run")
                return []
        except Exception as e:
            self.logger.error(f"Fatal error in scraper: {e}", exc_info=True)
            self.health_check.record_failure(str(e))
            print(f"❌ Fatal error in charlotte scraper: {e}")
            return []


# Simple functions for compatibility
def scrape_permits():
    scraper = CharlottePermitScraper()
    return scraper.scrape_permits(max_permits=5000, days_back=90)

def save_to_csv(permits):
    scraper = CharlottePermitScraper()
    scraper.permits = permits
    scraper.save_to_csv()


if __name__ == '__main__':
    scraper = CharlottePermitScraper()
    permits = scraper.scrape_permits(max_permits=5000, days_back=90)
    if permits:
        scraper.save_to_csv()
