from datetime import datetime, timedelta
import requests
import csv
import time
import os
import re
from utils import retry_with_backoff, setup_logger, ScraperHealthCheck, save_partial_results, validate_state
from base_scraper import BaseScraper

class HoustonScraper(BaseScraper):
    def __init__(self):
        super().__init__('houston')
        # Primary Houston endpoints (may change, auto-recovery will find new ones)
        self.endpoints = [
            {
                'url': 'https://services.arcgis.com/NummVBqZSIJKUeVR/arcgis/rest/services/SF_2015_to_2021/FeatureServer/1/query',
                'type': 'arcgis_api',
                'name': 'Single Family Permits'
            },
            {
                'url': 'https://services.arcgis.com/NummVBqZSIJKUeVR/arcgis/rest/services/MF_2015_to_2021/FeatureServer/0/query',
                'type': 'arcgis_api',
                'name': 'Multi Family Permits'
            }
        ]
        # Backup endpoints in case primary ones fail
        self.backup_endpoints = [
            'https://houston-mycity.opendata.arcgis.com/',
            'https://cohgis.houstontx.gov/cohgis/',
            'https://www.houstonpermittingcenter.org/'
        ]
        self.permits = []
        self.seen_permit_ids = set()
        self.endpoint_health = {}  # Track endpoint reliability

    @retry_with_backoff(max_retries=3, initial_delay=2, exceptions=(requests.RequestException,))
    def _fetch_arcgis_batch(self, url, params):
        """Fetch a single ArcGIS batch with retry logic"""
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def _auto_discover_endpoints(self):
        """Auto-discover new ArcGIS endpoints if current ones fail"""
        self.logger.info("🔍 Auto-discovering new Houston permit endpoints...")

        discovered_endpoints = []

        for backup_url in self.backup_endpoints:
            try:
                self.logger.debug(f"Checking backup source: {backup_url}")
                response = requests.get(backup_url, timeout=10)

                if response.status_code == 200:
                    # Look for ArcGIS service URLs in the page content
                    content = response.text

                    # Search for ArcGIS REST service patterns
                    arcgis_patterns = [
                        r'https://services\.arcgis\.com/[^/]+/arcgis/rest/services/[^/]+/FeatureServer/\d+/query',
                        r'https://[^/]+\.arcgis\.com/[^/]+/arcgis/rest/services/[^/]+/FeatureServer/\d+/query'
                    ]

                    found_urls = []
                    for pattern in arcgis_patterns:
                        matches = re.findall(pattern, content)
                        found_urls.extend(matches)

                    # Remove duplicates and filter for permit-related services
                    unique_urls = list(set(found_urls))
                    permit_urls = [url for url in unique_urls if any(term in url.lower() for term in ['permit', 'building', 'construction', 'sf_', 'mf_'])]

                    if permit_urls:
                        self.logger.info(f"Found {len(permit_urls)} potential permit endpoints at {backup_url}")
                        for url in permit_urls[:2]:  # Limit to 2 per source
                            discovered_endpoints.append({
                                'url': url,
                                'type': 'arcgis_api',
                                'name': f'Auto-discovered ({url.split("/")[-4]})',
                                'auto_discovered': True
                            })

            except Exception as e:
                self.logger.debug(f"Failed to check {backup_url}: {e}")
                continue

        return discovered_endpoints

    def get_permits(self, max_permits=5000, days_back=90):
        """Scrape Houston permits with auto-recovery across multiple endpoints"""
        self.logger.info("🏗️  Houston TX Construction Permits Scraper")
        print(f"🏗️  Houston TX Construction Permits Scraper")
        print(f"=" * 60)
        print(f"📅 Date Range: {(datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}")
        print(f"📡 Trying multiple Houston data sources...")

        total_permits_before = len(self.permits)
        permits_per_endpoint = max_permits // len(self.endpoints)  # Distribute limit across endpoints

        successful_endpoints = 0

        # Try each primary endpoint first
        for i, endpoint in enumerate(self.endpoints, 1):
            self.logger.info(f"Attempt {i}/{len(self.endpoints)}: {endpoint['type']}")
            print(f"\n🔍 Attempt {i}/{len(self.endpoints)}: {endpoint['type']}")

            try:
                if endpoint['type'] == 'arcgis_api':
                    endpoint_permits = self._try_arcgis_api(endpoint['url'], permits_per_endpoint, days_back, endpoint.get('name', 'Unknown'))
                    if endpoint_permits:
                        self.permits.extend(endpoint_permits)
                        successful_endpoints += 1
                        self.endpoint_health[endpoint['url']] = True  # Mark as healthy
                        self.logger.info(f"✅ {endpoint.get('name', 'Unknown')} endpoint succeeded! Added {len(endpoint_permits)} permits to collection")
                        print(f"✅ {endpoint.get('name', 'Unknown')} endpoint succeeded!")
                    else:
                        self.endpoint_health[endpoint['url']] = False  # Mark as unhealthy
                        print(f"   ❌ {endpoint.get('name', 'Unknown')} endpoint failed or returned no data")

            except Exception as e:
                self.endpoint_health[endpoint['url']] = False  # Mark as unhealthy
                self.logger.warning(f"Endpoint failed: {e}")
                print(f"   ❌ Failed: {e}")
                continue

        # If we got less than expected permits, try auto-discovery
        total_new_permits = len(self.permits) - total_permits_before
        min_expected_permits = max_permits * 0.1  # At least 10% of expected

        if total_new_permits < min_expected_permits and successful_endpoints < len(self.endpoints):
            self.logger.warning(f"Low permit count ({total_new_permits}), attempting auto-discovery...")
            print(f"\n🔄 Low permit count detected, attempting auto-discovery of new endpoints...")

            discovered_endpoints = self._auto_discover_endpoints()
            if discovered_endpoints:
                # Update endpoints for future runs
                self._update_endpoints_if_needed(discovered_endpoints)
                
                # Try discovered endpoints
                for endpoint in discovered_endpoints:
                    if total_new_permits >= max_permits:
                        break

                    try:
                        remaining_permits = max_permits - total_new_permits
                        endpoint_permits = self._try_arcgis_api(endpoint['url'], remaining_permits, days_back, endpoint.get('name', 'Unknown'))
                        if endpoint_permits:
                            self.permits.extend(endpoint_permits)
                            total_new_permits = len(self.permits) - total_permits_before
                            self.logger.info(f"✅ Auto-discovered {endpoint.get('name', 'Unknown')} endpoint succeeded! Added {len(endpoint_permits)} permits")
                            print(f"✅ Auto-discovered endpoint succeeded!")
                    except Exception as e:
                        self.logger.debug(f"Auto-discovered endpoint failed: {e}")
                        continue

        total_new_permits = len(self.permits) - total_permits_before

        if total_new_permits > 0:
            self.logger.info(f"✅ Success! Collected {total_new_permits} total permits from {successful_endpoints} endpoints")
            print(f"✅ Successfully collected {total_new_permits} total permits from all endpoints!")
            return self.permits
        else:
            # All endpoints failed
            self.logger.error("All Houston endpoints failed - auto-recovery unsuccessful")
            print(f"\n⚠️  All Houston endpoints failed - will retry next run")
            return []
    
    def _try_arcgis_api(self, url, max_permits_per_endpoint, days_back, endpoint_name="ArcGIS API"):
        """Try ArcGIS REST API with auto-recovery"""
        offset = 0
        batch_size = 1000
        consecutive_failures = 0
        max_consecutive_failures = 3
        endpoint_permits = []

        while len(endpoint_permits) < max_permits_per_endpoint:
            try:
                params = {
                    'where': '1=1',
                    'outFields': '*',
                    'returnGeometry': 'false',
                    'resultOffset': offset,
                    'resultRecordCount': min(batch_size, max_permits_per_endpoint - len(endpoint_permits)),
                    'f': 'json'
                }

                data = self._fetch_arcgis_batch(url, params)

                if 'features' not in data or not data['features']:
                    self.logger.info(f"No more data at offset {offset}")
                    break

                # Reset failure counter on success
                consecutive_failures = 0

                for feature in data['features']:
                    attrs = feature.get('attributes', {})
                    
                    # Auto-detect field mapping with fallback logic
                    permit_id = self._extract_permit_id(attrs, endpoint_name)
                    date_value = self._extract_date_value(attrs, endpoint_name)
                    
                    if permit_id not in self.seen_permit_ids:
                        self.seen_permit_ids.add(permit_id)

                        # Extract address first
                        address = attrs.get('ADDRESS') or attrs.get('Address') or attrs.get('address') or 'N/A'

                        # STATE VALIDATION: Only accept Texas addresses
                        if not validate_state(address, 'houston', self.logger):
                            continue  # Skip this record - wrong state

                        endpoint_permits.append({
                            'permit_number': permit_id,
                            'address': address,
                            'permit_type': self._extract_permit_type(attrs),
                            'description': self._extract_description(attrs),
                            'date': self._format_date(date_value),
                            'city': 'Houston'
                        })

                self.logger.debug(f"Fetched batch at offset {offset}: {len(data['features'])} records")

                if len(data['features']) < batch_size:
                    break
                offset += batch_size
                time.sleep(0.5)

            except requests.RequestException as e:
                consecutive_failures += 1
                self.logger.warning(f"Request error at offset {offset}: {e}")

                if consecutive_failures >= max_consecutive_failures:
                    self.logger.error(f"Too many consecutive failures, stopping ArcGIS API")
                    break

                offset += batch_size
                time.sleep(2)

            except Exception as e:
                consecutive_failures += 1
                self.logger.error(f"Unexpected error at offset {offset}: {e}", exc_info=True)

                if consecutive_failures >= max_consecutive_failures:
                    self.logger.error(f"Too many consecutive failures, stopping ArcGIS API")
                    break

                offset += batch_size
                time.sleep(2)

        return endpoint_permits
    
    def _extract_permit_id(self, attrs, endpoint_name):
        """Auto-detect permit ID field with fallbacks"""
        # Try known field names in order of preference
        id_fields = ['OBJECTID', 'OBJECTID_1', 'ObjectID', 'PERMIT_ID', 'Permit_ID', 'permit_id', 'ID']
        
        for field in id_fields:
            value = attrs.get(field)
            if value is not None and str(value).strip():
                return str(value).strip()
        
        # Fallback: create hash from other fields
        key_fields = ['ADDRESS', 'F_PROJ_NAME', 'FCC__Desc']
        key_string = '|'.join(str(attrs.get(field, '')) for field in key_fields)
        return str(hash(key_string))[-8:]  # Use last 8 chars of hash
    
    def _extract_date_value(self, attrs, endpoint_name):
        """Auto-detect date field with fallbacks"""
        # Try known date field names
        date_fields = ['Sold_Date', 'Sold_Date_SZ', 'DATE', 'Date', 'PERMIT_DATE', 'Permit_Date', 'ISSUED_DATE']
        
        for field in date_fields:
            value = attrs.get(field)
            if value is not None:
                return value
        
        return None
    
    def _extract_permit_type(self, attrs):
        """Auto-detect permit type field"""
        type_fields = ['FCC__Desc', 'F_PERMIT_TY', 'PERMIT_TYPE', 'Permit_Type', 'TYPE', 'Type']
        
        for field in type_fields:
            value = attrs.get(field)
            if value and str(value).strip():
                return str(value).strip()
        
        return 'N/A'
    
    def _update_endpoints_if_needed(self, discovered_endpoints):
        """Update primary endpoints if auto-discovered ones are more reliable"""
        if not discovered_endpoints:
            return
        
        # Check if we should replace failing endpoints
        failing_endpoints = [url for url, healthy in self.endpoint_health.items() if healthy is False]
        
        if len(failing_endpoints) > 0:
            self.logger.info(f"Replacing {len(failing_endpoints)} failing endpoints with auto-discovered ones")
            
            # Remove failing endpoints
            self.endpoints = [e for e in self.endpoints if e['url'] not in failing_endpoints]
            
            # Add discovered endpoints (up to the number we removed)
            for endpoint in discovered_endpoints[:len(failing_endpoints)]:
                self.endpoints.append(endpoint)
            
            self.logger.info(f"Updated endpoints. New count: {len(self.endpoints)}")
    
    def _parse_cost(self, value):
        try:
            return float(str(value).replace('$', '').replace(',', '')) if value else 0
        except:
            return 0
    
    def _format_date(self, timestamp):
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
    scraper = HoustonScraper()
    permits, filepath = scraper.run()
    print(f"Scraped {len(permits)} permits, saved to {filepath}")
