import requests
from bs4 import BeautifulSoup
import time
import random
from datetime import datetime, timedelta
import re
import json

class BasePermitScraper:
    """Base class for all permit scrapers"""

    def __init__(self, city_name, base_url=None):
        self.city_name = city_name
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def run(self):
        """Main scraping method - override in subclasses"""
        try:
            return self.scrape_permits()
        except Exception as e:
            print(f"❌ Error scraping {self.city_name}: {e}")
            return []

    def scrape_permits(self):
        """Override this method in subclasses"""
        raise NotImplementedError("Subclasses must implement scrape_permits()")

    def clean_address(self, address):
        """Clean and standardize address format"""
        if not address:
            return "Address not available"

        # Remove extra whitespace
        address = re.sub(r'\s+', ' ', address.strip())

        # Add city and state if missing
        if self.city_name.lower() not in address.lower():
            state = self.get_state_abbrev()
            address = f"{address}, {self.city_name}, {state}"

        return address

    def get_state_abbrev(self):
        """Get state abbreviation for city"""
        state_map = {
            'nashville': 'TN', 'chattanooga': 'TN', 'knoxville': 'TN',
            'austin': 'TX', 'san antonio': 'TX', 'houston': 'TX',
            'charlotte': 'NC', 'phoenix': 'AZ', 'atlanta': 'GA',
            'seattle': 'WA', 'san diego': 'CA', 'chicago': 'IL',
            'indianapolis': 'IN', 'columbus': 'OH', 'boston': 'MA',
            'philadelphia': 'PA', 'richmond': 'VA', 'milwaukee': 'WI',
            'omaha': 'NE', 'birmingham': 'AL'
        }
        return state_map.get(self.city_name.lower(), 'TN')

    def parse_permit_value(self, value_str):
        """Parse permit value from various formats"""
        if not value_str:
            return "0"

        # Remove commas, dollar signs, etc.
        value_str = re.sub(r'[$,\s]', '', str(value_str))

        # Extract numbers
        match = re.search(r'(\d+(?:\.\d+)?)', value_str)
        if match:
            return match.group(1)
        return "0"

    def format_date(self, date_str):
        """Format date string to YYYY-MM-DD"""
        if not date_str:
            return datetime.now().strftime('%Y-%m-%d')

        # Try various date formats
        formats = [
            '%Y-%m-%d', '%m/%d/%Y', '%m-%d-%Y',
            '%B %d, %Y', '%b %d, %Y'
        ]

        for fmt in formats:
            try:
                date_obj = datetime.strptime(date_str.strip(), fmt)
                return date_obj.strftime('%Y-%m-%d')
            except ValueError:
                continue

        # If parsing fails, return today's date
        return datetime.now().strftime('%Y-%m-%d')


# ===== ORIGINAL 7 CITIES =====

class NashvillePermitScraper(BasePermitScraper):
    def __init__(self):
        super().__init__('Nashville', 'https://www.nashville.gov')

    def scrape_permits(self):
        """Scrape Nashville permits - using sample data for now"""
        # TODO: Implement actual scraping from Nashville permit portal
        # For now, return sample data
        return self._get_sample_permits()

    def _get_sample_permits(self):
        """Generate sample permits for Nashville"""
        permits = []
        base_date = datetime.now() - timedelta(days=random.randint(1, 7))

        sample_data = [
            {'number': '20250001', 'address': '123 Main St', 'type': 'NEW CONSTRUCTION', 'value': '250000'},
            {'number': '20250002', 'address': '456 Oak Ave', 'type': 'REMODEL', 'value': '75000'},
            {'number': '20250003', 'address': '789 Broadway', 'type': 'ADDITION', 'value': '125000'},
            {'number': '20250004', 'address': '321 Church St', 'type': 'REPAIR', 'value': '15000'},
            {'number': '20250005', 'address': '654 Woodland St', 'type': 'NEW CONSTRUCTION', 'value': '180000'},
        ]

        for i, data in enumerate(sample_data):
            issue_date = (base_date - timedelta(days=i)).strftime('%Y-%m-%d')
            permits.append({
                'permit_number': data['number'],
                'address': self.clean_address(data['address']),
                'permit_type': data['type'],
                'permit_value': data['value'],
                'issue_date': issue_date
            })

        return permits


class ChattanoogaPermitScraper(BasePermitScraper):
    def __init__(self):
        super().__init__('Chattanooga', 'https://www.chattanooga.gov')

    def scrape_permits(self):
        """Scrape Chattanooga permits"""
        return self._get_sample_permits()

    def _get_sample_permits(self):
        """Generate sample permits for Chattanooga"""
        permits = []
        base_date = datetime.now() - timedelta(days=random.randint(1, 7))

        sample_data = [
            {'number': '20250001', 'address': '100 Market St', 'type': 'NEW CONSTRUCTION', 'value': '320000'},
            {'number': '20250002', 'address': '200 River Rd', 'type': 'REMODEL', 'value': '95000'},
            {'number': '20250003', 'address': '300 Mountain Ave', 'type': 'ADDITION', 'value': '85000'},
            {'number': '20250004', 'address': '400 Valley Dr', 'type': 'REPAIR', 'value': '22000'},
            {'number': '20250005', 'address': '500 Lake St', 'type': 'NEW CONSTRUCTION', 'value': '275000'},
        ]

        for i, data in enumerate(sample_data):
            issue_date = (base_date - timedelta(days=i)).strftime('%Y-%m-%d')
            permits.append({
                'permit_number': data['number'],
                'address': self.clean_address(data['address']),
                'permit_type': data['type'],
                'permit_value': data['value'],
                'issue_date': issue_date
            })

        return permits


class AustinPermitScraper(BasePermitScraper):
    def __init__(self):
        super().__init__('Austin', 'https://www.austintexas.gov')

    def scrape_permits(self):
        """Scrape Austin permits"""
        return self._get_sample_permits()

    def _get_sample_permits(self):
        """Generate sample permits for Austin"""
        permits = []
        base_date = datetime.now() - timedelta(days=random.randint(1, 7))

        sample_data = [
            {'number': '20250001', 'address': '601 Congress Ave', 'type': 'NEW CONSTRUCTION', 'value': '450000'},
            {'number': '20250002', 'address': '702 6th St', 'type': 'REMODEL', 'value': '120000'},
            {'number': '20250003', 'address': '803 Barton Springs', 'type': 'ADDITION', 'value': '95000'},
            {'number': '20250004', 'address': '904 South Congress', 'type': 'REPAIR', 'value': '18000'},
            {'number': '20250005', 'address': '1005 Rainey St', 'type': 'NEW CONSTRUCTION', 'value': '380000'},
        ]

        for i, data in enumerate(sample_data):
            issue_date = (base_date - timedelta(days=i)).strftime('%Y-%m-%d')
            permits.append({
                'permit_number': data['number'],
                'address': self.clean_address(data['address']),
                'permit_type': data['type'],
                'permit_value': data['value'],
                'issue_date': issue_date
            })

        return permits


class SanAntonioPermitScraper(BasePermitScraper):
    def __init__(self):
        super().__init__('San Antonio', 'https://www.sanantonio.gov')

    def scrape_permits(self):
        """Scrape San Antonio permits"""
        return self._get_sample_permits()

    def _get_sample_permits(self):
        """Generate sample permits for San Antonio"""
        permits = []
        base_date = datetime.now() - timedelta(days=random.randint(1, 7))

        sample_data = [
            {'number': '20250001', 'address': '1101 Alamo St', 'type': 'NEW CONSTRUCTION', 'value': '290000'},
            {'number': '20250002', 'address': '1202 River Walk', 'type': 'REMODEL', 'value': '78000'},
            {'number': '20250003', 'address': '1303 Market Sq', 'type': 'ADDITION', 'value': '110000'},
            {'number': '20250004', 'address': '1404 Pearl Brewery', 'type': 'REPAIR', 'value': '25000'},
            {'number': '20250005', 'address': '1505 King William', 'type': 'NEW CONSTRUCTION', 'value': '350000'},
        ]

        for i, data in enumerate(sample_data):
            issue_date = (base_date - timedelta(days=i)).strftime('%Y-%m-%d')
            permits.append({
                'permit_number': data['number'],
                'address': self.clean_address(data['address']),
                'permit_type': data['type'],
                'permit_value': data['value'],
                'issue_date': issue_date
            })

        return permits


class HoustonPermitScraper(BasePermitScraper):
    def __init__(self):
        super().__init__('Houston', 'https://www.houstontx.gov')

    def scrape_permits(self):
        """Scrape Houston permits"""
        return self._get_sample_permits()

    def _get_sample_permits(self):
        """Generate sample permits for Houston"""
        permits = []
        base_date = datetime.now() - timedelta(days=random.randint(1, 7))

        sample_data = [
            {'number': '20250001', 'address': '1601 Texas St', 'type': 'NEW CONSTRUCTION', 'value': '520000'},
            {'number': '20250002', 'address': '1702 Main St', 'type': 'REMODEL', 'value': '135000'},
            {'number': '20250003', 'address': '1803 Post Oak', 'type': 'ADDITION', 'value': '98000'},
            {'number': '20250004', 'address': '1904 Westheimer', 'type': 'REPAIR', 'value': '32000'},
            {'number': '20250005', 'address': '2005 Montrose', 'type': 'NEW CONSTRUCTION', 'value': '410000'},
        ]

        for i, data in enumerate(sample_data):
            issue_date = (base_date - timedelta(days=i)).strftime('%Y-%m-%d')
            permits.append({
                'permit_number': data['number'],
                'address': self.clean_address(data['address']),
                'permit_type': data['type'],
                'permit_value': data['value'],
                'issue_date': issue_date
            })

        return permits


class CharlottePermitScraper(BasePermitScraper):
    def __init__(self):
        super().__init__('Charlotte', 'https://www.charlottenc.gov')

    def scrape_permits(self):
        """Scrape Charlotte permits"""
        return self._get_sample_permits()

    def _get_sample_permits(self):
        """Generate sample permits for Charlotte"""
        permits = []
        base_date = datetime.now() - timedelta(days=random.randint(1, 7))

        sample_data = [
            {'number': '20250001', 'address': '2101 Trade St', 'type': 'NEW CONSTRUCTION', 'value': '380000'},
            {'number': '20250002', 'address': '2202 Tryon St', 'type': 'REMODEL', 'value': '92000'},
            {'number': '20250003', 'address': '2303 South Blvd', 'type': 'ADDITION', 'value': '115000'},
            {'number': '20250004', 'address': '2404 Providence Rd', 'type': 'REPAIR', 'value': '19000'},
            {'number': '20250005', 'address': '2505 Kings Dr', 'type': 'NEW CONSTRUCTION', 'value': '295000'},
        ]

        for i, data in enumerate(sample_data):
            issue_date = (base_date - timedelta(days=i)).strftime('%Y-%m-%d')
            permits.append({
                'permit_number': data['number'],
                'address': self.clean_address(data['address']),
                'permit_type': data['type'],
                'permit_value': data['value'],
                'issue_date': issue_date
            })

        return permits


class PhoenixPermitScraper(BasePermitScraper):
    def __init__(self):
        super().__init__('Phoenix', 'https://www.phoenix.gov')

    def scrape_permits(self):
        """Scrape Phoenix permits"""
        return self._get_sample_permits()

    def _get_sample_permits(self):
        """Generate sample permits for Phoenix"""
        permits = []
        base_date = datetime.now() - timedelta(days=random.randint(1, 7))

        sample_data = [
            {'number': '20250001', 'address': '2601 Camelback Rd', 'type': 'NEW CONSTRUCTION', 'value': '340000'},
            {'number': '20250002', 'address': '2702 Central Ave', 'type': 'REMODEL', 'value': '88000'},
            {'number': '20250003', 'address': '2803 Mill Ave', 'type': 'ADDITION', 'value': '102000'},
            {'number': '20250004', 'address': '2904 Scottsdale Rd', 'type': 'REPAIR', 'value': '21000'},
            {'number': '20250005', 'address': '3005 Biltmore', 'type': 'NEW CONSTRUCTION', 'value': '425000'},
        ]

        for i, data in enumerate(sample_data):
            issue_date = (base_date - timedelta(days=i)).strftime('%Y-%m-%d')
            permits.append({
                'permit_number': data['number'],
                'address': self.clean_address(data['address']),
                'permit_type': data['type'],
                'permit_value': data['value'],
                'issue_date': issue_date
            })

        return permits


# ===== NEW EXPANSION CITIES =====

class AtlantaPermitScraper(BasePermitScraper):
    def __init__(self):
        super().__init__('Atlanta', 'https://www.atlantaga.gov')

    def scrape_permits(self):
        """Scrape Atlanta permits"""
        return self._get_sample_permits()

    def _get_sample_permits(self):
        """Generate sample permits for Atlanta"""
        permits = []
        base_date = datetime.now() - timedelta(days=random.randint(1, 7))

        sample_data = [
            {'number': '20250001', 'address': '3101 Peachtree St', 'type': 'NEW CONSTRUCTION', 'value': '480000'},
            {'number': '20250002', 'address': '3202 Ponce De Leon', 'type': 'REMODEL', 'value': '110000'},
            {'number': '20250003', 'address': '3303 Piedmont Ave', 'type': 'ADDITION', 'value': '125000'},
            {'number': '20250004', 'address': '3404 Virginia Ave', 'type': 'REPAIR', 'value': '28000'},
            {'number': '20250005', 'address': '3505 North Ave', 'type': 'NEW CONSTRUCTION', 'value': '395000'},
        ]

        for i, data in enumerate(sample_data):
            issue_date = (base_date - timedelta(days=i)).strftime('%Y-%m-%d')
            permits.append({
                'permit_number': data['number'],
                'address': self.clean_address(data['address']),
                'permit_type': data['type'],
                'permit_value': data['value'],
                'issue_date': issue_date
            })

        return permits


class SeattlePermitScraper(BasePermitScraper):
    def __init__(self):
        super().__init__('Seattle', 'https://www.seattle.gov')

    def scrape_permits(self):
        """Scrape Seattle permits"""
        return self._get_sample_permits()

    def _get_sample_permits(self):
        """Generate sample permits for Seattle"""
        permits = []
        base_date = datetime.now() - timedelta(days=random.randint(1, 7))

        sample_data = [
            {'number': '20250001', 'address': '3601 Pike St', 'type': 'NEW CONSTRUCTION', 'value': '620000'},
            {'number': '20250002', 'address': '3702 Pine St', 'type': 'REMODEL', 'value': '145000'},
            {'number': '20250003', 'address': '3803 Union St', 'type': 'ADDITION', 'value': '98000'},
            {'number': '20250004', 'address': '3904 Capitol Hill', 'type': 'REPAIR', 'value': '35000'},
            {'number': '20250005', 'address': '4005 Ballard Ave', 'type': 'NEW CONSTRUCTION', 'value': '510000'},
        ]

        for i, data in enumerate(sample_data):
            issue_date = (base_date - timedelta(days=i)).strftime('%Y-%m-%d')
            permits.append({
                'permit_number': data['number'],
                'address': self.clean_address(data['address']),
                'permit_type': data['type'],
                'permit_value': data['value'],
                'issue_date': issue_date
            })

        return permits


class SanDiegoPermitScraper(BasePermitScraper):
    def __init__(self):
        super().__init__('San Diego', 'https://www.sandiego.gov')

    def scrape_permits(self):
        """Scrape San Diego permits"""
        return self._get_sample_permits()

    def _get_sample_permits(self):
        """Generate sample permits for San Diego"""
        permits = []
        base_date = datetime.now() - timedelta(days=random.randint(1, 7))

        sample_data = [
            {'number': '20250001', 'address': '4101 Gaslamp Quarter', 'type': 'NEW CONSTRUCTION', 'value': '550000'},
            {'number': '20250002', 'address': '4202 Hillcrest', 'type': 'REMODEL', 'value': '128000'},
            {'number': '20250003', 'address': '4303 Mission Valley', 'type': 'ADDITION', 'value': '112000'},
            {'number': '20250004', 'address': '4404 La Jolla', 'type': 'REPAIR', 'value': '29000'},
            {'number': '20250005', 'address': '4505 Ocean Beach', 'type': 'NEW CONSTRUCTION', 'value': '475000'},
        ]

        for i, data in enumerate(sample_data):
            issue_date = (base_date - timedelta(days=i)).strftime('%Y-%m-%d')
            permits.append({
                'permit_number': data['number'],
                'address': self.clean_address(data['address']),
                'permit_type': data['type'],
                'permit_value': data['value'],
                'issue_date': issue_date
            })

        return permits


class ChicagoPermitScraper(BasePermitScraper):
    def __init__(self):
        super().__init__('Chicago', 'https://www.chicago.gov')

    def scrape_permits(self):
        """Scrape Chicago permits"""
        return self._get_sample_permits()

    def _get_sample_permits(self):
        """Generate sample permits for Chicago"""
        permits = []
        base_date = datetime.now() - timedelta(days=random.randint(1, 7))

        sample_data = [
            {'number': '20250001', 'address': '4601 Michigan Ave', 'type': 'NEW CONSTRUCTION', 'value': '720000'},
            {'number': '20250002', 'address': '4702 Wabash Ave', 'type': 'REMODEL', 'value': '165000'},
            {'number': '20250003', 'address': '4803 State St', 'type': 'ADDITION', 'value': '142000'},
            {'number': '20250004', 'address': '4904 Dearborn St', 'type': 'REPAIR', 'value': '41000'},
            {'number': '20250005', 'address': '5005 Clark St', 'type': 'NEW CONSTRUCTION', 'value': '585000'},
        ]

        for i, data in enumerate(sample_data):
            issue_date = (base_date - timedelta(days=i)).strftime('%Y-%m-%d')
            permits.append({
                'permit_number': data['number'],
                'address': self.clean_address(data['address']),
                'permit_type': data['type'],
                'permit_value': data['value'],
                'issue_date': issue_date
            })

        return permits


class IndianapolisPermitScraper(BasePermitScraper):
    def __init__(self):
        super().__init__('Indianapolis', 'https://www.indy.gov')

    def scrape_permits(self):
        """Scrape Indianapolis permits"""
        return self._get_sample_permits()

    def _get_sample_permits(self):
        """Generate sample permits for Indianapolis"""
        permits = []
        base_date = datetime.now() - timedelta(days=random.randint(1, 7))

        sample_data = [
            {'number': '20250001', 'address': '5101 Monument Circle', 'type': 'NEW CONSTRUCTION', 'value': '315000'},
            {'number': '20250002', 'address': '5202 Mass Ave', 'type': 'REMODEL', 'value': '85000'},
            {'number': '20250003', 'address': '5303 Broad Ripple', 'type': 'ADDITION', 'value': '92000'},
            {'number': '20250004', 'address': '5404 Fountain Square', 'type': 'REPAIR', 'value': '24000'},
            {'number': '20250005', 'address': '5505 Castleton', 'type': 'NEW CONSTRUCTION', 'value': '265000'},
        ]

        for i, data in enumerate(sample_data):
            issue_date = (base_date - timedelta(days=i)).strftime('%Y-%m-%d')
            permits.append({
                'permit_number': data['number'],
                'address': self.clean_address(data['address']),
                'permit_type': data['type'],
                'permit_value': data['value'],
                'issue_date': issue_date
            })

        return permits


class ColumbusPermitScraper(BasePermitScraper):
    def __init__(self):
        super().__init__('Columbus', 'https://www.columbus.gov')

    def scrape_permits(self):
        """Scrape Columbus permits"""
        return self._get_sample_permits()

    def _get_sample_permits(self):
        """Generate sample permits for Columbus"""
        permits = []
        base_date = datetime.now() - timedelta(days=random.randint(1, 7))

        sample_data = [
            {'number': '20250001', 'address': '5601 High St', 'type': 'NEW CONSTRUCTION', 'value': '295000'},
            {'number': '20250002', 'address': '5702 3rd St', 'type': 'REMODEL', 'value': '78000'},
            {'number': '20250003', 'address': '5803 S 3rd St', 'type': 'ADDITION', 'value': '88000'},
            {'number': '20250004', 'address': '5904 Parsons Ave', 'type': 'REPAIR', 'value': '21000'},
            {'number': '20250005', 'address': '6005 Frank Fetch', 'type': 'NEW CONSTRUCTION', 'value': '345000'},
        ]

        for i, data in enumerate(sample_data):
            issue_date = (base_date - timedelta(days=i)).strftime('%Y-%m-%d')
            permits.append({
                'permit_number': data['number'],
                'address': self.clean_address(data['address']),
                'permit_type': data['type'],
                'permit_value': data['value'],
                'issue_date': issue_date
            })

        return permits


class BostonPermitScraper(BasePermitScraper):
    def __init__(self):
        super().__init__('Boston', 'https://www.boston.gov')

    def scrape_permits(self):
        """Scrape Boston permits"""
        return self._get_sample_permits()

    def _get_sample_permits(self):
        """Generate sample permits for Boston"""
        permits = []
        base_date = datetime.now() - timedelta(days=random.randint(1, 7))

        sample_data = [
            {'number': '20250001', 'address': '6101 Newbury St', 'type': 'NEW CONSTRUCTION', 'value': '850000'},
            {'number': '20250002', 'address': '6202 Boylston St', 'type': 'REMODEL', 'value': '195000'},
            {'number': '20250003', 'address': '6303 Commonwealth Ave', 'type': 'ADDITION', 'value': '168000'},
            {'number': '20250004', 'address': '6404 Beacon St', 'type': 'REPAIR', 'value': '45000'},
            {'number': '20250005', 'address': '6505 Harvard Ave', 'type': 'NEW CONSTRUCTION', 'value': '720000'},
        ]

        for i, data in enumerate(sample_data):
            issue_date = (base_date - timedelta(days=i)).strftime('%Y-%m-%d')
            permits.append({
                'permit_number': data['number'],
                'address': self.clean_address(data['address']),
                'permit_type': data['type'],
                'permit_value': data['value'],
                'issue_date': issue_date
            })

        return permits


class PhiladelphiaPermitScraper(BasePermitScraper):
    def __init__(self):
        super().__init__('Philadelphia', 'https://www.phila.gov')

    def scrape_permits(self):
        """Scrape Philadelphia permits"""
        return self._get_sample_permits()

    def _get_sample_permits(self):
        """Generate sample permits for Philadelphia"""
        permits = []
        base_date = datetime.now() - timedelta(days=random.randint(1, 7))

        sample_data = [
            {'number': '20250001', 'address': '6601 Market St', 'type': 'NEW CONSTRUCTION', 'value': '425000'},
            {'number': '20250002', 'address': '6702 Chestnut St', 'type': 'REMODEL', 'value': '112000'},
            {'number': '20250003', 'address': '6803 Walnut St', 'type': 'ADDITION', 'value': '135000'},
            {'number': '20250004', 'address': '6904 Locust St', 'type': 'REPAIR', 'value': '32000'},
            {'number': '20250005', 'address': '7005 Spruce St', 'type': 'NEW CONSTRUCTION', 'value': '380000'},
        ]

        for i, data in enumerate(sample_data):
            issue_date = (base_date - timedelta(days=i)).strftime('%Y-%m-%d')
            permits.append({
                'permit_number': data['number'],
                'address': self.clean_address(data['address']),
                'permit_type': data['type'],
                'permit_value': data['value'],
                'issue_date': issue_date
            })

        return permits


class RichmondPermitScraper(BasePermitScraper):
    def __init__(self):
        super().__init__('Richmond', 'https://www.richmondgov.com')

    def scrape_permits(self):
        """Scrape Richmond permits"""
        return self._get_sample_permits()

    def _get_sample_permits(self):
        """Generate sample permits for Richmond"""
        permits = []
        base_date = datetime.now() - timedelta(days=random.randint(1, 7))

        sample_data = [
            {'number': '20250001', 'address': '7101 Main St', 'type': 'NEW CONSTRUCTION', 'value': '285000'},
            {'number': '20250002', 'address': '7202 Broad St', 'type': 'REMODEL', 'value': '75000'},
            {'number': '20250003', 'address': '7303 Grace St', 'type': 'ADDITION', 'value': '82000'},
            {'number': '20250004', 'address': '7404 Cary St', 'type': 'REPAIR', 'value': '19000'},
            {'number': '20250005', 'address': '7505 Franklin St', 'type': 'NEW CONSTRUCTION', 'value': '325000'},
        ]

        for i, data in enumerate(sample_data):
            issue_date = (base_date - timedelta(days=i)).strftime('%Y-%m-%d')
            permits.append({
                'permit_number': data['number'],
                'address': self.clean_address(data['address']),
                'permit_type': data['type'],
                'permit_value': data['value'],
                'issue_date': issue_date
            })

        return permits


class MilwaukeePermitScraper(BasePermitScraper):
    def __init__(self):
        super().__init__('Milwaukee', 'https://www.milwaukee.gov')

    def scrape_permits(self):
        """Scrape Milwaukee permits"""
        return self._get_sample_permits()

    def _get_sample_permits(self):
        """Generate sample permits for Milwaukee"""
        permits = []
        base_date = datetime.now() - timedelta(days=random.randint(1, 7))

        sample_data = [
            {'number': '20250001', 'address': '7601 Wisconsin Ave', 'type': 'NEW CONSTRUCTION', 'value': '310000'},
            {'number': '20250002', 'address': '7702 Mitchell St', 'type': 'REMODEL', 'value': '88000'},
            {'number': '20250003', 'address': '7803 Kilbourn Ave', 'type': 'ADDITION', 'value': '95000'},
            {'number': '20250004', 'address': '7904 Wells St', 'type': 'REPAIR', 'value': '23000'},
            {'number': '20250005', 'address': '8005 Brady St', 'type': 'NEW CONSTRUCTION', 'value': '275000'},
        ]

        for i, data in enumerate(sample_data):
            issue_date = (base_date - timedelta(days=i)).strftime('%Y-%m-%d')
            permits.append({
                'permit_number': data['number'],
                'address': self.clean_address(data['address']),
                'permit_type': data['type'],
                'permit_value': data['value'],
                'issue_date': issue_date
            })

        return permits


class OmahaPermitScraper(BasePermitScraper):
    def __init__(self):
        super().__init__('Omaha', 'https://www.cityofomaha.org')

    def scrape_permits(self):
        """Scrape Omaha permits"""
        return self._get_sample_permits()

    def _get_sample_permits(self):
        """Generate sample permits for Omaha"""
        permits = []
        base_date = datetime.now() - timedelta(days=random.randint(1, 7))

        sample_data = [
            {'number': '20250001', 'address': '8101 Dodge St', 'type': 'NEW CONSTRUCTION', 'value': '265000'},
            {'number': '20250002', 'address': '8202 Farnam St', 'type': 'REMODEL', 'value': '72000'},
            {'number': '20250003', 'address': '8303 Harney St', 'type': 'ADDITION', 'value': '78000'},
            {'number': '20250004', 'address': '8404 Jackson St', 'type': 'REPAIR', 'value': '18000'},
            {'number': '20250005', 'address': '8505 Leavenworth St', 'type': 'NEW CONSTRUCTION', 'value': '295000'},
        ]

        for i, data in enumerate(sample_data):
            issue_date = (base_date - timedelta(days=i)).strftime('%Y-%m-%d')
            permits.append({
                'permit_number': data['number'],
                'address': self.clean_address(data['address']),
                'permit_type': data['type'],
                'permit_value': data['value'],
                'issue_date': issue_date
            })

        return permits


class KnoxvillePermitScraper(BasePermitScraper):
    def __init__(self):
        super().__init__('Knoxville', 'https://www.knoxvilletn.gov')

    def scrape_permits(self):
        """Scrape Knoxville permits"""
        return self._get_sample_permits()

    def _get_sample_permits(self):
        """Generate sample permits for Knoxville"""
        permits = []
        base_date = datetime.now() - timedelta(days=random.randint(1, 7))

        sample_data = [
            {'number': '20250001', 'address': '8601 Gay St', 'type': 'NEW CONSTRUCTION', 'value': '225000'},
            {'number': '20250002', 'address': '8702 Kingston Pike', 'type': 'REMODEL', 'value': '65000'},
            {'number': '20250003', 'address': '8803 Cumberland Ave', 'type': 'ADDITION', 'value': '71000'},
            {'number': '20250004', 'address': '8904 Broadway', 'type': 'REPAIR', 'value': '16000'},
            {'number': '20250005', 'address': '9005 Market Sq', 'type': 'NEW CONSTRUCTION', 'value': '195000'},
        ]

        for i, data in enumerate(sample_data):
            issue_date = (base_date - timedelta(days=i)).strftime('%Y-%m-%d')
            permits.append({
                'permit_number': data['number'],
                'address': self.clean_address(data['address']),
                'permit_type': data['type'],
                'permit_value': data['value'],
                'issue_date': issue_date
            })

        return permits


class BirminghamPermitScraper(BasePermitScraper):
    def __init__(self):
        super().__init__('Birmingham', 'https://www.birminghamal.gov')

    def scrape_permits(self):
        """Scrape Birmingham permits"""
        return self._get_sample_permits()

    def _get_sample_permits(self):
        """Generate sample permits for Birmingham"""
        permits = []
        base_date = datetime.now() - timedelta(days=random.randint(1, 7))

        sample_data = [
            {'number': '20250001', 'address': '9101 20th St N', 'type': 'NEW CONSTRUCTION', 'value': '240000'},
            {'number': '20250002', 'address': '9202 Highland Ave', 'type': 'REMODEL', 'value': '68000'},
            {'number': '20250003', 'address': '9303 University Blvd', 'type': 'ADDITION', 'value': '75000'},
            {'number': '20250004', 'address': '9404 5 Points S', 'type': 'REPAIR', 'value': '20000'},
            {'number': '20250005', 'address': '9505 Crestwood Blvd', 'type': 'NEW CONSTRUCTION', 'value': '285000'},
        ]

        for i, data in enumerate(sample_data):
            issue_date = (base_date - timedelta(days=i)).strftime('%Y-%m-%d')
            permits.append({
                'permit_number': data['number'],
                'address': self.clean_address(data['address']),
                'permit_type': data['type'],
                'permit_value': data['value'],
                'issue_date': issue_date
            })

        return permits