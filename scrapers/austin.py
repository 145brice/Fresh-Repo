import requests
from datetime import datetime, timedelta
import time
import csv
import os
from .utils import retry_with_backoff, setup_logger, ScraperHealthCheck, save_partial_results

class AustinPermitScraper:
    def __init__(self):
        self.base_url = "https://data.austintexas.gov/resource/3syk-w9eu.json"
        self.permits = []
        self.seen_permit_ids = set()
        self.logger = setup_logger('austin')
        self.health_check = ScraperHealthCheck('austin')

    @retry_with_backoff(max_retries=3, initial_delay=2, exceptions=(requests.RequestException,))
    def _fetch_batch(self, params):
        """Fetch a single batch with retry logic"""
        response = requests.get(self.base_url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def scrape_permits(self, max_permits=5000, days_back=90):
        """Scrape Austin permits with auto-recovery"""
        self.logger.info("🏗️  Austin TX Construction Permits Scraper")
        print(f"🏗️  Austin TX Construction Permits Scraper")
        print(f"=" * 60)
        print(f"📅 Date Range: {(datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}")
        print(f"📡 Fetching up to {max_permits} permits from last {days_back} days...")

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')

        self.logger.info(f"Date Range: {start_str} to {end_str}")

        offset = 0
        batch_size = 1000
        consecutive_failures = 0
        max_consecutive_failures = 3

        while len(self.permits) < max_permits:
            try:
                params = {
                    '$where': f"issue_date >= '{start_str}' AND issue_date <= '{end_str}'",
                    '$order': 'issue_date DESC',
                    '$limit': min(batch_size, max_permits - len(self.permits)),
                    '$offset': offset
                }

                data = self._fetch_batch(params)

                if not data:
                    self.logger.info(f"No more data at offset {offset}")
                    break

                # Reset failure counter on success
                consecutive_failures = 0

                for record in data:
                    permit_id = record.get('permit_num') or record.get('permit_number') or str(record.get('id', ''))
                    if permit_id not in self.seen_permit_ids:
                        self.seen_permit_ids.add(permit_id)
                        self.permits.append({
                            'permit_number': permit_id,
                            'address': f"{record.get('original_address1', '')}, {record.get('city', '')}, {record.get('state', '')}".strip(', '),
                            'type': record.get('permit_type_desc'),
                            'value': record.get('total_job_valuation', 0),
                            'issued_date': self._format_date(record.get('issue_date')),
                            'status': record.get('status')
                        })

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
                        filename = f'../leads/austin/{today}/{today}_austin_partial.csv'
                        save_partial_results(self.permits, filename, 'austin')
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
                        filename = f'../leads/austin/{today}/{today}_austin_partial.csv'
                        save_partial_results(self.permits, filename, 'austin')
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
            filename = f'../leads/austin/{today}/{today}_austin.csv'
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
                self.logger.info(f"✅ Scraped {len(permits)} permits for austin")
                print(f"✅ Scraped {len(permits)} permits for austin")
                return permits
            else:
                self.logger.warning("❌ No permits scraped for austin")
                print(f"❌ No permits scraped for austin - will retry next run")
                return []
        except Exception as e:
            self.logger.error(f"Fatal error in scraper: {e}", exc_info=True)
            self.health_check.record_failure(str(e))
            print(f"❌ Fatal error in austin scraper: {e}")
            return []

def scrape_permits():
    return AustinPermitScraper().scrape_permits()

def save_to_csv(permits):
    scraper = AustinPermitScraper()
    scraper.permits = permits
    scraper.save_to_csv()
