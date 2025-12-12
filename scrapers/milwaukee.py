from datetime import datetime, timedelta
import requests
import csv
import time
import os
from utils import retry_with_backoff
from base_scraper import BaseScraper

class MilwaukeeScraper(BaseScraper):
    def __init__(self):
        super().__init__('milwaukee')
        self.endpoints = ['https://data.milwaukee.gov/resource/ibb5-m9j5.json']
        self.permits = []
        self.seen_permit_ids = set()

    @retry_with_backoff(max_retries=3, initial_delay=2, exceptions=(requests.RequestException,))
    def _fetch_batch(self, endpoint_url, params):
        response = requests.get(endpoint_url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def get_permits(self, max_permits=5000, days_back=90):
        print("🏗️  Milwaukee WI Construction Permits Scraper")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        start_str = start_date.strftime('%Y-%m-%dT00:00:00.000')

        for endpoint in self.endpoints:
            try:
                offset = 0
                while len(self.permits) < max_permits:
                    params = {
                        '$where': f"issue_date >= '{start_str}'",
                        '$order': 'issue_date DESC',
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
                                'permit_type': record.get('permit_type') or 'N/A',
                                'description': f"Value: {record.get('project_value', '$0.00')}, Status: {record.get('status') or 'N/A'}",
                                'date': record.get('issue_date','').split('T')[0] if record.get('issue_date') else 'N/A',
                                'city': 'Milwaukee'
                            })
                    if len(data) < 1000:
                        break
                    offset += 1000
                if self.permits:
                    break
            except Exception as e:
                self.logger.error(f"Error: {e}")
        return self.permits

    def run(self):
        try:
            permits = self.get_permits()
            if permits:
                filepath = self.save_to_csv(permits)
                return permits, filepath
            return [], None
        except Exception as e:
            self.logger.error(f"Fatal error: {e}")
            return [], None

if __name__ == "__main__":
    scraper = MilwaukeeScraper()
    permits, filepath = scraper.run()
    print(f"Scraped {len(permits)} permits, saved to {filepath}")
