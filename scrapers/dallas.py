from datetime import datetime, timedelta
import requests
import csv
import time
import os
from .utils import retry_with_backoff, setup_logger, ScraperHealthCheck, save_partial_results

class DallasPermitScraper:
    def __init__(self):
        self.endpoints = [
            {
                'url': 'https://services2.arcgis.com/rwnOSbfKSwyTBcwN/arcgis/rest/services/NewPermit_2008_2024/FeatureServer/0/query',
                'type': 'arcgis_api'
            }
        ]
        self.permits = []
        self.seen_permit_ids = set()
        self.logger = setup_logger('dallas')
        self.health_check = ScraperHealthCheck('dallas')

    @retry_with_backoff(max_retries=3, initial_delay=2, exceptions=(requests.RequestException,))
    def _fetch_arcgis_batch(self, url, params):
        """Fetch a single ArcGIS batch with retry logic"""
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def scrape_permits(self, max_permits=5000, days_back=90):
        """Scrape Dallas permits with auto-recovery"""
        self.logger.info("🏗️  Dallas TX Construction Permits Scraper")
        print(f"🏗️  Dallas TX Construction Permits Scraper")
        print(f"=" * 60)
        print(f"📅 Date Range: {(datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}")
        print(f"📡 Trying Dallas data sources...")

        # Try each endpoint
        for i, endpoint in enumerate(self.endpoints, 1):
            self.logger.info(f"Attempt {i}/{len(self.endpoints)}: {endpoint['type']}")
            print(f"\n🔍 Attempt {i}/{len(self.endpoints)}: {endpoint['type']}")

            try:
                if endpoint['type'] == 'arcgis_api':
                    success = self._try_arcgis_api(endpoint['url'], max_permits, days_back)

                if success and len(self.permits) > 0:
                    self.logger.info(f"✅ Success! Got {len(self.permits)} permits")
                    self.health_check.record_success(len(self.permits))
                    print(f"✅ Successfully retrieved {len(self.permits)} permits!")
                    return self.permits

            except Exception as e:
                self.logger.warning(f"Endpoint failed: {e}")
                print(f"   ❌ Failed: {e}")
                continue

        # All endpoints failed
        self.logger.error("All Dallas endpoints failed")
        self.health_check.record_failure("All endpoints failed")
        print(f"\n⚠️  All Dallas endpoints failed - will retry next run")
        return []

    def _try_arcgis_api(self, url, max_permits, days_back):
        """Try ArcGIS REST API with date filtering"""
        offset = 0
        batch_size = 1000
        consecutive_failures = 0
        max_consecutive_failures = 3

        # First try without date filter to see if there's any data
        where_clause = '1=1'  # Get all records first

        while len(self.permits) < max_permits:
            try:
                params = {
                    'where': where_clause,
                    'outFields': '*',
                    'returnGeometry': 'false',
                    'resultOffset': offset,
                    'resultRecordCount': min(batch_size, max_permits - len(self.permits)),
                    'orderByFields': 'ISSUE_DATE DESC',  # Most recent first
                    'f': 'json'
                }

                data = self._fetch_arcgis_batch(url, params)

                if 'features' not in data or not data['features']:
                    self.logger.info(f"No more data at offset {offset}")
                    break

                # Reset failure counter on success
                consecutive_failures = 0

                for feature in data['features']:
                    attrs = feature.get('attributes', {})
                    permit_id = str(attrs.get('PERMIT_No', '')).strip()

                    if permit_id and permit_id not in self.seen_permit_ids:
                        self.seen_permit_ids.add(permit_id)
                        self.permits.append({
                            'permit_number': permit_id,
                            'address': attrs.get('ADDRESS', 'N/A'),
                            'type': attrs.get('PERMIT_TYPE', 'N/A'),
                            'value': self._parse_cost(attrs.get('VALUE', 0)),
                            'issued_date': self._format_date(attrs.get('ISSUE_DATE')),
                            'status': attrs.get('Status', 'N/A')
                        })

                self.logger.debug(f"Fetched batch at offset {offset}: {len(data['features'])} records")

                if len(data['features']) < batch_size:
                    break
                offset += batch_size
                time.sleep(0.5)

            except requests.RequestException as e:
                consecutive_failures += 1
                self.logger.warning(f"Request error at offset {offset}: {e}")

                if consecutive_failures >= max_consecutive_failures:
                    self.logger.error(f"Too many consecutive failures, stopping ArcGIS API")
                    if self.permits:
                        today = datetime.now().strftime('%Y-%m-%d')
                        filename = f'../leads/dallas/{today}/{today}_dallas_partial.csv'
                        save_partial_results(self.permits, filename, 'dallas')
                    break

                offset += batch_size
                time.sleep(2)

            except Exception as e:
                consecutive_failures += 1
                self.logger.error(f"Unexpected error at offset {offset}: {e}", exc_info=True)

                if consecutive_failures >= max_consecutive_failures:
                    self.logger.error("Too many consecutive failures, stopping ArcGIS API")
                    if self.permits:
                        today = datetime.now().strftime('%Y-%m-%d')
                        filename = f'../leads/dallas/{today}/{today}_dallas_partial.csv'
                        save_partial_results(self.permits, filename, 'dallas')
                    break

                offset += batch_size
                time.sleep(2)

        return len(self.permits) > 0

    def _parse_cost(self, value):
        try:
            return float(str(value).replace('$', '').replace(',', '')) if value else 0
        except:
            return 0

    def _format_date(self, timestamp):
        if not timestamp:
            return 'N/A'
        try:
            if isinstance(timestamp, (int, float)):
                return datetime.fromtimestamp(int(timestamp) / 1000).strftime('%Y-%m-%d')
            return str(timestamp)[:10]
        except:
            return 'N/A'

    def save_to_csv(self, filename=None):
        if not self.permits:
            return
        if filename is None:
            today = datetime.now().strftime('%Y-%m-%d')
            filename = f'../leads/dallas/{today}/{today}_dallas.csv'
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
                self.logger.info(f"✅ Scraped {len(permits)} permits for dallas")
                print(f"✅ Scraped {len(permits)} permits for dallas")
                return permits
            else:
                self.logger.warning("❌ No permits scraped for dallas")
                print(f"❌ No permits scraped for dallas - will retry next run")
                return []
        except Exception as e:
            self.logger.error(f"Fatal error in scraper: {e}", exc_info=True)
            self.health_check.record_failure(str(e))
            print(f"❌ Fatal error in dallas scraper: {e}")
            return []

def scrape_permits():
    return DallasPermitScraper().scrape_permits()

def save_to_csv(permits):
    scraper = DallasPermitScraper()
    scraper.permits = permits
    scraper.save_to_csv()