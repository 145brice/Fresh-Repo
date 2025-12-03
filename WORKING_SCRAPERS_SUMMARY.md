# Working City Scrapers Summary
**Last Updated:** December 3, 2025
**Status:** 5 cities with working real-time data scrapers

## Working Cities (5 total)

### 1. Austin, TX ✅
- **API Type:** Socrata SODA API
- **Endpoint:** `https://data.austintexas.gov/resource/3syk-w9eu.json`
- **Data Recency:** Current (Dec 2025 data confirmed)
- **Field Mappings:**
  - Permit Number: `permit_number`
  - Address: `address`
  - Type: `permit_type`
  - Value: `total_valuation`
  - Issued Date: `issued_date`
  - Status: `status_current`
- **File:** [backend/scrapers/austin.py](backend/scrapers/austin.py)
- **Notes:** Rock solid Socrata endpoint, very reliable

### 2. Seattle, WA ✅
- **API Type:** Socrata SODA API
- **Endpoint:** `https://data.seattle.gov/resource/76t5-zqzr.json`
- **Data Recency:** Current (Dec 2025 data confirmed)
- **Field Mappings:**
  - Permit Number: `permitnum` or `application_permit_number`
  - Address: `originaladdress1`
  - Type: `permittypedesc` or `permittypemapped`
  - Value: `estprojectcost`
  - Issued Date: `issueddate`
  - Status: `statuscurrent`
- **File:** [backend/scrapers/seattle.py](backend/scrapers/seattle.py)
- **Notes:** Another excellent Socrata implementation

### 3. Chicago, IL ✅
- **API Type:** Socrata SODA API
- **Endpoint:** `https://data.cityofchicago.org/resource/ydr8-5enu.json`
- **Data Recency:** Current (Dec 2025 data confirmed)
- **Field Mappings:**
  - Permit Number: `permit_`
  - Address: Assembled from `street_number`, `street_direction`, `street_name`
  - Type: `permit_type`
  - Value: `estimated_cost`
  - Issued Date: `issue_date`
  - Status: `status`
- **File:** [backend/scrapers/chicago.py](backend/scrapers/chicago.py)
- **Notes:** High volume city, can pull 1000+ permits easily

### 4. Philadelphia, PA ✅ (NEWLY FIXED)
- **API Type:** Carto SQL API
- **Endpoint:** `https://phl.carto.com/api/v2/sql`
- **Data Recency:** Current (Dec 2, 2025 data confirmed - permits issued TODAY)
- **Query:** `SELECT * FROM permits WHERE permitissuedate >= 'YYYY-MM-DD' ORDER BY permitissuedate DESC`
- **Field Mappings:**
  - Permit Number: `permitnumber`
  - Address: `address`
  - Type: `permitdescription` or `typeofwork`
  - Value: Not available (defaults to $0.00)
  - Issued Date: `permitissuedate`
  - Status: 'Issued' (all records are issued)
- **File:** [backend/scrapers/philadelphia.py](backend/scrapers/philadelphia.py)
- **Capacity:** Successfully pulled 5,893 permits from last 90 days
- **Notes:** Fixed table name from 'li_permits' to 'permits'. Very reliable Carto SQL endpoint.

### 5. Nashville, TN ✅ (NEWLY FIXED)
- **API Type:** ArcGIS MapServer REST API
- **Endpoint:** `https://maps.nashville.gov/arcgis/rest/services/Codes/BuildingPermits/MapServer/0/query`
- **Data Recency:** Current (Dec 2, 2025 data confirmed)
- **Field Mappings:**
  - Permit Number: `CASE_NUMBER`
  - Address: `LOCATION`
  - Type: `CASE_TYPE_DESC`
  - Value: `CONSTVAL`
  - Issued Date: `DATE_ISSUED` (ArcGIS timestamp in milliseconds)
  - Status: `STATUS_CODE`
- **File:** [backend/scrapers/nashville.py](backend/scrapers/nashville.py)
- **Notes:** Migrated from Socrata to ArcGIS MapServer. Use MapServer not FeatureServer. Timestamps are in milliseconds (divide by 1000).

---

## API Type Breakdown

### Socrata SODA API (3 cities)
- Austin, Seattle, Chicago
- **Pros:** Very reliable, standard REST API, consistent patterns
- **Cons:** Some cities migrating away from Socrata to ArcGIS Hub
- **Query Pattern:** `GET https://domain/resource/dataset-id.json?$limit=1000&$offset=0&$where=issued_date>'2025-01-01'`

### Carto SQL API (1 city)
- Philadelphia
- **Pros:** Powerful SQL interface, very flexible querying
- **Cons:** Need to know exact table name
- **Query Pattern:** `GET https://domain/api/v2/sql?q=SELECT * FROM table WHERE date >= 'YYYY-MM-DD'&format=json`

### ArcGIS REST API (1 city)
- Nashville (MapServer)
- **Pros:** Widely used by municipalities, powerful GIS features
- **Cons:** More complex parameter structure, timestamps in milliseconds
- **Query Pattern:** `GET https://domain/MapServer/0/query?where=1=1&outFields=*&returnGeometry=false&f=json`

---

## Broken Cities (15 cities)

### Cities with Potential (need research/fixes):
1. **Charlotte, NC** - ArcGIS Hub migration (similar to Nashville)
2. **Chattanooga, TN** - Needs endpoint research
3. **Phoenix, AZ** - Has data portal, needs correct endpoint
4. **Atlanta, GA** - ArcGIS endpoint exists but returns "Invalid URL"
5. **Boston, MA** - Has Socrata portal, needs correct dataset ID
6. **San Diego, CA** - CSV endpoint returns 403 Forbidden
7. **San Antonio, TX** - CSV 404, ArcGIS 400 errors
8. **Houston, TX** - 403 Forbidden on downloads

### Cities needing more research:
9. Indianapolis, IN
10. Columbus, OH
11. Richmond, VA
12. Milwaukee, WI
13. Omaha, NE
14. Knoxville, TN
15. Birmingham, AL

---

## Key Learnings

### Common Issues:
1. **Platform Migrations:** Many cities migrating from Socrata to ArcGIS Hub
2. **Invalid URL Errors:** ArcGIS endpoints often return "Invalid URL" - need to find correct service structure
3. **Field Name Variability:** Every city uses different field names even on same platform
4. **Date Format Differences:** Socrata uses ISO strings, ArcGIS uses millisecond timestamps
5. **Access Restrictions:** Some portals returning 403/404 on downloads

### Success Patterns:
1. **Socrata Cities:** Look for `data.cityname.gov/resource/dataset-id.json`
2. **ArcGIS Cities:** Try both MapServer and FeatureServer, check service directory
3. **Carto Cities:** Use SQL API with correct table name
4. **Date Filtering:** Always filter by recent dates to verify data currency

### Testing Approach:
1. First verify endpoint returns data with small query (limit 5)
2. Check date fields to confirm data is current (2025)
3. Test field mappings to ensure correct data extraction
4. Scale up to full query (1000-5000 records)

---

## Daily Scraper Schedule

All 20 cities enabled with auto-recovery system in [backend/app.py](backend/app.py):
- **Schedule:** 5:00-5:30 AM CST daily
- **Random Delay:** 0-30 minutes to avoid detection
- **Auto-Recovery:** If scraper fails, copies most recent data from previous successful run
- **Result:** System always delivers 20 cities of data daily (either fresh or recent fallback)

---

## Next Steps

1. **Charlotte, TN:** Similar to Nashville, likely migrated to ArcGIS MapServer
2. **Phoenix, AZ:** Research correct Socrata dataset ID
3. **Atlanta, GA:** Find correct ArcGIS service structure
4. **Boston, MA:** Identify correct Socrata dataset

Goal: Get to 10 working cities for robust daily scraping operation.
