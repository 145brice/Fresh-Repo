# Auto-Recovery System for Scrapers

## Overview

All scrapers now have comprehensive auto-recovery capabilities that ensure they continue working even when they encounter errors. If a scraper fails one day, it will automatically fix itself on the next run.

## Features Implemented

### 1. **Automatic Retry with Exponential Backoff**
- Each HTTP request automatically retries up to 3 times
- Wait time increases exponentially: 2s → 4s → 8s
- Prevents temporary network issues from breaking scrapes

### 2. **Batch-Level Recovery**
- If one batch fails, the scraper continues with the next batch
- Tracks consecutive failures (max 3 before stopping)
- Saves partial results before stopping

### 3. **Partial Results Saving**
- If scraper fails midway, all collected data is saved
- Saved as `{date}_{city}_partial.csv`
- No data loss even during failures

### 4. **Comprehensive Logging**
- All operations logged to `backend/logs/{city}.log`
- Includes timestamps, error details, and stack traces
- Easy to debug issues

### 5. **Health Monitoring**
- Each scraper tracks success/failure history
- Health check files in `backend/logs/{city}_health.txt`
- Shows last successful scrape timestamp

### 6. **Smart Scheduler**
- Automatically retries failed scrapers
- Prioritizes cities by importance
- Reduces priority for repeatedly failing cities (but still retries)
- Sends email alerts every 3rd failure (not every failure)

## File Structure

```
backend/
├── scrapers/
│   ├── utils.py                    # Shared utilities (NEW)
│   ├── __init__.py                 # Package exports (UPDATED)
│   ├── nashville.py                # Updated with auto-recovery
│   ├── austin.py                   # Updated with auto-recovery
│   ├── houston.py                  # Updated with auto-recovery
│   ├── charlotte.py                # Updated with auto-recovery
│   ├── phoenix.py                  # Updated with auto-recovery
│   ├── chattanooga.py              # Updated with auto-recovery
│   └── sanantonio.py               # Updated with auto-recovery
├── scheduler.py                    # Updated with smart retry logic
├── test_scrapers.py                # Test script (NEW)
└── logs/                           # Log files (NEW)
    ├── scheduler.log
    ├── nashville.log
    ├── nashville_health.txt
    └── ... (one per city)
```

## How It Works

### When a Scraper Runs:

1. **Initialize** with logger and health check
2. **Fetch data** in batches with automatic retry
3. **Track failures** - if 3 consecutive batches fail, stop
4. **Save partial results** if we have any data
5. **Log everything** for debugging
6. **Record health status** (success or failure)

### When the Scheduler Runs:

1. **Select next city** using smart prioritization
2. **Run scraper** with up to 2 retries (3 total attempts)
3. **Wait between retries** (5s, 10s)
4. **Track failures** per city
5. **Send alerts** every 3rd failure
6. **Continue** to next city regardless of result

## Usage

### Run Individual Scraper
```bash
cd backend
python3 -m scrapers.nashville
```

### Run Scheduler (Production)
```bash
cd backend
python3 scheduler.py
```

### Test All Scrapers
```bash
cd backend
python3 test_scrapers.py
```

### Check Scraper Health
```bash
# View logs
cat backend/logs/nashville.log

# View health status
cat backend/logs/nashville_health.txt

# Check all health files
ls -lh backend/logs/*_health.txt
```

## Error Recovery Examples

### Example 1: Temporary Network Error
```
❌ Batch 5 fails (network timeout)
→ Retry #1 after 2 seconds
→ ✅ Success! Continue scraping
```

### Example 2: API Rate Limit
```
❌ Batch 10 fails (429 Too Many Requests)
→ Retry #1 after 2 seconds
→ Retry #2 after 4 seconds
→ Retry #3 after 8 seconds
→ ✅ Success! Continue scraping
```

### Example 3: Partial Outage
```
✅ Batches 1-5: 5,000 permits collected
❌ Batch 6 fails
❌ Batch 7 fails
❌ Batch 8 fails (3 consecutive failures)
→ 💾 Save 5,000 permits to partial CSV
→ 📧 Send alert email
→ ⏰ Scheduler will retry later
```

### Example 4: Complete API Outage
```
❌ Attempt 1 fails
→ Wait 5 seconds
❌ Attempt 2 fails
→ Wait 10 seconds
❌ Attempt 3 fails
→ Log error
→ Send alert (if 3rd failure)
→ Try again on next scheduled run
```

## Configuration

### Adjust Retry Settings
Edit `backend/scrapers/utils.py`:
```python
@retry_with_backoff(
    max_retries=3,          # Number of retries
    initial_delay=2,        # Initial wait time
    backoff_factor=2,       # Delay multiplier
    exceptions=(requests.RequestException,)
)
```

### Adjust Scheduler Settings
Edit `backend/scheduler.py`:
```python
# Retry attempts per scraper run
success = run_scraper(city, max_retries=2)  # Change from 2 to desired value

# Sleep time between scrapes (in seconds)
sleep_time = random.randint(0, 1800)  # Reduce for testing
```

### City Priority
Edit `backend/scheduler.py`:
```python
CITIES = {
    'nashville': 3,      # Higher = scraped more often
    'chattanooga': 2,
    'austin': 3,
    # ... etc
}
```

## Monitoring

### View Real-Time Logs
```bash
# Tail scheduler log
tail -f backend/logs/scheduler.log

# Tail specific scraper
tail -f backend/logs/phoenix.log
```

### Check Health Status
```bash
# See which scrapers are healthy
grep "SUCCESS" backend/logs/*_health.txt

# See recent failures
grep "FAILURE" backend/logs/*_health.txt
```

### Monitor Scheduler Status
The scheduler prints status every 10 cycles:
```
📊 Scheduler Status
   Total Cities: 7
   Cities with failures: 2
   nashville      : ✅                    Last: Mon Nov 29 10:30:45 2025
   austin         : ⚠️  (2 failures)     Last: Mon Nov 29 08:15:22 2025
   ...
```

## Email Alerts

Email alerts are sent when:
- A scraper fails 3 times in a row
- Then every 3rd failure after that (to avoid spam)

Alert includes:
- City name
- Failure count
- Last successful scrape time
- Error message
- Full stack trace

## Best Practices

1. **Check logs regularly** - Look for patterns in failures
2. **Monitor health files** - Know when scrapers last succeeded
3. **Update endpoints** - If a scraper fails consistently, the API may have changed
4. **Adjust priorities** - Focus on most important cities
5. **Test after changes** - Run `test_scrapers.py` after modifying code

## Troubleshooting

### Scraper Keeps Failing
1. Check logs: `cat backend/logs/{city}.log`
2. Test manually: `python3 -m scrapers.{city}`
3. Check if API endpoint changed
4. Verify API still exists and is public

### No Logs Being Created
1. Ensure logs directory exists: `mkdir -p backend/logs`
2. Check file permissions
3. Run scraper manually to see errors

### Scheduler Not Running
1. Check for Python errors
2. Verify all scrapers can import
3. Run test script: `python3 test_scrapers.py`

### Too Many Email Alerts
1. Alerts only sent every 3rd failure
2. Adjust in `scheduler.py`:
   ```python
   if failure_count % 3 != 0:  # Change 3 to higher number
   ```

## Summary

Your scraper system is now fully automated with auto-recovery:

✅ **Automatic retries** on failures
✅ **Partial results saving** - no data loss
✅ **Comprehensive logging** - easy debugging
✅ **Health monitoring** - track scraper status
✅ **Smart scheduler** - prioritized execution
✅ **Email alerts** - know when issues occur
✅ **Self-healing** - recovers from temporary errors

The system will continue running and automatically recover from most errors!
