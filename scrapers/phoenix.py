#!/usr/bin/env python3
"""
Phoenix Permit Scraper
Data source: City of Phoenix ArcGIS API
"""

from datetime import datetime, timedelta
import requests
import csv
import time
import os
from base_scraper import BaseScraper
from utils import retry_with_backoff, validate_state

class PhoenixScraper(BaseScraper):
    def __init__(self):
        super().__init__("Phoenix")
        # Phoenix uses ArcGIS REST API
        self.base_url = "https://services1.arcgis.com/mpVYz37anSdrK4d8/arcgis/rest/services/Building_Permits/FeatureServer/0/query"
        self.permits = []
        
    @retry_with_backoff(max_retries=3, initial_delay=2, exceptions=(requests.RequestException,))
    def _fetch_batch(self, params):
        """Fetch a single batch of permits with retry logic"""
        response = requests.get(self.base_url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def get_permits(self, max_permits=5000, days_back=30):
        """
        Scrape Phoenix building permits with auto-recovery

        Args:
            max_permits: Maximum number of permits to retrieve (up to 5000)
            days_back: Number of days back to search (default 90)
        """
        self.logger.info("=" * 60)
        self.logger.info("🏗️  Phoenix AZ Construction Permits Scraper")
        self.logger.info(f"Fetching up to {max_permits} permits from last {days_back} days...")

        print(f"🏗️  Phoenix AZ Construction Permits Scraper")
        print(f"=" * 60)
        print(f"Fetching up to {max_permits} permits from last {days_back} days...")
        print()

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        # Convert to Unix timestamp (milliseconds) for ArcGIS
        start_timestamp = int(start_date.timestamp() * 1000)
        end_timestamp = int(end_date.timestamp() * 1000)

        self.logger.info(f"Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        print(f"Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        print()

        offset = 0
        batch_size = 1000  # ArcGIS limit
        total_fetched = 0
        consecutive_failures = 0
        max_consecutive_failures = 3

        while total_fetched < max_permits:
            try:
                params = {
                    'where': f"issued_date >= {start_timestamp} AND issued_date <= {end_timestamp}",
                    'outFields': '*',
                    'returnGeometry': 'false',
                    'resultOffset': offset,
                    'resultRecordCount': min(batch_size, max_permits - total_fetched),
                    'f': 'json'
                }

                data = self._fetch_batch(params)

                if 'features' not in data or not data['features']:
                    self.logger.info(f"No more data available at offset {offset}")
                    break

                # Reset failure counter on success
                consecutive_failures = 0

                for feature in data['features']:
                    attrs = feature.get('attributes', {})
                    permit_id = str(attrs.get('permit_number') or attrs.get('PermitNumber') or attrs.get('OBJECTID', ''))

                    if permit_id not in self.seen_permit_ids:
                        self.seen_permit_ids.add(permit_id)

                        # Extract address first
                        address = attrs.get('address') or 'N/A'

                        # STATE VALIDATION: Only accept Arizona addresses
                        if not validate_state(address, 'phoenix', self.logger):
                            continue  # Skip this record - wrong state

                        self.permits.append({
                            'permit_number': permit_id,
                            'address': address,
                            'permit_type': attrs.get('work_type') or 'N/A',
                            'description': f"Value: ${self._parse_cost(attrs.get('cost') or 0):,.0f}, Status: {attrs.get('status') or 'N/A'}",
                            'date': self._format_date(attrs.get('issued_date')),
                            'city': 'Phoenix'
                        })

                total_fetched += len(data['features'])
                self.logger.debug(f"Fetched batch at offset {offset}: {len(data['features'])} records")

                if len(data['features']) < batch_size:
                    break
                offset += batch_size
                time.sleep(0.5)

            except requests.RequestException as e:
                consecutive_failures += 1
                self.logger.warning(f"Request error at offset {offset}: {e}")

                if consecutive_failures >= max_consecutive_failures:
                    self.logger.error(f"Too many consecutive failures ({consecutive_failures}), stopping scrape")
                    # Save partial results
                    if self.permits:
                        today = datetime.now().strftime('%Y-%m-%d')
                        filename = f'../leads/phoenix/{today}/{today}_phoenix_partial.csv'
                        save_partial_results(self.permits, filename, 'phoenix')
                    break

                # Continue to next batch instead of breaking immediately
                self.logger.info(f"Skipping batch at offset {offset}, continuing...")
                offset += batch_size
                time.sleep(2)

            except Exception as e:
                consecutive_failures += 1
                self.logger.error(f"Unexpected error at offset {offset}: {e}", exc_info=True)

                if consecutive_failures >= max_consecutive_failures:
                    self.logger.error("Too many consecutive failures, stopping scrape")
                    if self.permits:
                        today = datetime.now().strftime('%Y-%m-%d')
                        filename = f'../leads/phoenix/{today}/{today}_phoenix_partial.csv'
                        save_partial_results(self.permits, filename, 'phoenix')
                    break

                offset += batch_size
                time.sleep(2)

        print()
        print(f"=" * 60)

        if self.permits:
            self.logger.info(f"✅ Scraping Complete! Found {len(self.permits)} permits")
            print(f"✅ Scraping Complete!")
            print(f"   Total Permits Found: {len(self.permits)}")
            print(f"   Duplicates Removed: {total_fetched - len(self.permits)}")
        else:
            self.logger.error("❌ No permits found")
            print(f"❌ No permits found")

        print(f"=" * 60)
        print()

        return self.permits
    
    def _parse_cost(self, value):
        """Parse cost value from various formats"""
        if not value:
            return 0
        try:
            if isinstance(value, (int, float)):
                return float(value)
            return float(str(value).replace('$', '').replace(',', ''))
        except:
            return 0
    
    def _format_date(self, timestamp):
        """Convert epoch timestamp to readable date"""
        if not timestamp:
            return 'N/A'
        
        try:
            if isinstance(timestamp, (int, float)):
                return datetime.fromtimestamp(int(timestamp) / 1000).strftime('%Y-%m-%d')
            return str(timestamp)[:10]
        except:
            return 'N/A'
    
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
    scraper = PhoenixScraper()
    permits, filepath = scraper.run()
    print(f"Scraped {len(permits)} permits, saved to {filepath}")
