"""
Geocode community support services and map to LSOAs.

This script:
1. Reads the community support services CSV
2. Uses the postcodes.io API (free, no key needed) to geocode postcodes -> lat/lon
3. Uses postcodes.io to get LSOA codes for each postcode
4. Outputs an enriched CSV with LSOA codes ready for joining to your master dataset

Usage:
    python geocode_and_map_lsoa.py
"""

import csv
import json
import time
import urllib.request
import urllib.error
import os

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_CSV = os.path.join(DATA_DIR, "data RAW", "london_community_support_services.csv")
OUTPUT_CSV = os.path.join(DATA_DIR, "data RAW", "london_community_services_with_lsoa.csv")


def bulk_postcode_lookup(postcodes):
    """
    Use postcodes.io bulk lookup API to get lat/lon and LSOA for multiple postcodes.
    Free API, no key needed. Max 100 postcodes per request.
    """
    url = "https://api.postcodes.io/postcodes"
    data = json.dumps({"postcodes": postcodes}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result.get("result", [])
    except urllib.error.HTTPError as e:
        print(f"  HTTP Error {e.code}: {e.reason}")
        return []
    except Exception as e:
        print(f"  Error: {e}")
        return []


def is_full_postcode(pc):
    """Check if a postcode looks like a full UK postcode (e.g., SW1A 1AA)."""
    pc = pc.strip().upper()
    # Full postcodes are typically 5-8 chars with a space or parseable pattern
    # They end with a digit followed by two letters
    clean = pc.replace(" ", "")
    if len(clean) < 5:
        return False
    # Last 3 chars should be digit-letter-letter
    if clean[-1].isalpha() and clean[-2].isalpha() and clean[-3].isdigit():
        return True
    return False


def normalize_postcode(pc):
    """Normalize postcode formatting for API lookup."""
    pc = pc.strip().upper().replace("  ", " ")
    # If no space, try to insert one (last 3 chars are the inward code)
    if " " not in pc and len(pc) >= 5:
        pc = pc[:-3] + " " + pc[-3:]
    return pc


def main():
    # Read the CSV
    print(f"Reading {INPUT_CSV}...")
    with open(INPUT_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Loaded {len(rows)} records.")

    # Collect all full postcodes for bulk lookup
    postcode_set = set()
    for row in rows:
        pc = row["postcode"].strip()
        if is_full_postcode(pc):
            postcode_set.add(normalize_postcode(pc))

    print(f"Found {len(postcode_set)} unique full postcodes to look up.")

    # Bulk lookup in batches of 100
    postcode_list = sorted(postcode_set)
    postcode_data = {}

    for i in range(0, len(postcode_list), 100):
        batch = postcode_list[i:i+100]
        print(f"  Looking up batch {i//100 + 1} ({len(batch)} postcodes)...")
        results = bulk_postcode_lookup(batch)

        for item in results:
            query_pc = item.get("query", "")
            result = item.get("result")
            if result:
                postcode_data[query_pc.upper().strip()] = {
                    "latitude": result.get("latitude"),
                    "longitude": result.get("longitude"),
                    "lsoa_code": result.get("codes", {}).get("lsoa", ""),
                    "lsoa_name": result.get("lsoa", ""),
                    "msoa_code": result.get("codes", {}).get("msoa", ""),
                    "msoa_name": result.get("msoa", ""),
                    "ward": result.get("admin_ward", ""),
                    "district": result.get("admin_district", ""),
                }

        time.sleep(0.5)  # Be polite to the API

    print(f"Successfully geocoded {len(postcode_data)} postcodes.")

    # Enrich each row
    enriched = []
    geocoded_count = 0
    for row in rows:
        pc = normalize_postcode(row["postcode"].strip()).upper()
        lookup = postcode_data.get(pc, {})

        # Use API lat/lon if available, otherwise keep existing
        if lookup.get("latitude"):
            row["latitude"] = lookup["latitude"]
            row["longitude"] = lookup["longitude"]
            geocoded_count += 1

        row["lsoa_code"] = lookup.get("lsoa_code", "")
        row["lsoa_name"] = lookup.get("lsoa_name", "")
        row["msoa_code"] = lookup.get("msoa_code", "")
        row["msoa_name"] = lookup.get("msoa_name", "")
        row["ward"] = lookup.get("ward", "")

        enriched.append(row)

    # Write output
    fieldnames = [
        "name", "type", "category", "address", "postcode", "borough",
        "latitude", "longitude", "lsoa_code", "lsoa_name",
        "msoa_code", "msoa_name", "ward", "source"
    ]

    print(f"\nWriting {OUTPUT_CSV}...")
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(enriched)

    print(f"Done! {geocoded_count} records geocoded with precise coordinates.")
    print(f"Output: {OUTPUT_CSV}")

    # Summary stats
    with_lsoa = sum(1 for r in enriched if r.get("lsoa_code"))
    without_lsoa = len(enriched) - with_lsoa
    print(f"\nRecords with LSOA code: {with_lsoa}")
    print(f"Records without LSOA code: {without_lsoa} (partial postcodes)")


if __name__ == "__main__":
    main()
