import os
import sys
import time
import urllib.request
import urllib.parse
import urllib.error
import json

CURRENT_PRICES_RESOURCE = "9ef84268-d588-465a-a308-a864a43d0070"
HISTORICAL_PRICES_RESOURCE = "35985678-0d79-46b4-9ed6-6f13308a1d24"
BASE_URL = "https://api.data.gov.in/resource"

API_KEY = os.environ.get(
    "DATA_GOV_API_KEY",
    "579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b"
)

def test_rate_limit():
    print(f"Starting Rate Limit Test...")
    print(f"API Key: {API_KEY[:10]}...{API_KEY[-5:]}")
    print("=" * 60)
    print("Fetching as many items as possible to test rate limits.")
    print("We will send requests without sleep delays until we get a 429 Too Many Requests response or fetch all data.")
    print("=" * 60)
    
    offset = 0
    limit = 500
    requests_made = 0
    items_fetched = 0
    start_time = time.time()
    
    try:
        while True:
            params = {
                "api-key": API_KEY,
                "format": "json",
                "limit": limit,
                "offset": offset,
            }
            query = urllib.parse.urlencode(params)
            url = f"{BASE_URL}/{CURRENT_PRICES_RESOURCE}?{query}"
            
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "MandiMitra-RateLimitTester/1.0")
            
            req_start = time.time()
            try:
                # No timeout or sleep - we want to hit the rate limit!
                with urllib.request.urlopen(req, timeout=30) as response:
                    data = json.loads(response.read().decode("utf-8"))
                    requests_made += 1
                    
                    records = data.get("records", [])
                    total = data.get("total", 0)
                    
                    items_fetched += len(records)
                    
                    elapsed = time.time() - req_start
                    print(f"Request {requests_made:03d} | Offset {offset:05d} | Retrieved {len(records):03d}/{total} items | Took {elapsed:.2f}s | HTTP 200 OK")
                    
                    if not records:
                        print("No more records to fetch.")
                        break
                        
                    offset += limit
                    
                    if offset >= total:
                        print(f"\nAll {total} available items fetched successfully without hitting rate limits!")
                        break
                        
            except urllib.error.HTTPError as e:
                requests_made += 1
                if e.code == 429:
                    print(f"\n>>> RATE LIMIT HIT AFTER {requests_made} REQUESTS! <<<")
                    print(f"HTTP Status: 429 Too Many Requests")
                    break
                else:
                    print(f"\nHTTP Error {e.code}: {e.reason} on Request {requests_made}")
                    break
            except Exception as e:
                print(f"\nError on Request {requests_made + 1}: {e}")
                break
                
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
        
    duration = time.time() - start_time
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Total duration:      {duration:.2f} seconds")
    print(f"Total requests made: {requests_made}")
    print(f"Total items fetched: {items_fetched}")
    if duration > 0:
        print(f"Requests per second: {requests_made / duration:.2f}")

if __name__ == "__main__":
    test_rate_limit()
