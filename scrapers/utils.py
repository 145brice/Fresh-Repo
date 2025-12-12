"""
Shared utilities for all scrapers - retry logic, logging, and error handling
"""
import time
import logging
import os
from functools import wraps
from datetime import datetime
import traceback

# Setup logging
LOG_DIR = os.path.join(os.path.dirname(__file__), '../logs')
os.makedirs(LOG_DIR, exist_ok=True)

def setup_logger(scraper_name):
    """Setup logger for a specific scraper"""
    logger = logging.getLogger(scraper_name)
    logger.setLevel(logging.INFO)

    # Prevent duplicate handlers
    if logger.handlers:
        return logger

    # File handler - one log file per scraper
    log_file = os.path.join(LOG_DIR, f'{scraper_name}.log')
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def retry_with_backoff(max_retries=3, initial_delay=1, backoff_factor=2, exceptions=(Exception,)):
    """
    Retry decorator with exponential backoff

    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch and retry
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None

            # Get logger from args if available (self.logger)
            logger = None
            if args and hasattr(args[0], 'logger'):
                logger = args[0].logger

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_retries:
                        if logger:
                            logger.error(f"Final attempt failed for {func.__name__}: {e}")
                            logger.debug(traceback.format_exc())
                        raise

                    if logger:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {e}. "
                            f"Retrying in {delay}s..."
                        )
                    else:
                        print(f"⚠️  Retry {attempt + 1}/{max_retries + 1} - waiting {delay}s...")

                    time.sleep(delay)
                    delay *= backoff_factor

            raise last_exception

        return wrapper
    return decorator


def safe_request(session_or_requests, url, params=None, timeout=30, max_retries=3):
    """
    Make a safe HTTP request with automatic retries

    Args:
        session_or_requests: requests module or requests.Session instance
        url: URL to request
        params: Query parameters
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts

    Returns:
        Response object or None if all retries failed
    """
    import requests

    for attempt in range(max_retries):
        try:
            response = session_or_requests.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            return response
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"⏱️  Timeout - retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"❌ Request timeout after {max_retries} attempts")
                return None
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"⚠️  Request failed: {e} - retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"❌ Request failed after {max_retries} attempts: {e}")
                return None

    return None


class ScraperHealthCheck:
    """Track scraper health and success rates"""

    def __init__(self, scraper_name):
        self.scraper_name = scraper_name
        self.health_file = os.path.join(LOG_DIR, f'{scraper_name}_health.txt')

    def record_success(self, count):
        """Record successful scrape"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(self.health_file, 'a') as f:
            f.write(f"{timestamp} | SUCCESS | {count} permits\n")

    def record_failure(self, error):
        """Record failed scrape"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(self.health_file, 'a') as f:
            f.write(f"{timestamp} | FAILURE | {str(error)[:100]}\n")

    def get_last_success(self):
        """Get timestamp of last successful scrape"""
        if not os.path.exists(self.health_file):
            return None

        try:
            with open(self.health_file, 'r') as f:
                lines = f.readlines()
                for line in reversed(lines):
                    if 'SUCCESS' in line:
                        return line.split('|')[0].strip()
        except:
            pass

        return None

    def check_health(self):
        """Check if scraper is healthy (succeeded recently)"""
        last_success = self.get_last_success()
        if not last_success:
            return False, "No successful scrapes recorded"

        try:
            last_time = datetime.strptime(last_success, '%Y-%m-%d %H:%M:%S')
            hours_since = (datetime.now() - last_time).total_seconds() / 3600

            if hours_since > 48:  # Alert if no success in 48 hours
                return False, f"Last success was {hours_since:.1f} hours ago"
            return True, f"Last success: {last_success}"
        except:
            return False, "Could not parse last success time"


def save_partial_results(permits, filename, scraper_name):
    """Save partial results even if scraper fails midway"""
    if not permits:
        return False

    import csv

    try:
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=list(permits[0].keys()))
            writer.writeheader()
            writer.writerows(permits)

        print(f"💾 Saved {len(permits)} partial results to {filename}")
        return True
    except Exception as e:
        print(f"❌ Failed to save partial results: {e}")
        return False


def load_scraper_config():
    """Load scraper configuration with state validation rules"""
    import json
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')

    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Failed to load scraper config: {e}")
        return {}


def validate_state(address, scraper_name, logger=None):
    """
    Validate that scraped data matches expected state for this scraper.
    This prevents data contamination (e.g., Philadelphia data in Phoenix folder).

    Args:
        address: Address string to validate
        scraper_name: Name of scraper (e.g., 'phoenix', 'houston')
        logger: Optional logger instance

    Returns:
        True if state matches or cannot be determined, False if wrong state detected
    """
    import re

    if not address or address == 'N/A':
        return True  # Can't validate empty addresses

    # Load config
    config = load_scraper_config()
    if scraper_name not in config:
        if logger:
            logger.warning(f"No config found for {scraper_name} - skipping state validation")
        return True

    valid_states = config[scraper_name].get('valid_states', [])
    if not valid_states:
        return True

    # Extract state abbreviation from address
    # Look for common patterns: ", AZ", " AZ ", "Arizona"
    state_pattern = r',\s*([A-Z]{2})(?:\s|,|$)'
    match = re.search(state_pattern, address)

    if not match:
        # Try full state names
        state_names = {
            'arizona': 'AZ', 'texas': 'TX', 'pennsylvania': 'PA',
            'illinois': 'IL', 'north carolina': 'NC', 'washington': 'WA',
            'tennessee': 'TN', 'georgia': 'GA', 'california': 'CA'
        }
        address_lower = address.lower()
        for name, abbrev in state_names.items():
            if name in address_lower:
                found_state = abbrev
                break
        else:
            return True  # Can't determine state, allow it
    else:
        found_state = match.group(1)

    # Check if found state matches valid states
    if found_state not in valid_states:
        if logger:
            logger.warning(
                f"❌ STATE MISMATCH: Found {found_state} in address '{address}' "
                f"but {scraper_name} expects {valid_states}. DISCARDING."
            )
        else:
            print(
                f"❌ STATE MISMATCH in {scraper_name}: "
                f"Found {found_state}, expected {valid_states}. DISCARDING: {address}"
            )
        return False

    return True
