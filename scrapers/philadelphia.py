from datetime import datetime, timedelta
import requests
import csv
import time
import os
from .utils import retry_with_backoff, setup_logger, ScraperHealthCheck

class PhiladelphiaPermitScraper:
    def __init__(self):
        self.endpoints = ['https://phl.carto.com/api/v2/sql']
        self.permits = []
        self.seen_permit_ids = set()
        self.logger = setup_logger('philadelphia')
        self.health_check = ScraperHealthCheck('philadelphia')

    @retry_with_backoff(max_retries=3, initial_delay=2, exceptions=(requests.RequestException,))
    def _fetch_batch(self, endpoint_url, params):
        response = requests.get(endpoint_url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def scrape_permits(self, max_permits=5000, days_back=90):
        self.logger.info("🏗️  Philadelphia PA Construction Permits Scraper")
        print(f"🏗️  Philadelphia PA Construction Permits Scraper")
        print(f"=" * 60)
        print(f"📅 Date Range: {(datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}")
        print(f"📡 Using Carto SQL API...")

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        start_str = start_date.strftime('%Y-%m-%d')

        for endpoint in self.endpoints:
            try:
                offset = 0
                batch_size = 1000

                while len(self.permits) < max_permits:
                    # Fixed: query from 'permits' table not 'li_permits'
                    query = f"""
                        SELECT permitnumber, permitissuedate, permitdescription,
                               address, typeofwork, opa_account_num
                        FROM permits
                        WHERE permitissuedate >= '{start_str}'
                        ORDER BY permitissuedate DESC
                        LIMIT {batch_size} OFFSET {offset}
                    """

                    params = {'q': query, 'format': 'json'}
                    result = self._fetch_batch(endpoint, params)
                    data = result.get('rows', [])

                    if not data:
                        self.logger.info(f"No more data at offset {offset}")
                        break

                    for record in data:
                        pid = record.get('permitnumber')
                        if pid and pid not in self.seen_permit_ids:
                            self.seen_permit_ids.add(pid)
                            self.permits.append({
                                'permit_number': pid,
                                'address': record.get('address') or 'N/A',
                                'type': record.get('permitdescription') or record.get('typeofwork') or 'N/A',
                                'value': '$0.00',  # No cost field in this dataset
                                'issued_date': record.get('permitissuedate','').split('T')[0] if record.get('permitissuedate') else 'N/A',
                                'status': 'Issued'  # All records are issued permits
                            })

                    print(f"✓ Fetched {len(self.permits)} permits so far...")

                    if len(data) < batch_size:
                        break
                    offset += batch_size
                    time.sleep(0.5)  # Rate limiting

                if self.permits:
                    self.logger.info(f"✅ Success! Got {len(self.permits)} permits from Carto")
                    self.health_check.record_success(len(self.permits))
                    print(f"\n✅ Scraping complete! Total permits: {len(self.permits)}")
                    break

            except Exception as e:
                self.logger.error(f"Endpoint error: {e}")
                print(f"❌ Endpoint failed: {e}")
                self.health_check.record_failure(str(e))

        if not self.permits:
            self.logger.warning("No permits found")
            print(f"⚠️  No permits found - will retry next run")

        return self.permits

    def save_to_csv(self, filename=None):
        if not self.permits:
            return
        if not filename:
            today = datetime.now().strftime('%Y-%m-%d')
            filename = f'leads/philadelphia/{today}/{today}_philadelphia.csv'
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(self.permits[0].keys()))
            writer.writeheader()
            writer.writerows(self.permits)

    def run(self):
        try:
            permits = self.scrape_permits()
            if permits:
                self.save_to_csv()
            return permits
        except Exception as e:
            self.logger.error(f"Fatal error: {e}")
            return []
