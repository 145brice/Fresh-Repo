import os
import datetime
import time
import random
import logging
import traceback
from collections import defaultdict
import firebase_admin
from firebase_admin import credentials, firestore
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import warnings

# Suppress warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(__file__), 'logs/scheduler.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('scheduler')

# Environment variables
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY', 'SG....')
OWNER_EMAIL = os.getenv('OWNER_EMAIL', '145brice@gmail.com')
FROM_EMAIL = os.getenv('FROM_EMAIL', 'leads@yourdomain.com')

# Firebase setup
try:
    cred = credentials.Certificate(os.path.join(os.path.dirname(__file__), 'serviceAccountKey.json'))
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    logger.info("✅ Firebase initialized successfully")
except Exception as e:
    logger.error(f"⚠️  Firebase initialization failed: {e}")
    db = None

# Cities list with priority (higher = more important)
CITIES = {
    'nashville': 3,
    'chattanooga': 2,
    'austin': 3,
    'sanantonio': 2,
    'houston': 3,
    'charlotte': 3,
    'phoenix': 3
}

# Track failures per city
failure_counts = defaultdict(int)
last_success = {}

def send_alert_email(city, error, failure_count):
    """Send email alert for scraper failures"""
    try:
        # Only send email every 3rd failure to avoid spam
        if failure_count % 3 != 0:
            return

        message = Mail(
            from_email=FROM_EMAIL,
            to_emails=[OWNER_EMAIL],
            subject=f'ALERT: {city} scraper failing (attempt #{failure_count})',
            plain_text_content=f'''
Scraper Alert for {city.upper()}

Failure Count: {failure_count}
Last Success: {last_success.get(city, 'Never')}
Time: {time.ctime()}

Error:
{str(error)}

Stack Trace:
{traceback.format_exc()}

The scraper will automatically retry on the next scheduled run.
            '''
        )
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        sg.send(message)
        logger.info(f"📧 Alert email sent for {city}")
    except Exception as email_error:
        logger.error(f'Failed to send email alert: {email_error}')

def run_scraper(city, max_retries=2):
    """
    Run scraper with auto-recovery and retries

    Args:
        city: City name to scrape
        max_retries: Number of retry attempts if initial scrape fails
    """
    for attempt in range(max_retries + 1):
        try:
            logger.info(f"🚀 Starting {city} scraper (attempt {attempt + 1}/{max_retries + 1})")

            # Use the new .run() method which has built-in error handling
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
            else:
                logger.error(f'No scraper configured for {city}')
                return False

            # Check if we got permits
            if permits and len(permits) > 0:
                logger.info(f'✅ Successfully scraped {len(permits)} permits for {city}')
                print(f'✅ Scraped {len(permits)} permits for {city}')

                # Reset failure counter on success
                failure_counts[city] = 0
                last_success[city] = time.ctime()
                return True
            else:
                logger.warning(f'⚠️  {city} scraper returned no permits (attempt {attempt + 1})')

                if attempt < max_retries:
                    wait_time = 5 * (attempt + 1)  # Increasing wait time
                    logger.info(f"Retrying {city} in {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                else:
                    # Max retries reached
                    failure_counts[city] += 1
                    logger.error(f'❌ {city} scraper failed after {max_retries + 1} attempts')
                    send_alert_email(city, "No permits returned after retries", failure_counts[city])
                    return False

        except Exception as e:
            logger.error(f'❌ Error scraping {city} (attempt {attempt + 1}): {e}')
            logger.debug(traceback.format_exc())

            if attempt < max_retries:
                wait_time = 5 * (attempt + 1)
                logger.info(f"Retrying {city} in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                # Max retries reached
                failure_counts[city] += 1
                send_alert_email(city, str(e), failure_counts[city])
                return False

    return False

def get_next_city():
    """
    Select next city to scrape based on:
    1. Priority (higher priority cities scraped more often)
    2. Time since last success (prioritize cities that haven't succeeded recently)
    3. Failure count (deprioritize repeatedly failing cities, but still retry)
    """
    import random

    # Create weighted list based on priority and failure count
    weighted_cities = []
    for city, priority in CITIES.items():
        # Reduce weight for cities with failures, but never to zero
        failure_penalty = max(1, 5 - failure_counts[city])
        weight = priority * failure_penalty
        weighted_cities.extend([city] * weight)

    return random.choice(weighted_cities)

def print_status():
    """Print current scheduler status"""
    logger.info("=" * 60)
    logger.info("📊 Scheduler Status")
    logger.info(f"   Total Cities: {len(CITIES)}")
    logger.info(f"   Cities with failures: {len([c for c, f in failure_counts.items() if f > 0])}")
    for city in CITIES:
        failures = failure_counts[city]
        last = last_success.get(city, 'Never')
        status = '✅' if failures == 0 else f'⚠️  ({failures} failures)'
        logger.info(f"   {city:15s}: {status:20s} Last: {last}")
    logger.info("=" * 60)

if __name__ == '__main__':
    logger.info("🎲 Auto-recovery scheduler starting...")
    print("🎲 Auto-recovery scheduler starting...")

    # Print initial status
    print_status()

    cycle_count = 0
    while True:
        try:
            cycle_count += 1

            # Pick next city using smart selection
            city = get_next_city()
            logger.info(f"\n🎯 Cycle #{cycle_count}: Selected {city}")
            print(f"\n🎯 Cycle #{cycle_count}: Selected {city}")

            # Sleep random time between 5:00-5:30 AM (0-1800 seconds for production)
            # For testing, you can reduce this
            sleep_time = random.randint(0, 1800)
            logger.info(f"😴 Sleeping {sleep_time} seconds until next scrape...")
            print(f"😴 Sleeping {sleep_time} seconds until next scrape...")
            time.sleep(sleep_time)

            # Run the scraper with auto-recovery
            logger.info(f"🚀 Scraping {city} at {time.ctime()}")
            print(f"🚀 Scraping {city} at {time.ctime()}")

            success = run_scraper(city, max_retries=2)

            if success:
                logger.info(f"✅ {city} scrape completed successfully at {time.ctime()}")
                print(f"✅ {city} scrape completed successfully at {time.ctime()}")
            else:
                logger.warning(f"⚠️  {city} scrape completed with errors at {time.ctime()}")
                print(f"⚠️  {city} scrape completed with errors - will retry later")

            # Print status every 10 cycles
            if cycle_count % 10 == 0:
                print_status()

            # Brief pause before next cycle
            time.sleep(10)

        except KeyboardInterrupt:
            logger.info("\n👋 Scheduler stopped by user")
            print("\n👋 Scheduler stopped by user")
            print_status()
            break
        except Exception as e:
            logger.error(f"❌ Scheduler error: {e}")
            logger.debug(traceback.format_exc())
            print(f"❌ Scheduler error: {e}")
            print("Continuing in 30 seconds...")
            time.sleep(30)