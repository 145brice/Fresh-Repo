import os
import datetime
import time
import sys
import firebase_admin
from firebase_admin import credentials, firestore
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import warnings

# Suppress warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Environment variables
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY', 'SG....')
OWNER_EMAIL = os.getenv('OWNER_EMAIL', '145brice@gmail.com')
FROM_EMAIL = os.getenv('FROM_EMAIL', 'leads@yourdomain.com')

# Firebase setup
cred = credentials.Certificate(os.path.join(os.path.dirname(__file__), 'serviceAccountKey.json'))
firebase_admin.initialize_app(cred)
db = firestore.client()

# Cities list
CITIES = ['nashville', 'chattanooga', 'austin', 'sanantonio', 'houston', 'charlotte', 'phoenix', 'dallas']

def run_scraper(city):
    try:
        if city == 'nashville':
            from scrapers.nashville import NashvillePermitScraper
            scraper = NashvillePermitScraper()
            permits = scraper.run()
        elif city == 'chattanooga':
            from scrapers.chattanooga import ChattanoogaPermitScraper
            scraper = ChattanoogaPermitScraper()
            permits = scraper.run()
        elif city == 'austin':
            from scrapers.austin import AustinPermitScraper
            scraper = AustinPermitScraper()
            permits = scraper.run()
        elif city == 'sanantonio':
            from scrapers.sanantonio import SanAntonioPermitScraper
            scraper = SanAntonioPermitScraper()
            permits = scraper.run()
        elif city == 'houston':
            from scrapers.houston import HoustonPermitScraper
            scraper = HoustonPermitScraper()
            permits = scraper.run()
        elif city == 'charlotte':
            from scrapers.charlotte import CharlottePermitScraper
            scraper = CharlottePermitScraper()
            permits = scraper.run()
        elif city == 'phoenix':
            from scrapers.phoenix import PhoenixPermitScraper
            scraper = PhoenixPermitScraper()
            permits = scraper.run()
        elif city == 'dallas':
            from scrapers.dallas import DallasPermitScraper
            scraper = DallasPermitScraper()
            permits = scraper.run()
        else:
            print(f'No scraper for {city}')
            return

        print(f'✅ Scraped {len(permits)} permits for {city}')
    except Exception as e:
        print(f'❌ Error scraping {city}: {e}')
        # Email alert on failure
        try:
            message = Mail(
                from_email=FROM_EMAIL,
                to_emails=[OWNER_EMAIL],
                subject=f'ALERT: {city} scrape FAILED at {time.ctime()}',
                plain_text_content=f'Scraper error:\n\n{str(e)}\n\nCheck logs.'
            )
            sg = SendGridAPIClient(SENDGRID_API_KEY)
            sg.send(message)
        except Exception as email_error:
            print(f'❌ Failed to send error email: {email_error}')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 on-call.py <city>")
        print(f"Available cities: {', '.join(CITIES)}")
        sys.exit(1)
    
    city = sys.argv[1].lower()
    if city not in CITIES:
        print(f"❌ Unknown city: {city}")
        print(f"Available cities: {', '.join(CITIES)}")
        sys.exit(1)
    
    print(f"🔧 On-call scrape for {city}")
    run_scraper(city)
    print(f"✅ On-call scrape completed for {city}")