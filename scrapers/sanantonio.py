from datetime import datetime, timedelta
import requests
import csv
import io
import time
import os
from .utils import retry_with_backoff, setup_logger, ScraperHealthCheck, save_partial_results, validate_state

class SanAntonioPermitScraper:
    def __init__(self):
        # San Antonio uses CSV downloads - updated URLs
        self.csv_urls = [
            'https://data.sanantonio.gov/dataset/05012dcb-ba1b-4ade-b5f3-7403bc7f52eb/resource/c21106f9-3ef5-4f3a-8604-f992b4db7512/download/permits_issued.csv',
            'https://data.sanantonio.gov/dataset/05012dcb-ba1b-4ade-b5f3-7403bc7f52eb/resource/fbb7202e-c6c1-475b-849e-c5c2cfb65833/download/accelasubmitpermitsextract.csv',
        ]
        # Also try ArcGIS
        self.arcgis_urls = [
            'https://services.arcgis.com/g1fRTDLeMgspWrYp/arcgis/rest/services/PermitApplications/FeatureServer/0/query',
            'https://opendata-cosagis.opendata.arcgis.com/api/v3/datasets',
        ]
        self.permits = []
        self.seen_permit_ids = set()
        self.logger = setup_logger('sanantonio')
        self.health_check = ScraperHealthCheck('sanantonio')

    @retry_with_backoff(max_retries=3, initial_delay=2, exceptions=(requests.RequestException,))
    def _fetch_csv(self, url):
        """Fetch CSV data with retry logic"""
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        return response.content.decode('utf-8')

    @retry_with_backoff(max_retries=3, initial_delay=2, exceptions=(requests.RequestException,))
    def _fetch_arcgis(self, url, params):
        """Fetch ArcGIS data with retry logic"""
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def scrape_permits(self, max_permits=5000, days_back=90):
        """Scrape San Antonio permits with auto-recovery across multiple sources"""
        self.logger.info("🏗️  San Antonio TX Construction Permits Scraper")
        print(f"🏗️  San Antonio TX Construction Permits Scraper")
        print(f"=" * 60)
        print(f"📅 Date Range: {(datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}")
        print(f"📡 San Antonio uses CSV downloads...")

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        # Try CSV downloads first
        for csv_url in self.csv_urls:
            self.logger.info(f"Trying CSV: {csv_url[:60]}...")
            print(f"\n🔍 Trying CSV: {csv_url[:60]}...")
            try:
                content = self._fetch_csv(csv_url)
                csv_reader = csv.DictReader(io.StringIO(content))

                consecutive_failures = 0
                max_consecutive_failures = 10  # More lenient for CSV row parsing

                for row in csv_reader:
                    if len(self.permits) >= max_permits:
                        break

                    # Parse date from CSV - San Antonio uses "DATE ISSUED" column
                    issue_date_str = row.get('DATE ISSUED') or row.get('DATE SUBMITTED') or ''
                    try:
                        if issue_date_str:
                            issue_date = datetime.strptime(issue_date_str[:10], '%Y-%m-%d')
                            if start_date <= issue_date <= end_date:
                                permit_id = row.get('PERMIT #') or ''
                                if permit_id and permit_id not in self.seen_permit_ids:
                                    self.seen_permit_ids.add(permit_id)
                                    # Build address - ALWAYS use San Antonio, TX (autofix)
                                    raw_address = row.get('ADDRESS') or 'N/A'
                                    if raw_address != 'N/A' and 'San Antonio' not in raw_address:
                                        address = f"{raw_address}, San Antonio, TX"
                                    else:
                                        address = raw_address

                                    # STATE VALIDATION: Only accept Texas addresses
                                    if not validate_state(address, 'sanantonio', self.logger):
                                        continue  # Skip this record - wrong state

                                    self.permits.append({
                                        'permit_number': permit_id,
                                        'address': address,
                                        'type': row.get('PERMIT TYPE') or 'N/A',
                                        'value': self._parse_cost(row.get('DECLARED VALUATION') or 0),
                                        'issued_date': issue_date.strftime('%Y-%m-%d'),
                                        'status': 'Issued'
                                    })
                                    # Reset failure counter on success
                                    consecutive_failures = 0
                    except Exception as e:
                        consecutive_failures += 1
                        if consecutive_failures >= max_consecutive_failures:
                            self.logger.warning(f"Too many row parsing failures, moving to next source")
                            break
                        continue

                if len(self.permits) > 0:
                    self.logger.info(f"✅ Success! Got {len(self.permits)} permits from CSV")
                    self.health_check.record_success(len(self.permits))
                    print(f"✅ Success! Got {len(self.permits)} permits from CSV")
                    return self.permits

            except Exception as e:
                self.logger.warning(f"CSV failed: {e}")
                print(f"   ❌ CSV failed: {e}")
                continue

        # Try ArcGIS as backup
        for arcgis_url in self.arcgis_urls:
            self.logger.info(f"Trying ArcGIS: {arcgis_url[:60]}...")
            print(f"\n🔍 Trying ArcGIS: {arcgis_url[:60]}...")
            try:
                params = {
                    'where': '1=1',
                    'outFields': '*',
                    'returnGeometry': 'false',
                    'resultRecordCount': min(1000, max_permits),
                    'f': 'json'
                }
                data = self._fetch_arcgis(arcgis_url, params)

                if 'features' in data:
                    for feature in data['features'][:max_permits]:
                        props = feature.get('properties', {})
                        permit_id = str(props.get('permit_number') or props.get('PermitNumber') or props.get('OBJECTID', ''))

                        if permit_id not in self.seen_permit_ids:
                            self.seen_permit_ids.add(permit_id)
                            self.permits.append({
                                'permit_number': permit_id,
                                'address': props.get('address') or 'N/A',
                                'type': props.get('permit_type') or 'N/A',
                                'value': self._parse_cost(props.get('cost') or 0),
                                'issued_date': self._format_date(props.get('issue_date')),
                                'status': props.get('status') or 'N/A'
                            })

                    if len(self.permits) > 0:
                        self.logger.info(f"✅ Success! Got {len(self.permits)} permits from ArcGIS")
                        self.health_check.record_success(len(self.permits))
                        print(f"✅ Success! Got {len(self.permits)} permits from ArcGIS")
                        return self.permits

            except Exception as e:
                self.logger.warning(f"ArcGIS failed: {e}")
                print(f"   ❌ ArcGIS failed: {e}")
                continue

        # All sources failed
        self.logger.error("All San Antonio sources failed")
        self.health_check.record_failure("All sources failed")
        print(f"\n⚠️  All San Antonio sources failed - will retry next run")
        return []
    
    def _parse_cost(self, value):
        try:
            return float(str(value).replace('$', '').replace(',', '')) if value else 0
        except:
            return 0
    
    def _format_date(self, timestamp):
        if not timestamp:
            return 'N/A'
        try:
            return datetime.fromtimestamp(int(timestamp) / 1000).strftime('%Y-%m-%d')
        except:
            return str(timestamp)[:10]
    
    def save_to_csv(self, filename=None):
        if not self.permits:
            return
        if filename is None:
            today = datetime.now().strftime('%Y-%m-%d')
            filename = f'../leads/sanantonio/{today}/{today}_sanantonio.csv'
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
                self.logger.info(f"✅ Scraped {len(permits)} permits for sanantonio")
                print(f"✅ Scraped {len(permits)} permits for sanantonio")
                return permits
            else:
                self.logger.warning("❌ No permits scraped for sanantonio")
                print(f"❌ No permits scraped for sanantonio - will retry next run")
                return []
        except Exception as e:
            self.logger.error(f"Fatal error in scraper: {e}", exc_info=True)
            self.health_check.record_failure(str(e))
            print(f"❌ Fatal error in sanantonio scraper: {e}")
            return []

def scrape_permits():
    return SanAntonioPermitScraper().scrape_permits()

def save_to_csv(permits):
    scraper = SanAntonioPermitScraper()
    scraper.permits = permits
    scraper.save_to_csv()
