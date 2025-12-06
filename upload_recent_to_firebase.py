#!/usr/bin/env python3
"""
Upload ONLY Recent Leads (Last 30 Days) to Firebase
This keeps Firebase usage low while maintaining accurate city totals
"""

import csv
import os
import sys
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, firestore

def initialize_firebase():
    """Initialize Firebase Admin SDK"""
    try:
        firebase_admin.get_app()
    except ValueError:
        cred = credentials.Certificate('serviceAccountKey.json')
        firebase_admin.initialize_app(cred)
    return firestore.client()

def parse_csv_file(csv_path, days_back=30):
    """Parse CSV and return ALL permits + RECENT permits (last N days)"""
    all_permits = []
    recent_permits = []

    # Calculate cutoff date (30 days ago)
    cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')

    try:
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)

            for row in reader:
                permit = {
                    'date': row.get('date', row.get('Date', row.get('issued_date', ''))),
                    'city': row.get('city', row.get('City', '')),
                    'permit_type': row.get('permit_type', row.get('Permit Type', row.get('type', ''))),
                    'permit_number': row.get('permit_number', row.get('Permit Number', row.get('Number', ''))),
                    'address': row.get('address', row.get('Address', '')),
                    'description': row.get('description', row.get('Description', ''))
                }

                if not any(permit.values()):
                    continue

                all_permits.append(permit)

                # Only add to recent if within last 30 days
                if permit.get('date') and permit['date'] >= cutoff_date:
                    recent_permits.append(permit)

    except Exception as e:
        print(f"Error reading {csv_path}: {e}")
        return [], []

    return all_permits, recent_permits

def upload_to_firebase(db, permits, city_name):
    """Upload permits to Firebase"""
    if not permits:
        print(f"  ⚠️  No recent permits to upload for {city_name}")
        return 0

    batch = db.batch()
    count = 0

    for permit in permits:
        doc_ref = db.collection('admin_leads').document()

        if not permit.get('date'):
            permit['date'] = datetime.now().strftime('%Y-%m-%d')

        if not permit.get('city'):
            permit['city'] = city_name

        batch.set(doc_ref, permit)
        count += 1

        if count % 500 == 0:
            batch.commit()
            batch = db.batch()
            print(f"  📤 Uploaded {count} permits for {city_name}...")

    if count % 500 != 0:
        batch.commit()

    return count

def update_city_stats(db, city_name, total_leads, recent_leads):
    """Update city statistics with TOTAL count"""
    city_data = {
        'name': city_name,
        'leads': total_leads,  # TOTAL scraped leads
        'recent_leads': recent_leads,  # Last 30 days in Firebase
        'files': 1,
        'last_updated': datetime.now()
    }

    cities_ref = db.collection('admin_cities')
    query = cities_ref.where('name', '==', city_name).limit(1)
    docs = query.get()

    if docs:
        doc_ref = docs[0].reference
        doc_ref.update(city_data)
    else:
        cities_ref.add(city_data)

    print(f"  📊 Stats: {total_leads} total leads, {recent_leads} recent (uploaded to Firebase)")

def get_city_name_from_filename(filename):
    """Extract city name from filename"""
    base = os.path.basename(filename).lower()
    base = base.replace('.csv', '').replace('_', ' ')

    import re
    base = re.sub(r'\d{4}[-_]?\d{2}[-_]?\d{2}', '', base)
    base = re.sub(r'\d{8}', '', base)
    base = ' '.join(base.split())

    return base.title()

def batch_upload_recent(csv_directory):
    """Upload ONLY recent leads from all CSV files"""
    if not os.path.exists(csv_directory):
        print(f"Error: Directory not found: {csv_directory}")
        return

    # Find all CSV files
    csv_files = []
    for root, dirs, files in os.walk(csv_directory):
        for file in files:
            if file.endswith('.csv'):
                csv_files.append(os.path.join(root, file))

    if not csv_files:
        print(f"No CSV files found in {csv_directory}")
        return

    print(f"Found {len(csv_files)} CSV files")
    print(f"📅 Will upload ONLY leads from last 30 days to Firebase")
    print(f"📊 City totals will reflect ALL scraped leads\n")

    # Initialize Firebase
    print("Initializing Firebase...")
    db = initialize_firebase()

    # Track totals
    total_all_leads = 0
    total_recent_leads = 0
    city_totals = {}

    for csv_file in csv_files:
        filename = os.path.basename(csv_file)
        city_name = get_city_name_from_filename(filename)

        print(f"\n📁 Processing {filename} -> {city_name}")

        # Parse CSV - get both all permits and recent permits
        all_permits, recent_permits = parse_csv_file(csv_file, days_back=30)

        if not all_permits:
            print(f"  ⚠️  No permits found in {filename}")
            continue

        print(f"  📊 Total in file: {len(all_permits)} permits")
        print(f"  📅 Recent (30 days): {len(recent_permits)} permits")

        # Aggregate city totals
        if city_name not in city_totals:
            city_totals[city_name] = {'all': 0, 'recent': 0}

        city_totals[city_name]['all'] += len(all_permits)
        city_totals[city_name]['recent'] += len(recent_permits)

    # Clear existing Firebase data
    print(f"\n🧹 Clearing existing Firebase data...")
    existing_docs = db.collection('admin_leads').stream()
    batch = db.batch()
    count = 0
    for doc in existing_docs:
        batch.delete(doc.reference)
        count += 1
        if count % 500 == 0:
            batch.commit()
            batch = db.batch()
    if count > 0:
        batch.commit()
        print(f"  🗑️  Cleared {count} existing permits")

    # Now upload recent data for each city
    for city_name, totals in city_totals.items():
        print(f"\n🏙️  {city_name}")

        # Re-parse files for this city to get recent permits
        city_recent_permits = []
        for csv_file in csv_files:
            if get_city_name_from_filename(os.path.basename(csv_file)) == city_name:
                _, recent = parse_csv_file(csv_file, days_back=30)
                city_recent_permits.extend(recent)

        # Upload recent permits to Firebase
        uploaded = upload_to_firebase(db, city_recent_permits, city_name)

        # Update city stats with TOTAL count
        update_city_stats(db, city_name, totals['all'], uploaded)

        total_all_leads += totals['all']
        total_recent_leads += uploaded

    print(f"\n✅ Upload complete!")
    print(f"📊 Total leads across all cities: {total_all_leads:,}")
    print(f"📅 Recent leads uploaded to Firebase: {total_recent_leads:,}")
    print(f"💾 Firebase storage saved: {total_all_leads - total_recent_leads:,} leads kept on server only")

def main():
    if len(sys.argv) < 2:
        print("Usage: python upload_recent_to_firebase.py <csv_directory>")
        print("Example: python upload_recent_to_firebase.py /Users/briceleasure/Desktop/contractor-leads-backend/leads/")
        sys.exit(1)

    csv_directory = sys.argv[1]

    if not os.path.exists('serviceAccountKey.json'):
        print("❌ Error: serviceAccountKey.json not found")
        sys.exit(1)

    batch_upload_recent(csv_directory)

if __name__ == "__main__":
    main()
