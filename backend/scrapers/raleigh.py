from datetime import datetime, timedelta
import requests
import csv
import time
import os
from .utils import retry_with_backoff, setup_logger, ScraperHealthCheck, save_partial_results

class RaleighPermitScraper:
    def __init__(self):
        # Raleigh ArcGIS FeatureServer endpoint for building permits (past 31 days)
        self.endpoints = [
            {
                'name': 'Raleigh Building Permits Past 31 Days',
                'url': 'https://services.arcgis.com/v400IkDOw1ad7Yad/arcgis/rest/services/Building_Permits_Past_31_Days/FeatureServer/0/query',
                'type': 'arcgis_featureserver'
            },
            {
                'name': 'Raleigh Building Permits Full',
                'url': 'https://services.arcgis.com/v400IkDOw1ad7Yad/arcgis/rest/services/Building_Permits/FeatureServer/0/query',
                'type': 'arcgis_featureserver'
            }
        ]
        self.permits = []
        self.seen_permit_ids = set()
        self.logger = setup_logger('raleigh')
        self.health_check = ScraperHealthCheck('raleigh')

    @retry_with_backoff(max_retries=3, initial_delay=2, exceptions=(requests.RequestException,))
    def _fetch_arcgis_batch(self, params, endpoint_url):
        """Fetch ArcGIS data with retry logic"""
        response = requests.get(endpoint_url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def scrape_permits(self, max_permits=5000, days_back=31):
        """Scrape Raleigh permits with auto-recovery across multiple endpoints"""
        self.logger.info("🏗️  Raleigh NC Construction Permits Scraper")
        print(f"🏗️  Raleigh NC Construction Permits Scraper")
        print(f"=" * 60)
        print(f"📡 Trying multiple Raleigh endpoints with auto-recovery...")

        # Try each endpoint in sequence until one works
        for endpoint_config in self.endpoints:
            endpoint_url = endpoint_config['url']
            endpoint_name = endpoint_config['name']

            self.logger.info(f"Trying {endpoint_name}")
            print(f"\n🔍 Trying: {endpoint_name}...")

            try:
                self.permits = []  # Reset for each endpoint
                self.seen_permit_ids = set()
                offset = 0
                batch_size = 1000
                consecutive_failures = 0
                max_consecutive_failures = 3

                while len(self.permits) < max_permits:
                    try:
                        params = {
                            'where': '1=1',  # Get all permits (endpoint already filters to recent)
                            'outFields': 'permitnum,issueddate,estprojectcost,originaladdress1,workclass,permitclassmapped,proposedworkdescription,contractorcompanyname,statuscurrentmapped',
                            'returnGeometry': 'false',
                            'resultRecordCount': min(batch_size, max_permits - len(self.permits)),
                            'resultOffset': offset,
                            'orderByFields': 'issueddate DESC',
                            'f': 'json'
                        }

                        response = self._fetch_arcgis_batch(params, endpoint_url)
                        data = response

                        # Check for ArcGIS error
                        if 'error' in data:
                            self.logger.warning(f"{endpoint_name} returned error: {data['error']}")
                            print(f"   ❌ {endpoint_name} error: {data['error'].get('message', 'Unknown')}")
                            break

                        if not data.get('features'):
                            self.logger.info(f"No more data at offset {offset}")
                            break

                        # Reset failure counter on success
                        consecutive_failures = 0

                        for feature in data['features']:
                            attrs = feature.get('attributes', {})
                            permit_id = str(attrs.get('permitnum', ''))

                            if permit_id and permit_id not in self.seen_permit_ids:
                                self.seen_permit_ids.add(permit_id)
                                self.permits.append({
                                    'permit_number': permit_id,
                                    'address': attrs.get('originaladdress1') or 'N/A',
                                    'type': attrs.get('workclass') or attrs.get('permitclassmapped') or 'N/A',
                                    'value': self._parse_cost(attrs.get('estprojectcost') or 0),
                                    'issued_date': self._format_arcgis_date(attrs.get('issueddate')),
                                    'status': attrs.get('statuscurrentmapped') or 'N/A',
                                    'description': attrs.get('proposedworkdescription') or '',
                                    'contractor': attrs.get('contractorcompanyname') or 'N/A'
                                })

                        print(f"✓ Fetched {len(self.permits)} permits so far...")

                        if len(data['features']) < batch_size:
                            break
                        offset += batch_size
                        time.sleep(0.5)

                    except requests.RequestException as e:
                        consecutive_failures += 1
                        self.logger.warning(f"Batch error at offset {offset}: {e}")

                        if consecutive_failures >= max_consecutive_failures:
                            self.logger.error(f"Too many consecutive failures on {endpoint_name}")
                            print(f"   ❌ Too many failures on {endpoint_name}")
                            break

                        offset += batch_size
                        time.sleep(2)

                # If we got permits from this endpoint, we're done!
                if len(self.permits) > 0:
                    self.logger.info(f"✅ Success! Got {len(self.permits)} permits from {endpoint_name}")
                    self.health_check.record_success(len(self.permits))
                    print(f"\n✅ Success! Got {len(self.permits)} Raleigh permits from {endpoint_name}")
                    return self.permits

            except Exception as e:
                self.logger.warning(f"{endpoint_name} failed: {e}")
                print(f"   ❌ {endpoint_name} failed: {str(e)[:60]}...")
                # Continue to next endpoint
                continue

        # If we get here, all endpoints failed
        self.logger.error("All Raleigh endpoints failed")
        self.health_check.record_failure("All endpoints failed")
        print(f"\n❌ All Raleigh endpoints failed - will retry next run")
        return []

    def _parse_cost(self, value):
        try:
            cost = float(value) if value else 0
            return f"${cost:,.2f}"
        except:
            return "$0.00"

    def _format_arcgis_date(self, timestamp_ms):
        """Convert ArcGIS timestamp (milliseconds) to date string"""
        if not timestamp_ms:
            return 'N/A'
        try:
            # ArcGIS timestamps are in milliseconds since Unix epoch
            timestamp_s = int(timestamp_ms) / 1000
            return datetime.fromtimestamp(timestamp_s).strftime('%Y-%m-%d')
        except:
            return 'N/A'

    def save_to_csv(self, filename=None):
        if not self.permits:
            return
        if filename is None:
            today = datetime.now().strftime('%Y-%m-%d')
            filename = f'../leads/raleigh/{today}/{today}_raleigh.csv'
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
                self.logger.info(f"✅ Scraped {len(permits)} permits for raleigh")
                print(f"✅ Scraped {len(permits)} permits for raleigh")
                return permits
            else:
                self.logger.warning("❌ No permits scraped for raleigh")
                print(f"❌ No permits scraped for raleigh - will retry next run")
                return []
        except Exception as e:
            self.logger.error(f"Fatal error in scraper: {e}", exc_info=True)
            self.health_check.record_failure(str(e))
            print(f"❌ Fatal error in raleigh scraper: {e}")
            return []