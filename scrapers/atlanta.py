from datetime import datetime, timedelta
import requests
import csv
import time
import os
from .utils import retry_with_backoff, setup_logger, ScraperHealthCheck, save_partial_results

class AtlantaPermitScraper:
    def __init__(self):
        # Atlanta Open Data API endpoint for building permits
        self.endpoints = [
            'https://services1.arcgis.com/2iuE39TFJByDB5pA/arcgis/rest/services/Building_Permits/FeatureServer/0/query',
        ]
        self.permits = []
        self.seen_permit_ids = set()
        self.logger = setup_logger('atlanta')
        self.health_check = ScraperHealthCheck('atlanta')

    @retry_with_backoff(max_retries=3, initial_delay=2, exceptions=(requests.RequestException,))
    def _fetch_batch(self, endpoint_url, params):
        """Fetch a single batch with retry logic"""
        response = requests.get(endpoint_url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def scrape_permits(self, max_permits=5000, days_back=90):
        """Scrape Atlanta permits with auto-recovery"""
        self.logger.info("🏗️  Atlanta GA Construction Permits Scraper")
        print(f"🏗️  Atlanta GA Construction Permits Scraper")
        print(f"=" * 60)
        print(f"📅 Date Range: {(datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}")
        print(f"📡 Fetching up to {max_permits} permits from last {days_back} days...")

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        start_timestamp = int(start_date.timestamp() * 1000)
        end_timestamp = int(end_date.timestamp() * 1000)

        for endpoint_url in self.endpoints:
            self.logger.info(f"Trying endpoint: {endpoint_url}")
            print(f"\n🔍 Trying: {endpoint_url}")

            try:
                offset = 0
                batch_size = 1000

                while len(self.permits) < max_permits:
                    try:
                        params = {
                            'where': f"ISSUED_DATE >= {start_timestamp} AND ISSUED_DATE <= {end_timestamp}",
                            'outFields': '*',
                            'orderByFields': 'ISSUED_DATE DESC',
                            'resultOffset': offset,
                            'resultRecordCount': min(batch_size, max_permits - len(self.permits)),
                            'f': 'json'
                        }

                        data = self._fetch_batch(endpoint_url, params)

                        if not data.get('features'):
                            self.logger.info(f"No more data at offset {offset}")
                            break

                        for record in data['features']:
                            attrs = record.get('attributes', {})
                            permit_id = attrs.get('PERMIT_NUMBER') or attrs.get('OBJECTID')

                            if permit_id and permit_id not in self.seen_permit_ids:
                                self.seen_permit_ids.add(permit_id)
                                self.permits.append({
                                    'permit_number': permit_id,
                                    'address': attrs.get('ADDRESS') or 'N/A',
                                    'type': attrs.get('PERMIT_TYPE') or 'N/A',
                                    'value': self._parse_cost(attrs.get('COST') or 0),
                                    'issued_date': self._format_date(attrs.get('ISSUED_DATE')),
                                    'status': attrs.get('STATUS') or 'N/A'
                                })

                        print(f"✓ Fetched {len(self.permits)} permits so far...")

                        if len(data['features']) < batch_size:
                            break

                        offset += batch_size
                        time.sleep(0.5)

                    except Exception as e:
                        self.logger.error(f"Batch error at offset {offset}: {e}")
                        print(f"⚠️  Error at offset {offset}, continuing...")
                        break

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

    def _format_date(self, timestamp):
        if not timestamp:
            return 'N/A'
        try:
            # Convert milliseconds to seconds
            return datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d')
        except:
            return 'N/A'

    def save_to_csv(self, filename=None):
        if not self.permits:
            return
        if filename is None:
            today = datetime.now().strftime('%Y-%m-%d')
            filename = f'leads/atlanta/{today}/{today}_atlanta.csv'
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
                self.logger.info(f"✅ Scraped {len(permits)} permits for atlanta")
                print(f"✅ Scraped {len(permits)} permits for atlanta")
                return permits
            else:
                self.logger.warning("❌ No permits scraped for atlanta")
                print(f"❌ No permits scraped for atlanta - will retry next run")
                return []
        except Exception as e:
            self.logger.error(f"Fatal error in scraper: {e}", exc_info=True)
            self.health_check.record_failure(str(e))
            print(f"❌ Fatal error in atlanta scraper: {e}")
            return []
