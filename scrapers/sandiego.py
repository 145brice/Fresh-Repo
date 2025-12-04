from datetime import datetime, timedelta
import requests
import csv
import time
import os
from .utils import retry_with_backoff, setup_logger, ScraperHealthCheck, save_partial_results

class SanDiegoPermitScraper:
    def __init__(self):
        # San Diego Open Data API endpoint
        self.endpoints = [
            'https://datasd-prod.s3.amazonaws.com/opendatafiles/development_permits_datasd.csv',
        ]
        self.permits = []
        self.seen_permit_ids = set()
        self.logger = setup_logger('sandiego')
        self.health_check = ScraperHealthCheck('sandiego')

    @retry_with_backoff(max_retries=3, initial_delay=2, exceptions=(requests.RequestException,))
    def _fetch_csv(self, url):
        """Fetch CSV data with retry logic"""
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        return response.text

    def scrape_permits(self, max_permits=5000, days_back=90):
        """Scrape San Diego permits with auto-recovery"""
        self.logger.info("🏗️  San Diego CA Construction Permits Scraper")
        print(f"🏗️  San Diego CA Construction Permits Scraper")
        print(f"=" * 60)
        print(f"📅 Date Range: {(datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}")
        print(f"📡 Fetching permits from last {days_back} days...")

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        for endpoint_url in self.endpoints:
            self.logger.info(f"Trying endpoint: {endpoint_url}")
            print(f"\n🔍 Trying: {endpoint_url}")

            try:
                csv_data = self._fetch_csv(endpoint_url)

                import io
                reader = csv.DictReader(io.StringIO(csv_data))

                for row in reader:
                    if len(self.permits) >= max_permits:
                        break

                    permit_date_str = row.get('issue_date') or row.get('date_issued')
                    if not permit_date_str:
                        continue

                    try:
                        permit_date = datetime.strptime(permit_date_str.split('T')[0], '%Y-%m-%d')
                        if permit_date < start_date or permit_date > end_date:
                            continue
                    except:
                        continue

                    permit_id = row.get('permit_num') or row.get('project_id')

                    if permit_id and permit_id not in self.seen_permit_ids:
                        self.seen_permit_ids.add(permit_id)
                        self.permits.append({
                            'permit_number': permit_id,
                            'address': row.get('address') or 'N/A',
                            'type': row.get('permit_type') or 'N/A',
                            'value': self._parse_cost(row.get('estimated_cost') or 0),
                            'issued_date': permit_date.strftime('%Y-%m-%d'),
                            'status': row.get('status') or 'N/A'
                        })

                        if len(self.permits) % 100 == 0:
                            print(f"✓ Fetched {len(self.permits)} permits so far...")

                if self.permits:
                    break

            except Exception as e:
                self.logger.error(f"Endpoint error: {e}")
                print(f"❌ Endpoint failed: {e}")
                continue

        print(f"\n✅ Scraping complete! Total permits: {len(self.permits)}")
        self.health_check.record_success(len(self.permits))
        return self.permits

    def _parse_cost(self, cost):
        try:
            return f"${float(cost):,.2f}"
        except:
            return "$0.00"

    def save_to_csv(self, filename=None):
        if not self.permits:
            return
        if filename is None:
            today = datetime.now().strftime('%Y-%m-%d')
            filename = f'leads/sandiego/{today}/{today}_sandiego.csv'
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
                self.logger.info(f"✅ Scraped {len(permits)} permits for sandiego")
                print(f"✅ Scraped {len(permits)} permits for sandiego")
                return permits
            else:
                self.logger.warning("❌ No permits scraped for sandiego")
                print(f"❌ No permits scraped for sandiego - will retry next run")
                return []
        except Exception as e:
            self.logger.error(f"Fatal error in scraper: {e}", exc_info=True)
            self.health_check.record_failure(str(e))
            print(f"❌ Fatal error in sandiego scraper: {e}")
            return []
