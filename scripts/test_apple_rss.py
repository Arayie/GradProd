#!/usr/bin/env python3
"""
Apple RSS Feasibility Test Script for Phase 0
Tests Apple customer-review RSS feed for India storefront across candidate applications
using official verified Apple App IDs from iTunes Search API.
"""
import json
import time
import urllib.request
import urllib.error

APPS = [
    {
        "internal_id": "groww",
        "name": "Groww",
        "apple_id": "1404871703"
    },
    {
        "internal_id": "zerodha_coin",
        "name": "Zerodha Coin (Mutual Funds)",
        "apple_id": "1392892554"
    },
    {
        "internal_id": "zerodha_kite",
        "name": "Zerodha Kite (Trading/Investing)",
        "apple_id": "1449453802"
    },
    {
        "internal_id": "upstox",
        "name": "Upstox",
        "apple_id": "1584953620"
    },
    {
        "internal_id": "angel_one",
        "name": "Angel One",
        "apple_id": "1060530981"
    },
    {
        "internal_id": "indmoney",
        "name": "INDmoney",
        "apple_id": "1450178837"
    },
    {
        "internal_id": "et_money",
        "name": "ET Money",
        "apple_id": "1212752482"
    },
    {
        "internal_id": "paytm_money",
        "name": "Paytm Money",
        "apple_id": "1344431352"
    }
]

def test_app_feed(app, max_pages=12):
    apple_id = app["apple_id"]
    print(f"\n==========================================")
    print(f"Testing {app['name']} (App ID: {apple_id})")
    print(f"==========================================")
    
    all_reviews = []
    seen_ids = set()
    pages_tested = 0
    http_statuses = {}
    pagination_behavior = ""
    newest_date = None
    oldest_date = None
    sample_fields = set()
    
    for page in range(1, max_pages + 1):
        url = f"https://itunes.apple.com/in/rss/customerreviews/page={page}/id={apple_id}/sortby=mostrecent/json"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
        )
        
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                status = resp.status
                http_statuses[page] = status
                raw_data = resp.read().decode("utf-8")
                data = json.loads(raw_data)
                
                feed = data.get("feed", {})
                entries = feed.get("entry", [])
                
                if isinstance(entries, dict):
                    entries = [entries]
                
                page_reviews = []
                for entry in entries:
                    if "im:rating" not in entry:
                        continue
                    
                    rev_id = entry.get("id", {}).get("label")
                    title = entry.get("title", {}).get("label")
                    content = entry.get("content", {}).get("label")
                    rating = entry.get("im:rating", {}).get("label")
                    updated = entry.get("updated", {}).get("label")
                    version = entry.get("im:version", {}).get("label")
                    author_name = entry.get("author", {}).get("name", {}).get("label")
                    
                    sample_fields.update(entry.keys())
                    
                    page_reviews.append({
                        "id": rev_id,
                        "title": title,
                        "rating": rating,
                        "updated": updated,
                        "version": version,
                        "has_content": bool(content),
                        "has_author_name": bool(author_name)
                    })
                
                print(f"  Page {page}: HTTP {status}, Total entries in feed: {len(entries)}, Extracted reviews: {len(page_reviews)}")
                
                if len(page_reviews) == 0:
                    pagination_behavior = f"Returned 0 reviews on page {page}"
                    break
                
                # Check for duplicates
                new_on_page = 0
                for r in page_reviews:
                    if r["id"] not in seen_ids:
                        seen_ids.add(r["id"])
                        all_reviews.append(r)
                        new_on_page += 1
                
                print(f"    -> Unique new reviews: {new_on_page} (Total unique so far: {len(all_reviews)})")
                
                if new_on_page == 0:
                    pagination_behavior = f"Page {page} duplicates earlier pages (loop detected)"
                    break
                    
                pages_tested += 1
                time.sleep(0.4) # Politeness delay
                
        except urllib.error.HTTPError as e:
            http_statuses[page] = e.code
            print(f"  Page {page}: HTTPError {e.code} ({e.reason})")
            if e.code == 400:
                pagination_behavior = f"Hard page cap reached at page {page-1} (HTTP 400)"
            elif e.code == 404:
                pagination_behavior = f"Not found at page {page} (HTTP 404)"
            else:
                pagination_behavior = f"Error {e.code} on page {page}"
            break
        except Exception as e:
            http_statuses[page] = str(e)
            print(f"  Page {page}: Exception {e}")
            pagination_behavior = f"Exception: {e}"
            break
            
    if all_reviews:
        dated_reviews = [r for r in all_reviews if r.get("updated")]
        if dated_reviews:
            dated_reviews.sort(key=lambda x: x["updated"], reverse=True)
            newest_date = dated_reviews[0]["updated"]
            oldest_date = dated_reviews[-1]["updated"]
            
    res = {
        "app": app["name"],
        "internal_id": app["internal_id"],
        "apple_id": apple_id,
        "http_statuses": http_statuses,
        "page_1_status": http_statuses.get(1),
        "pages_accessible": pages_tested,
        "total_unique_reviews": len(all_reviews),
        "newest_review": newest_date,
        "oldest_review": oldest_date,
        "pagination_behavior": pagination_behavior or f"Tested up to {pages_tested} pages successfully",
        "sample_fields": sorted(list(sample_fields))
    }
    return res

if __name__ == "__main__":
    results = []
    for app in APPS:
        res = test_app_feed(app, max_pages=12)
        results.append(res)
        
    print("\n\n================ SUMMARY REPORT ================")
    print(json.dumps(results, indent=2))
    
    with open("reports/apple_rss_empirical_results.json", "w") as f:
        json.dump(results, f, indent=2)
