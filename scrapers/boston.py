from datetime import datetime, timedelta
import requests
import csv
import time
import os
from .utils import retry_with_backoff, setup_logger, ScraperHealthCheck

class BostonPermitScraper:
    def __init__(self):
        self.endpoints = ['https://data.boston.gov/api/3/action/datastore_search?resource_id=6ddcd912-32a0-43df-9908-63574f8c7e77']
        self.permits = []
        self.seen_permit_ids = set()
        self.logger = setup_logger('boston')
        self.health_check = ScraperHealthCheck('boston')

    @retry_with_backoff(max_retries=3, initial_delay=2, exceptions=(requests.RequestException,))
    def _fetch_batch(self, endpoint_url, params):
        response = requests.get(endpoint_url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def scrape_permits(self, max_permits=5000, days_back=90):
        print("🏗️  Boston MA Construction Permits Scraper")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        for endpoint in self.endpoints:
            try:
                offset = 0
                while len(self.permits) < max_permits:
                    params = {
                        'limit': 1000,
                        'offset': offset
                    }
                    result = self._fetch_batch(endpoint, params)
                    data = result.get('result', {}).get('records', [])
                    if not data:
                        break
                    for record in data:
                        permit_date_str = record.get('issued_date')
                        if permit_date_str:
                            try:
                                permit_date = datetime.strptime(permit_date_str.split('T')[0], '%Y-%m-%d')
                                if permit_date < start_date or permit_date > end_date:
                                    continue
                            except:
                                continue
                        pid = record.get('permit') or record.get('_id')
                        if pid and pid not in self.seen_permit_ids:
                            self.seen_permit_ids.add(pid)
                            self.permits.append({
                                'permit_number': pid,
                                'address': record.get('address') or 'N/A',
                                'type': record.get('permittype') or 'N/A',
                                'value': f"${float(record.get('declared_valuation',0)):,.2f}" if record.get('declared_valuation') else "$0.00",
                                'issued_date': permit_date_str.split('T')[0] if permit_date_str else 'N/A',
                                'status': record.get('status') or 'N/A'
                            })
                    if len(data) < 1000:
                        break
                    offset += 1000
                if self.permits:
                    break
            except Exception as e:
                self.logger.error(f"Error: {e}")
        return self.permits

    def save_to_csv(self, filename=None):
        if not self.permits:
            return
        if not filename:
            today = datetime.now().strftime('%Y-%m-%d')
            filename = f'leads/boston/{today}/{today}_boston.csv'
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
