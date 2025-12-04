from datetime import datetime, timedelta
import requests
import csv
import time
import os
from .utils import retry_with_backoff, setup_logger, ScraperHealthCheck

class RichmondPermitScraper:
    def __init__(self):
        self.endpoints = ['https://data.richmondgov.com/resource/w6j8-aqqm.json']
        self.permits = []
        self.seen_permit_ids = set()
        self.logger = setup_logger('richmond')
        self.health_check = ScraperHealthCheck('richmond')

    @retry_with_backoff(max_retries=3, initial_delay=2, exceptions=(requests.RequestException,))
    def _fetch_batch(self, endpoint_url, params):
        response = requests.get(endpoint_url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def scrape_permits(self, max_permits=5000, days_back=90):
        print("🏗️  Richmond VA Construction Permits Scraper")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        start_str = start_date.strftime('%Y-%m-%dT00:00:00.000')

        for endpoint in self.endpoints:
            try:
                offset = 0
                while len(self.permits) < max_permits:
                    params = {
                        '$where': f"issued_date >= '{start_str}'",
                        '$order': 'issued_date DESC',
                        '$limit': 1000,
                        '$offset': offset
                    }
                    data = self._fetch_batch(endpoint, params)
                    if not data:
                        break
                    for record in data:
                        pid = record.get('permit_number')
                        if pid and pid not in self.seen_permit_ids:
                            self.seen_permit_ids.add(pid)
                            self.permits.append({
                                'permit_number': pid,
                                'address': record.get('address') or 'N/A',
                                'type': record.get('permit_type') or 'N/A',
                                'value': f"${float(record.get('value',0)):,.2f}" if record.get('value') else "$0.00",
                                'issued_date': record.get('issued_date','').split('T')[0] if record.get('issued_date') else 'N/A',
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
            filename = f'leads/richmond/{today}/{today}_richmond.csv'
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
