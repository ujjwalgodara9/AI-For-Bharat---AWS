"""
Test script to find the optimal API delay for data.gov.in Agmarknet API.
Sends requests with different delays and measures 429 error rate.

Usage: python backend/scripts/test_api_rate_limit.py
"""
import time
import json
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timedelta

API_KEY = "579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b"
RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"
BASE_URL = f"https://api.data.gov.in/resource/{RESOURCE_ID}"

# Test with a few commodity/state combos
TEST_COMBOS = [
    ("Wheat", "Madhya Pradesh"),
    ("Onion", "Maharashtra"),
    ("Tomato", "Rajasthan"),
    ("Rice", "Uttar Pradesh"),
    ("Potato", "Gujarat"),
    ("Mustard", "Rajasthan"),
    ("Chana", "Madhya Pradesh"),
    ("Maize", "Karnataka"),
    ("Cotton", "Gujarat"),
    ("Soyabean", "Madhya Pradesh"),
    ("Garlic", "Rajasthan"),
    ("Moong", "Rajasthan"),
    ("Bajra", "Haryana"),
    ("Jowar", "Karnataka"),
    ("Turmeric", "Andhra Pradesh"),
    ("Red Chilli", "Andhra Pradesh"),
    ("Groundnut", "Gujarat"),
    ("Urad", "Madhya Pradesh"),
    ("Coriander", "Rajasthan"),
    ("Cumin", "Rajasthan"),
]

target_date = datetime.utcnow().strftime("%d/%m/%Y")


def make_request(commodity, state):
    params = {
        "api-key": API_KEY,
        "format": "json",
        "limit": 10,
        "offset": 0,
        "filters[state.keyword]": state,
        "filters[commodity]": commodity,
        "filters[arrival_date]": target_date,
    }
    query_string = urllib.parse.urlencode(params)
    url = f"{BASE_URL}?{query_string}"
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "MandiMitra/1.0")
    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
        return data.get("total", 0)


def test_delay(delay_seconds, num_requests=20):
    """Test a specific delay and return success/failure counts."""
    success = 0
    fail_429 = 0
    fail_other = 0

    print(f"\n{'='*60}")
    print(f"Testing delay={delay_seconds}s with {num_requests} requests...")
    print(f"{'='*60}")

    start = time.time()
    for i, (commodity, state) in enumerate(TEST_COMBOS[:num_requests]):
        try:
            total = make_request(commodity, state)
            success += 1
            print(f"  [{i+1}/{num_requests}] OK: {commodity}/{state} -> {total} records")
        except urllib.error.HTTPError as e:
            if e.code == 429:
                fail_429 += 1
                print(f"  [{i+1}/{num_requests}] 429: {commodity}/{state}")
            else:
                fail_other += 1
                print(f"  [{i+1}/{num_requests}] ERR {e.code}: {commodity}/{state}")
        except Exception as e:
            fail_other += 1
            print(f"  [{i+1}/{num_requests}] ERR: {commodity}/{state} -> {e}")

        if i < num_requests - 1:
            time.sleep(delay_seconds)

    elapsed = time.time() - start
    print(f"\nResults for delay={delay_seconds}s:")
    print(f"  Success: {success}/{num_requests}")
    print(f"  429 errors: {fail_429}/{num_requests}")
    print(f"  Other errors: {fail_other}/{num_requests}")
    print(f"  Total time: {elapsed:.1f}s")
    print(f"  Effective rate: {num_requests/elapsed:.2f} req/s")

    if num_requests == 20:
        estimated_total = elapsed / 20 * 280
        print(f"  Estimated time for 280 calls: {estimated_total:.0f}s ({estimated_total/60:.1f} min)")

    return success, fail_429, fail_other


if __name__ == "__main__":
    delays_to_test = [1.0, 1.5, 2.0, 3.0]

    print(f"Testing Agmarknet API rate limits for date={target_date}")
    print(f"API Key: {API_KEY[:10]}...")

    results = {}
    for delay in delays_to_test:
        s, f429, fother = test_delay(delay, num_requests=20)
        results[delay] = {"success": s, "429": f429, "other": fother}

        # Wait between test rounds to let rate limit reset
        if delay != delays_to_test[-1]:
            print(f"\nWaiting 30s for rate limit to reset...")
            time.sleep(30)

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"{'Delay':>8s} | {'Success':>8s} | {'429s':>6s} | {'Other':>6s}")
    print(f"{'-'*8} | {'-'*8} | {'-'*6} | {'-'*6}")
    for delay, r in results.items():
        print(f"{delay:>7.1f}s | {r['success']:>7d}/20 | {r['429']:>5d} | {r['other']:>5d}")

    # Recommend the lowest delay with 0 failures
    best = None
    for delay in delays_to_test:
        if results[delay]["429"] == 0:
            best = delay
            break

    if best:
        print(f"\nRecommended delay: {best}s (lowest delay with zero 429 errors)")
    else:
        print(f"\nAll delays had 429 errors. Try higher delays (4s, 5s).")
