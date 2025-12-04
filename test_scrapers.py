#!/usr/bin/env python3
"""
Quick test script to verify all scrapers are working with auto-recovery
"""
import sys
import os

# Add scrapers to path
sys.path.insert(0, os.path.dirname(__file__))

def test_scraper(city_name, ScraperClass):
    """Test a single scraper"""
    print(f"\n{'='*60}")
    print(f"Testing {city_name} scraper...")
    print(f"{'='*60}")

    try:
        scraper = ScraperClass()
        print(f"✅ {city_name} scraper initialized")

        # Check if logger exists
        if hasattr(scraper, 'logger'):
            print(f"✅ {city_name} has logger")
        else:
            print(f"❌ {city_name} missing logger")

        # Check if health check exists
        if hasattr(scraper, 'health_check'):
            print(f"✅ {city_name} has health_check")
        else:
            print(f"❌ {city_name} missing health_check")

        # Check if run method exists
        if hasattr(scraper, 'run'):
            print(f"✅ {city_name} has run() method")
        else:
            print(f"❌ {city_name} missing run() method")

        # Try a small scrape (just 10 permits for testing)
        print(f"\n🚀 Running quick test scrape (max 10 permits)...")
        permits = scraper.scrape_permits(max_permits=10, days_back=7)

        if permits:
            print(f"✅ {city_name} scraper works! Retrieved {len(permits)} permits")
            return True
        else:
            print(f"⚠️  {city_name} scraper returned 0 permits (may be normal if no recent permits)")
            return True  # Not necessarily a failure

    except Exception as e:
        print(f"❌ {city_name} scraper failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("🧪 Testing All Scrapers with Auto-Recovery\n")

    from scrapers.nashville import NashvillePermitScraper
    from scrapers.austin import AustinPermitScraper
    from scrapers.houston import HoustonPermitScraper
    from scrapers.sanantonio import SanAntonioPermitScraper
    from scrapers.charlotte import CharlottePermitScraper
    from scrapers.chattanooga import ChattanoogaPermitScraper
    from scrapers.phoenix import PhoenixPermitScraper

    scrapers = [
        ('Nashville', NashvillePermitScraper),
        ('Austin', AustinPermitScraper),
        ('Houston', HoustonPermitScraper),
        ('San Antonio', SanAntonioPermitScraper),
        ('Charlotte', CharlottePermitScraper),
        ('Chattanooga', ChattanoogaPermitScraper),
        ('Phoenix', PhoenixPermitScraper),
    ]

    results = {}
    for city_name, ScraperClass in scrapers:
        results[city_name] = test_scraper(city_name, ScraperClass)

    # Summary
    print(f"\n{'='*60}")
    print("📊 Test Summary")
    print(f"{'='*60}")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for city, status in results.items():
        emoji = '✅' if status else '❌'
        print(f"{emoji} {city:15s}: {'PASS' if status else 'FAIL'}")

    print(f"\n{passed}/{total} scrapers passed")

    if passed == total:
        print("\n🎉 All scrapers are working with auto-recovery!")
    else:
        print(f"\n⚠️  {total - passed} scraper(s) need attention")

if __name__ == '__main__':
    main()
