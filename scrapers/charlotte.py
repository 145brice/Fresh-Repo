from datetime import datetime, timedelta
import requests
import csv
import time
import os
from .utils import retry_with_backoff, setup_logger, ScraperHealthCheck, save_partial_results

class CharlottePermitScraper:
    def __init__(self):
        # Charlotte migrated to ArcGIS Hub - use ArcGIS REST API
        # New portal: https://data.charlottenc.gov/
        self.arcgis_url = "https://services1.arcgis.com/x4bFVvkPY6h8hYPF/arcgis/rest/services/Building_Permits/FeatureServer/0/query"
        self.permits = []
        self.seen_permit_ids = set()
        self.logger = setup_logger('charlotte')
        self.health_check = ScraperHealthCheck('charlotte')

    def scrape_permits(self, max_permits=5000, days_back=90):
        """
        Scrape Charlotte building permits using ArcGIS REST API
        
        Args:
            max_permits: Maximum number of permits to retrieve (up to 5000)
            days_back: Number of days back to search (default 90)
        """
        print(f"🏗️  Charlotte NC Construction Permits Scraper")
        print(f"=" * 60)
        print(f"Fetching up to {max_permits} permits from last {days_back} days...")
        print(f"📡 Using ArcGIS Hub REST API...")
        print()
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        print(f"Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        print()
        
        offset = 0
        batch_size = 1000
        total_fetched = 0
        consecutive_failures = 0
        max_consecutive_failures = 3

        self.logger.info(f"Starting scrape: max_permits={max_permits}, days_back={days_back}")

        while total_fetched < max_permits:
            try:
                # ArcGIS date format (Unix timestamp in milliseconds)
                start_timestamp = int(start_date.timestamp() * 1000)
                end_timestamp = int(end_date.timestamp() * 1000)

                params = {
                    'where': f"issued_date >= {start_timestamp} AND issued_date <= {end_timestamp}",
                    'outFields': 'permit_number,address,permit_type,cost,issued_date,status,objectid',
                    'returnGeometry': 'false',
                    'resultRecordCount': min(batch_size, max_permits - total_fetched),
                    'resultOffset': offset,
                    'orderByFields': 'issued_date DESC',
                    'f': 'json'
                }

                response = requests.get(self.arcgis_url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()

                if not data.get('features'):
                    self.logger.info(f"No more data at offset {offset}")
                    break

                # Reset failure counter on success
                consecutive_failures = 0

                for feature in data['features']:
                    props = feature.get('properties', {})
                    permit_id = str(props.get('permit_number') or props.get('objectid', ''))
                    
                    if permit_id not in self.seen_permit_ids:
                        self.seen_permit_ids.add(permit_id)
                        self.permits.append({
                            'permit_number': permit_id,
                            'address': props.get('address') or 'N/A',
                            'type': props.get('permit_type') or 'N/A',
                            'value': self._parse_cost(props.get('cost') or 0),
                            'issued_date': self._format_arcgis_date(props.get('issued_date')),
                            'status': props.get('status') or 'N/A'
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
                    self.logger.error(f"Too many consecutive failures ({consecutive_failures}), stopping")
                    if self.permits:
                        today = datetime.now().strftime('%Y-%m-%d')
                        filename = f'../leads/charlotte/{today}/{today}_charlotte_partial.csv'
                        save_partial_results(self.permits, filename, 'charlotte')
                    break

                offset += batch_size
                time.sleep(2)

            except Exception as e:
                consecutive_failures += 1
                self.logger.error(f"Unexpected error at offset {offset}: {e}", exc_info=True)

                if consecutive_failures >= max_consecutive_failures:
                    self.logger.error("Too many consecutive failures, stopping")
                    if self.permits:
                        today = datetime.now().strftime('%Y-%m-%d')
                        filename = f'../leads/charlotte/{today}/{today}_charlotte_partial.csv'
                        save_partial_results(self.permits, filename, 'charlotte')
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
    
    def _format_arcgis_date(self, timestamp_ms):
        """Convert ArcGIS timestamp (milliseconds) to readable date"""
        if not timestamp_ms:
            return 'N/A'
        try:
            # ArcGIS timestamps are in milliseconds, convert to seconds
            dt = datetime.fromtimestamp(timestamp_ms / 1000)
            return dt.strftime('%Y-%m-%d')
        except:
            return 'N/A'
    
    def save_to_csv(self, filename=None):
        """Save permits to CSV file"""
        if not self.permits:
            print("⚠️  No permits to save")
            return
        
        if filename is None:
            today = datetime.now().strftime('%Y-%m-%d')
            filename = f'../leads/charlotte/{today}/{today}_charlotte.csv'
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        print(f"💾 Saving to {filename}...")
        
        fieldnames = list(self.permits[0].keys())
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.permits)
        
        print(f"✅ Saved {len(self.permits)} permits to {filename}")

    def run(self):
        """Main execution with error handling and auto-recovery"""
        try:
            permits = self.scrape_permits()
            if permits:
                self.save_to_csv()
                self.logger.info(f"✅ Scraped {len(permits)} permits for charlotte")
                print(f"✅ Scraped {len(permits)} permits for charlotte")
                return permits
            else:
                self.logger.warning("❌ No permits scraped for charlotte")
                print(f"❌ No permits scraped for charlotte - will retry next run")
                return []
        except Exception as e:
            self.logger.error(f"Fatal error in scraper: {e}", exc_info=True)
            self.health_check.record_failure(str(e))
            print(f"❌ Fatal error in charlotte scraper: {e}")
            return []


# Simple functions for compatibility
def scrape_permits():
    scraper = CharlottePermitScraper()
    return scraper.scrape_permits(max_permits=5000, days_back=90)

def save_to_csv(permits):
    scraper = CharlottePermitScraper()
    scraper.permits = permits
    scraper.save_to_csv()


if __name__ == '__main__':
    scraper = CharlottePermitScraper()
    permits = scraper.scrape_permits(max_permits=5000, days_back=90)
    if permits:
        scraper.save_to_csv()
