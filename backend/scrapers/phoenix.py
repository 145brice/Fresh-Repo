from datetime import datetime, timedelta
import requests
import csv
import time
import os
from .utils import retry_with_backoff, setup_logger, ScraperHealthCheck, save_partial_results

class PhoenixPermitScraper:
    def __init__(self):
        # Phoenix uses ArcGIS REST API
        self.base_url = "https://services1.arcgis.com/mpVYz37anSdrK4d8/arcgis/rest/services/Building_Permits/FeatureServer/0/query"
        self.permits = []
        self.seen_permit_ids = set()
        self.logger = setup_logger('phoenix')
        self.health_check = ScraperHealthCheck('phoenix')
        
    @retry_with_backoff(max_retries=3, initial_delay=2, exceptions=(requests.RequestException,))
    def _fetch_batch(self, params):
        """Fetch a single batch of permits with retry logic"""
        response = requests.get(self.base_url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def scrape_permits(self, max_permits=5000, days_back=90):
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
                        self.permits.append({
                            'permit_number': permit_id,
                            'address': attrs.get('address') or 'N/A',
                            'type': attrs.get('work_type') or 'N/A',
                            'value': self._parse_cost(attrs.get('cost') or 0),
                            'issued_date': self._format_date(attrs.get('issued_date')),
                            'status': attrs.get('status') or 'N/A'
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
            self.health_check.record_success(len(self.permits))
            print(f"✅ Scraping Complete!")
            print(f"   Total Permits Found: {len(self.permits)}")
            print(f"   Duplicates Removed: {total_fetched - len(self.permits)}")
        else:
            self.logger.error("❌ No permits found")
            self.health_check.record_failure("No permits retrieved")
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
    
    def save_to_csv(self, filename=None):
        """Save permits to CSV file"""
        if not self.permits:
            print("⚠️  No permits to save")
            return
        
        if filename is None:
            today = datetime.now().strftime('%Y-%m-%d')
            filename = f'../leads/phoenix/{today}/{today}_phoenix.csv'
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        print(f"💾 Saving to {filename}...")
        
        fieldnames = list(self.permits[0].keys())
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.permits)
        
        print(f"✅ Saved {len(self.permits)} permits to {filename}")
    
    def save_to_json(self, filename='../leads/phoenix_permits.json'):
        """Save permits to JSON file"""
        if not self.permits:
            print("⚠️  No permits to save")
            return
        
        print(f"💾 Saving to {filename}...")
        
        import json
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.permits, f, indent=2, default=str)
        
        print(f"✅ Saved {len(self.permits)} permits to {filename}")
    
    def get_statistics(self):
        """Print statistics about scraped permits"""
        if not self.permits:
            print("No permits to analyze")
            return
        
        print(f"\n📊 Permit Statistics:")
        print(f"   Total Permits: {len(self.permits)}")
        
        work_types = defaultdict(int)
        statuses = defaultdict(int)
        
        for permit in self.permits:
            work_types[permit['work_type']] += 1
            statuses[permit['status']] += 1
        
        print(f"   Work Types: {dict(work_types)}")
        print(f"   Statuses: {dict(statuses)}")

    def run(self):
        """Main execution with error handling and auto-recovery"""
        try:
            permits = self.scrape_permits()
            if permits:
                self.save_to_csv()
                self.logger.info(f"✅ Scraped {len(permits)} permits for phoenix")
                print(f"✅ Scraped {len(permits)} permits for phoenix")
                return permits
            else:
                self.logger.warning("❌ No permits scraped for phoenix")
                print(f"❌ No permits scraped for phoenix - will retry next run")
                return []
        except Exception as e:
            self.logger.error(f"Fatal error in scraper: {e}", exc_info=True)
            self.health_check.record_failure(str(e))
            print(f"❌ Fatal error in phoenix scraper: {e}")
            return []


def main():
    """Main execution function"""
    scraper = PhoenixPermitScraper()
    
    # Scrape permits (up to 5000, last 30 days)
    permits = scraper.scrape_permits(max_permits=5000, days_back=30)
    
    if permits:
        print(f"Successfully scraped {len(permits)} permits")
        scraper.save_to_csv()
        scraper.get_statistics()
    else:
        print("No permits found")


if __name__ == '__main__':
    main()
