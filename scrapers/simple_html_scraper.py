"""
Simple HTML Table Scraper - For counties that dump Excel as HTML
No BS. Just requests + BeautifulSoup. Grabs everything.
"""
import requests
from bs4 import BeautifulSoup
import csv
import os
from datetime import datetime

def scrape_html_table(url, city_name):
    """Dead simple scraper for HTML tables"""

    # Retry logic
    for _ in range(3):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            break
        except:
            pass

    soup = BeautifulSoup(response.text, 'html.parser')

    # Find the table - try common patterns
    table = soup.find('table', class_='permit') or soup.find('table', id='permitGrid') or soup.find('table')

    if not table:
        print(f"No table found for {city_name}")
        return []

    rows = table.find_all('tr')
    permits = []

    for row in rows[1:]:  # Skip header
        cols = row.find_all('td')
        if len(cols) < 3:
            continue

        permits.append({
            'permit_number': cols[0].get_text(strip=True),
            'address': cols[1].get_text(strip=True) if len(cols) > 1 else 'N/A',
            'owner': cols[2].get_text(strip=True) if len(cols) > 2 else 'N/A',
            'type': cols[3].get_text(strip=True) if len(cols) > 3 else 'N/A',
            'date': cols[4].get_text(strip=True) if len(cols) > 4 else 'N/A',
            'value': cols[5].get_text(strip=True) if len(cols) > 5 else '$0.00'
        })

    print(f"Scraped {len(permits)} permits from {city_name}")
    return permits

def save_csv(permits, city_name):
    """Save to CSV"""
    if not permits:
        return

    today = datetime.now().strftime('%Y-%m-%d')
    filename = f'leads/{city_name.lower().replace(" ", "")}/{today}/permits.csv'
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(permits[0].keys()))
        writer.writeheader()
        writer.writerows(permits)

    print(f"Saved to {filename}")

if __name__ == "__main__":
    # Test with a real city
    permits = scrape_html_table('YOUR_URL_HERE', 'TestCity')
    if permits:
        save_csv(permits, 'TestCity')
