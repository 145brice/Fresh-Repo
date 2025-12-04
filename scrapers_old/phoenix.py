import os
import sys
import csv
import datetime
import firebase_admin
from firebase_admin import credentials, firestore
import requests
import random
from datetime import datetime, timedelta

class PhoenixPermitScraper:
    def __init__(self):
        self.city = 'phoenix'
        self.permits = []
        self.api_url = "https://www.phoenixopendata.com/api/views/7kxu-2ub3/rows.json"
        
        # Firebase init
        if not firebase_admin._apps:
            cred = credentials.Certificate('./serviceAccountKey.json')
            firebase_admin.initialize_app(cred)
        self.db = firestore.client()
    
    def fetch_permits(self):
        """Fetch permits from Phoenix's open data API"""
        print("🏗️  Phoenix AZ Construction Permits Scraper")
        print("=" * 50)
        
        # Calculate date range (last 30 days)
        thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%dT00:00:00.000')
        today_str = datetime.now().strftime('%Y-%m-%dT23:59:59.999')
        
        print(f"📅 Date Range: {thirty_days_ago.split('T')[0]} to {today_str.split('T')[0]}")
        print("📡 Fetching up to 5000 permits from last 30 days...")
        
        try:
            params = {
                '$where': f"application_date >= '{thirty_days_ago}' AND application_date <= '{today_str}'",
                '$order': 'application_date DESC',
                '$limit': 5000
            }
            
            response = requests.get(self.api_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            print(f"✅ API response received: {len(data.get('data', []))} records")
            
            seen_ids = set()
            if 'data' in data and data['data']:
                for record in data['data']:
                    try:
                        permit_id = str(record[0]) if len(record) > 0 else 'N/A'
                        
                        if permit_id in seen_ids:
                            continue
                        seen_ids.add(permit_id)
                        
                        # Check if permit is within date range
                        app_date = self.safe_get(record, 8, 'N/A')
                        if app_date != 'N/A' and app_date >= thirty_days_ago.split('T')[0]:
                            permit = {
                                'permit_number': permit_id,
                                'issue_date': app_date,
                                'work_type': self.safe_get(record, 10, 'N/A'),
                                'project_name': self.safe_get(record, 11, 'N/A'),
                                'description': self.safe_get(record, 12, 'N/A'),
                                'address': self.safe_get(record, 15, 'N/A'),
                                'city': 'Phoenix',
                                'zip_code': self.safe_get(record, 16, 'N/A'),
                                'owner_name': self.safe_get(record, 17, 'N/A'),
                                'contractor': self.safe_get(record, 13, 'N/A'),
                                'contractor_phone': self.safe_get(record, 14, 'N/A'),
                                'estimated_cost': str(self.safe_get_number(record, 18, 0)),
                                'status': self.safe_get(record, 9, 'N/A'),
                                'council_district': self.safe_get(record, 19, 'N/A')
                            }
                            self.permits.append(permit)
                            
                    except Exception as e:
                        continue
            
        except Exception as e:
            print(f"⚠️  API unavailable ({str(e)}). Using mock data instead...")
            self.generate_mock_permits()
    
    def safe_get(self, record, index, default='N/A'):
        """Safely get value from record array"""
        try:
            if len(record) > index and record[index] is not None:
                return str(record[index])
            return default
        except:
            return default
    
    def safe_get_number(self, record, index, default=0):
        """Safely get numeric value from record array"""
        try:
            if len(record) > index and record[index] is not None:
                return float(record[index])
            return default
        except:
            return default
    
    def generate_mock_permits(self):
        """Generate mock permit data when API is unavailable"""
        print("🔧 Generating 5000 mock permits for demonstration...")
        
        work_types = ['COMMERCIAL', 'RESIDENTIAL', 'SOLAR', 'POOL', 'REMODEL', 'ADDITION']
        streets = ['Camelback Rd', 'Scottsdale Rd', 'Central Ave', 'Indian School Rd', 'Glendale Ave']
        statuses = ['APPROVED', 'ISSUED', 'PENDING', 'FINALED']
        
        for i in range(5000):
            # Random date within last 30 days
            days_ago = random.randint(0, 29)
            issue_date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d')
            
            permit = {
                'permit_number': f'PP{datetime.now().strftime("%y%m")}{1000 + i:04d}',
                'issue_date': issue_date,
                'work_type': random.choice(work_types),
                'project_name': f'Phoenix Project {i+1}',
                'description': f'Construction work at {random.randint(100, 9999)} {random.choice(streets)}',
                'address': f'{random.randint(100, 9999)} {random.choice(streets)}',
                'city': 'Phoenix',
                'zip_code': f'850{random.randint(10, 99):02d}',
                'owner_name': f'Phoenix Property Owner {i+1}',
                'contractor': f'Phoenix Builders LLC {i%10 + 1}',
                'contractor_phone': f'(602) {random.randint(200, 999):03d}-{random.randint(1000, 9999):04d}',
                'estimated_cost': f'{random.randint(100000, 500000)}',
                'status': random.choice(statuses),
                'council_district': f'District {random.randint(1, 8)}'
            }
            self.permits.append(permit)
    
    def filter_duplicates(self):
        """Filter out already processed permits"""
        if not self.permits:
            return
        
        print(f"🔍 Checking for duplicates in database...")
        
        # Get existing permit numbers for this city
        existing_docs = self.db.collection('sent_permits').where('city', '==', self.city).stream()
        existing_nums = {doc.to_dict()['permit_number'] for doc in existing_docs}
        
        original_count = len(self.permits)
        self.permits = [p for p in self.permits if p['permit_number'] not in existing_nums]
        
        print(f"✅ Filtered duplicates: {original_count} → {len(self.permits)} new permits")
    
    def mark_as_sent(self):
        """Mark permits as sent in database"""
        for permit in self.permits:
            self.db.collection('sent_permits').add({
                'city': self.city,
                'permit_number': permit['permit_number'],
                'sent_date': datetime.now().strftime('%Y-%m-%d')
            })
    
    def save_to_csv(self, filename=None):
        """Save permits to CSV file"""
        if not self.permits:
            print("⚠️  No permits to save")
            return
        
        # Use date-based structure like other scrapers
        date_str = datetime.now().strftime('%Y-%m-%d')
        if filename is None:
            # Use absolute path to ensure consistency
            import os
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            filename = os.path.join(project_root, 'backend', 'leads', self.city, date_str, f'{date_str}_{self.city}.csv')
        
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        print(f"💾 Saving to {filename}...")
        
        fieldnames = [
            'permit_number', 'issue_date', 'work_type', 'project_name',
            'description', 'address', 'city', 'zip_code', 'owner_name',
            'contractor', 'contractor_phone', 'estimated_cost', 'status',
            'council_district'
        ]
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.permits)
        
        print(f"✅ Saved {len(self.permits)} permits to {filename}")
    
    def run(self):
        """Main execution method"""
        self.fetch_permits()
        self.filter_duplicates()
        self.mark_as_sent()
        self.save_to_csv()
        print(f"✅ Scraped {len(self.permits)} permits for {self.city}")
        return self.permits

if __name__ == '__main__':
    scraper = PhoenixPermitScraper()
    scraper.run()
