from datetime import datetime, timedelta
import requests
import csv
import time
import os
from .utils import retry_with_backoff, setup_logger, ScraperHealthCheck, save_partial_results

class ChattanoogaPermitScraper:
    def __init__(self):
        # Chattanooga Open Data Portal (updated endpoint)
        self.base_url = "https://www.chattadata.org/resource/764y-vxm2.json"
        self.permits = []
        self.seen_permit_ids = set()
        self.logger = setup_logger('chattanooga')
        self.health_check = ScraperHealthCheck('chattanooga')

    @retry_with_backoff(max_retries=3, initial_delay=2, exceptions=(requests.RequestException,))
    def _fetch_batch(self, params):
        """Fetch a single batch with retry logic"""
        response = requests.get(self.base_url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def scrape_permits(self, max_permits=5000, days_back=90):
        """
        Scrape Chattanooga building permits with auto-recovery

        Args:
            max_permits: Maximum number of permits to retrieve (up to 5000)
            days_back: Number of days back to search (default 90)
        """
        self.logger.info("🏗️  Chattanooga TN Construction Permits Scraper")
        print(f"🏗️  Chattanooga TN Construction Permits Scraper")
        print(f"=" * 60)
        print(f"Fetching up to {max_permits} permits from last {days_back} days...")
        print()

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        # Format dates for filtering
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')

        self.logger.info(f"Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        print(f"Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        print()

        offset = 0
        batch_size = 1000
        total_fetched = 0
        consecutive_failures = 0
        max_consecutive_failures = 3

        while total_fetched < max_permits:
            try:
                # Use simple limit/offset for Chattanooga API
                params = {
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
                    # Filter by issued date in Python
                    issued_date_str = record.get('issueddate', '')
                    if issued_date_str:
                        try:
                            issued_date = datetime.fromisoformat(issued_date_str.replace('Z', '+00:00'))
                            if start_date <= issued_date <= end_date:
                                permit_id = record.get('permitnum') or str(record.get('id', ''))
                                if permit_id not in self.seen_permit_ids:
                                    self.seen_permit_ids.add(permit_id)
                                    self.permits.append({
                                        'permit_number': permit_id,
                                        'address': f"{record.get('originaladdress1', '')} {record.get('originalcity', '')} {record.get('originalstate', '')} {record.get('originalzip', '')}".strip(),
                                        'type': record.get('permittype') or record.get('permitclass') or 'N/A',
                                        'value': self._parse_cost(record.get('estprojectcost') or 0),
                                        'issued_date': self._format_date(record.get('issueddate')),
                                        'status': record.get('statuscurrent') or 'N/A'
                                    })
                        except:
                            continue  # Skip records with invalid dates

                total_fetched += len(data)
                self.logger.debug(f"Fetched batch at offset {offset}: {len(data)} records, filtered to {len(self.permits)}")

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
                        filename = f'../leads/chattanooga/{today}/{today}_chattanooga_partial.csv'
                        save_partial_results(self.permits, filename, 'chattanooga')
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
                        filename = f'../leads/chattanooga/{today}/{today}_chattanooga_partial.csv'
                        save_partial_results(self.permits, filename, 'chattanooga')
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
            filename = f'../leads/chattanooga/{today}/{today}_chattanooga.csv'
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
                self.logger.info(f"✅ Scraped {len(permits)} permits for chattanooga")
                print(f"✅ Scraped {len(permits)} permits for chattanooga")
                return permits
            else:
                self.logger.warning("❌ No permits scraped for chattanooga")
                print(f"❌ No permits scraped for chattanooga - will retry next run")
                return []
        except Exception as e:
            self.logger.error(f"Fatal error in scraper: {e}", exc_info=True)
            self.health_check.record_failure(str(e))
            print(f"❌ Fatal error in chattanooga scraper: {e}")
            return []


# Simple functions for compatibility
def scrape_permits():
    scraper = ChattanoogaPermitScraper()
    return scraper.scrape_permits(max_permits=5000, days_back=90)

def save_to_csv(permits):
    scraper = ChattanoogaPermitScraper()
    scraper.permits = permits
    scraper.save_to_csv()


if __name__ == '__main__':
    scraper = ChattanoogaPermitScraper()
    permits = scraper.scrape_permits(max_permits=5000, days_back=90)
    if permits:
        scraper.save_to_csv()
