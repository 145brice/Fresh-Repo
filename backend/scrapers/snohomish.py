import requests
from bs4 import BeautifulSoup
import time
import random

def get_leads_for_city(city_name):
    """Scrape Snohomish County, WA building permits from HTML table"""
    if city_name.lower() != 'snohomish':
        return []

    url = "https://snohomishcountywa.gov/Archive.aspx?AMID=13"
    leads = []

    # Retry logic with exponential backoff
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Try specific table selector first, fallback to general table
            table_selectors = ['table#permitGrid', 'table', 'table.permitTable']
            rows = None

            for selector in table_selectors:
                rows = soup.select(f'{selector} tr')
                if rows and len(rows) > 1:  # Has header + data
                    break

            if not rows or len(rows) <= 1:
                print(f"Snohomish: No table rows found on attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    time.sleep(random.uniform(1, 3) * (2 ** attempt))  # Exponential backoff
                    continue
                return leads

            for row in rows[1:]:  # Skip header
                cols = row.select('td')
                if len(cols) >= 5:
                    try:
                        permit = cols[0].get_text(strip=True)
                        address = cols[1].get_text(strip=True)
                        owner = cols[2].get_text(strip=True) if len(cols) > 2 else ''
                        permit_type = cols[3].get_text(strip=True) if len(cols) > 3 else ''
                        date = cols[4].get_text(strip=True) if len(cols) > 4 else ''
                        value = cols[5].get_text(strip=True) if len(cols) > 5 else ''

                        # Clean up value (remove $ and commas)
                        if value:
                            value = value.replace('$', '').replace(',', '').strip()
                            try:
                                value = float(value)
                            except ValueError:
                                value = 0.0

                        leads.append({
                            'permit_number': permit,
                            'address': address,
                            'permit_type': permit_type,
                            'permit_value': value,
                            'issue_date': date,
                            'owner': owner,
                            'status': 'issued'
                        })
                    except Exception as e:
                        print(f"Snohomish: Error parsing row: {e}")
                        continue

            print(f"Snohomish: Successfully scraped {len(leads)} permits")
            return leads

        except requests.exceptions.RequestException as e:
            print(f"Snohomish: Request error on attempt {attempt + 1}: {e}")
        except Exception as e:
            print(f"Snohomish: Unexpected error on attempt {attempt + 1}: {e}")

        if attempt < max_retries - 1:
            time.sleep(random.uniform(1, 3) * (2 ** attempt))  # Exponential backoff

    print(f"Snohomish: Failed to scrape after {max_retries} attempts")
    return leads