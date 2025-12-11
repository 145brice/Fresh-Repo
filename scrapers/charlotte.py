from datetime import datetime, timedelta
import requests
import csv
import time
import os
from .utils import retry_with_backoff, setup_logger, ScraperHealthCheck, save_partial_results, validate_state

class CharlottePermitScraper:
    def __init__(self):
        # Charlotte/Mecklenburg County - use correct ArcGIS REST API
        # Mecklenburg County Data Dashboard API
        self.arcgis_url = "https://services.arcgis.com/lQySeXwbBg53XWDi/arcgis/rest/services/building_permits/FeatureServer/0/query"
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
                # Format dates for ArcGIS (YYYY-MM-DD format for string comparison)
                start_date_str = start_date.strftime('%Y-%m-%d')
                end_date_str = end_date.strftime('%Y-%m-%d')

                params = {
                    'where': f"IssuedDate >= '{start_date_str}' AND IssuedDate <= '{end_date_str}'",
                    'outFields': 'PermitNum,OriginalAddress1,OriginalCity,Type,IssuedDate,StatusCurrent,Description,OBJECTID',
                    'returnGeometry': 'false',
                    'resultRecordCount': min(batch_size, max_permits - total_fetched),
                    'resultOffset': offset,
                    'orderByFields': 'IssuedDateDtm DESC',
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
                    attrs = feature.get('attributes', {})
                    permit_id = str(attrs.get('PermitNum') or attrs.get('OBJECTID', ''))

                    if permit_id not in self.seen_permit_ids:
                        self.seen_permit_ids.add(permit_id)
                        # Build full address - ALWAYS use Charlotte, NC (autofix bad API city names)
                        address = attrs.get('OriginalAddress1', 'N/A')
                        if address != 'N/A':
                            address = f"{address}, Charlotte, NC"

                        # STATE VALIDATION: Only accept North Carolina addresses
                        if not validate_state(address, 'charlotte', self.logger):
                            continue  # Skip this record - wrong state

                        self.permits.append({
                            'permit_number': permit_id,
                            'address': address,
                            'type': attrs.get('Type') or 'N/A',
                            'value': '',  # Not provided in this API
                            'issued_date': attrs.get('IssuedDate') or 'N/A',
                            'status': attrs.get('StatusCurrent') or 'N/A',
                            'description': attrs.get('Description') or ''
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
    
    def _format_arcgis_date(self, date_string):
        """Date is already in YYYY-MM-DD format, just validate it"""
        if not date_string or date_string == 'N/A':
            return 'N/A'
        return date_string
    
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
