from datetime import datetime, timedelta
import requests
import csv
import time
import os
from .utils import retry_with_backoff, setup_logger, ScraperHealthCheck, save_partial_results

class NashvillePermitScraper:
    def __init__(self):
        # Try multiple Nashville endpoints
        self.endpoints = [
            'https://data.nashville.gov/resource/3h5w-q8b7.json',
            'https://data.nashville.gov/resource/kqff-rxj8.json',  # Building Permit Applications
        ]
        self.permits = []
        self.seen_permit_ids = set()
        self.logger = setup_logger('nashville')
        self.health_check = ScraperHealthCheck('nashville')
        
    @retry_with_backoff(max_retries=3, initial_delay=2, exceptions=(requests.RequestException,))
    def _fetch_batch(self, endpoint_url, params):
        """Fetch a single batch with retry logic"""
        response = requests.get(endpoint_url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def scrape_permits(self, max_permits=5000, days_back=90):
        """Scrape Nashville permits with auto-recovery across multiple endpoints"""
        self.logger.info("🏗️  Nashville TN Construction Permits Scraper")
        print(f"🏗️  Nashville TN Construction Permits Scraper")
        print(f"=" * 60)
        print(f"📅 Date Range: {(datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}")
        print(f"📡 Fetching up to {max_permits} permits from last {days_back} days...")

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        start_str = start_date.strftime('%Y-%m-%dT00:00:00.000')
        end_str = end_date.strftime('%Y-%m-%dT23:59:59.999')

        # Try each endpoint
        for endpoint_url in self.endpoints:
            self.logger.info(f"Trying endpoint: {endpoint_url}")
            print(f"\n🔍 Trying: {endpoint_url}")

            try:
                offset = 0
                batch_size = 1000
                consecutive_failures = 0
                max_consecutive_failures = 3

                while len(self.permits) < max_permits:
                    try:
                        params = {
                            '$where': f"permit_issued_date >= '{start_str}' AND permit_issued_date <= '{end_str}'",
                            '$order': 'permit_issued_date DESC',
                            '$limit': min(batch_size, max_permits - len(self.permits)),
                            '$offset': offset
                        }

                        data = self._fetch_batch(endpoint_url, params)

                        if not data:
                            self.logger.info(f"No more data at offset {offset}")
                            break

                        # Reset failure counter on success
                        consecutive_failures = 0

                        for record in data:
                            permit_id = record.get('permit_number') or record.get('permit_id') or str(record.get('objectid', ''))
                            if permit_id not in self.seen_permit_ids:
                                self.seen_permit_ids.add(permit_id)
                                self.permits.append({
                                    'permit_number': permit_id,
                                    'address': record.get('address') or 'N/A',
                                    'type': record.get('permit_type') or 'N/A',
                                    'value': self._parse_cost(record.get('cost') or 0),
                                    'issued_date': self._format_date(record.get('permit_issued_date')),
                                    'status': record.get('status') or 'N/A'
                                })

                        if len(data) < batch_size:
                            break
                        offset += batch_size
                        time.sleep(0.5)

                    except requests.RequestException as e:
                        consecutive_failures += 1
                        self.logger.warning(f"Batch error at offset {offset}: {e}")

                        if consecutive_failures >= max_consecutive_failures:
                            self.logger.error(f"Too many consecutive failures, trying next endpoint")
                            break

                        offset += batch_size
                        time.sleep(2)

                if len(self.permits) > 0:
                    self.logger.info(f"✅ Success! Got {len(self.permits)} permits")
                    self.health_check.record_success(len(self.permits))
                    print(f"✅ Success! Got {len(self.permits)} permits")
                    return self.permits

            except Exception as e:
                self.logger.warning(f"Endpoint failed: {e}")
                print(f"   ❌ Error: {e}")
                continue

        # All endpoints failed
        self.logger.error("All Nashville endpoints failed")
        self.health_check.record_failure("All endpoints failed")
        print(f"\n⚠️  All Nashville endpoints failed - will retry next run")
        return []
    
    def _parse_cost(self, value):
        try:
            return float(str(value).replace('$', '').replace(',', '')) if value else 0
        except:
            return 0
    
    def _format_date(self, date_str):
        if not date_str:
            return 'N/A'
        try:
            return datetime.fromisoformat(str(date_str).replace('Z', '+00:00')).strftime('%Y-%m-%d')
        except:
            return 'N/A'
    
    def save_to_csv(self, filename=None):
        if not self.permits:
            return
        if filename is None:
            today = datetime.now().strftime('%Y-%m-%d')
            filename = f'../leads/nashville/{today}/{today}_nashville.csv'
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(self.permits[0].keys()))
            writer.writeheader()
            writer.writerows(self.permits)
        print(f"✅ Saved {len(self.permits)} permits to {filename}")

    def run(self):
        """Main execution with error handling and auto-recovery"""
        try:
            permits = self.scrape_permits()
            if permits:
                self.save_to_csv()
                self.logger.info(f"✅ Scraped {len(permits)} permits for nashville")
                print(f"✅ Scraped {len(permits)} permits for nashville")
                return permits
            else:
                self.logger.warning("❌ No permits scraped for nashville")
                print(f"❌ No permits scraped for nashville - will retry next run")
                return []
        except Exception as e:
            self.logger.error(f"Fatal error in scraper: {e}", exc_info=True)
            self.health_check.record_failure(str(e))
            print(f"❌ Fatal error in nashville scraper: {e}")
            return []

def scrape_permits():
    return NashvillePermitScraper().scrape_permits()

def save_to_csv(permits):
    scraper = NashvillePermitScraper()
    scraper.permits = permits
    scraper.save_to_csv()
