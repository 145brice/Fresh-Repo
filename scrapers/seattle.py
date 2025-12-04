from datetime import datetime, timedelta
import requests
import csv
import time
import os
from .utils import retry_with_backoff, setup_logger, ScraperHealthCheck, save_partial_results

class SeattlePermitScraper:
    def __init__(self):
        # Seattle Open Data API endpoint
        self.endpoints = [
            'https://data.seattle.gov/resource/76t5-zqzr.json',  # Building Permits
        ]
        self.permits = []
        self.seen_permit_ids = set()
        self.logger = setup_logger('seattle')
        self.health_check = ScraperHealthCheck('seattle')

    @retry_with_backoff(max_retries=3, initial_delay=2, exceptions=(requests.RequestException,))
    def _fetch_batch(self, endpoint_url, params):
        """Fetch a single batch with retry logic"""
        response = requests.get(endpoint_url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def scrape_permits(self, max_permits=5000, days_back=90):
        """Scrape Seattle permits with auto-recovery"""
        self.logger.info("🏗️  Seattle WA Construction Permits Scraper")
        print(f"🏗️  Seattle WA Construction Permits Scraper")
        print(f"=" * 60)
        print(f"📅 Date Range: {(datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}")
        print(f"📡 Fetching up to {max_permits} permits from last {days_back} days...")

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        start_str = start_date.strftime('%Y-%m-%dT00:00:00.000')
        end_str = end_date.strftime('%Y-%m-%dT23:59:59.999')

        for endpoint_url in self.endpoints:
            self.logger.info(f"Trying endpoint: {endpoint_url}")
            print(f"\n🔍 Trying: {endpoint_url}")

            try:
                offset = 0
                batch_size = 1000

                while len(self.permits) < max_permits:
                    try:
                        params = {
                            '$where': f"issueddate >= '{start_str}' AND issueddate <= '{end_str}'",
                            '$order': 'issueddate DESC',
                            '$limit': min(batch_size, max_permits - len(self.permits)),
                            '$offset': offset
                        }

                        data = self._fetch_batch(endpoint_url, params)

                        if not data:
                            self.logger.info(f"No more data at offset {offset}")
                            break

                        for record in data:
                            permit_id = record.get('permitnum') or record.get('application_permit_number')

                            if permit_id and permit_id not in self.seen_permit_ids:
                                self.seen_permit_ids.add(permit_id)
                                self.permits.append({
                                    'permit_number': permit_id,
                                    'address': record.get('originaladdress1') or 'N/A',
                                    'type': record.get('permittypedesc') or record.get('permittypemapped') or 'N/A',
                                    'value': self._parse_cost(record.get('estprojectcost') or 0),
                                    'issued_date': self._format_date(record.get('issueddate')),
                                    'status': record.get('statuscurrent') or 'N/A'
                                })

                        print(f"✓ Fetched {len(self.permits)} permits so far...")

                        if len(data) < batch_size:
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
            filename = f'leads/seattle/{today}/{today}_seattle.csv'
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
                self.logger.info(f"✅ Scraped {len(permits)} permits for seattle")
                print(f"✅ Scraped {len(permits)} permits for seattle")
                return permits
            else:
                self.logger.warning("❌ No permits scraped for seattle")
                print(f"❌ No permits scraped for seattle - will retry next run")
                return []
        except Exception as e:
            self.logger.error(f"Fatal error in scraper: {e}", exc_info=True)
            self.health_check.record_failure(str(e))
            print(f"❌ Fatal error in seattle scraper: {e}")
            return []
