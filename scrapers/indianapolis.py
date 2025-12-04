from datetime import datetime, timedelta
import requests
import csv
import time
import os
from .utils import retry_with_backoff, setup_logger, ScraperHealthCheck, save_partial_results

class IndianapolisPermitScraper:
    def __init__(self):
        self.endpoints = [
            'https://data.indy.gov/resource/mqp2-yq28.json',  # Building Permits
        ]
        self.permits = []
        self.seen_permit_ids = set()
        self.logger = setup_logger('indianapolis')
        self.health_check = ScraperHealthCheck('indianapolis')

    @retry_with_backoff(max_retries=3, initial_delay=2, exceptions=(requests.RequestException,))
    def _fetch_batch(self, endpoint_url, params):
        response = requests.get(endpoint_url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def scrape_permits(self, max_permits=5000, days_back=90):
        self.logger.info("🏗️  Indianapolis IN Construction Permits Scraper")
        print(f"🏗️  Indianapolis IN Construction Permits Scraper")
        print(f"=" * 60)
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        start_str = start_date.strftime('%Y-%m-%dT00:00:00.000')
        end_str = end_date.strftime('%Y-%m-%dT23:59:59.999')

        for endpoint_url in self.endpoints:
            try:
                offset = 0
                batch_size = 1000

                while len(self.permits) < max_permits:
                    params = {
                        '$where': f"issue_date >= '{start_str}' AND issue_date <= '{end_str}'",
                        '$order': 'issue_date DESC',
                        '$limit': min(batch_size, max_permits - len(self.permits)),
                        '$offset': offset
                    }

                    data = self._fetch_batch(endpoint_url, params)
                    if not data:
                        break

                    for record in data:
                        permit_id = record.get('permit_number') or record.get('permitnumber')
                        if permit_id and permit_id not in self.seen_permit_ids:
                            self.seen_permit_ids.add(permit_id)
                            self.permits.append({
                                'permit_number': permit_id,
                                'address': record.get('address') or 'N/A',
                                'type': record.get('permit_type') or 'N/A',
                                'value': self._parse_cost(record.get('declared_value') or 0),
                                'issued_date': self._format_date(record.get('issue_date')),
                                'status': record.get('status') or 'N/A'
                            })

                    if len(data) < batch_size:
                        break
                    offset += batch_size
                    time.sleep(0.5)

                if self.permits:
                    break
            except Exception as e:
                self.logger.error(f"Error: {e}")
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
            filename = f'leads/indianapolis/{today}/{today}_indianapolis.csv'
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(self.permits[0].keys()))
            writer.writeheader()
            writer.writerows(self.permits)
        print(f"✅ Saved {len(self.permits)} permits to {filename}")

    def run(self):
        try:
            permits = self.scrape_permits()
            if permits:
                self.save_to_csv()
                return permits
            return []
        except Exception as e:
            self.logger.error(f"Fatal error: {e}", exc_info=True)
            self.health_check.record_failure(str(e))
            return []
