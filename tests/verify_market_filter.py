
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from src.infrastructure.dart_api import DartApiClient
from dotenv import load_dotenv

def verify_market_filter():
    load_dotenv()
    api_key = os.getenv("DART_API_KEY")
    if not api_key:
        print("No API Key found.")
        return

    client = DartApiClient(api_key, save_directory="data/test_filter")
    
    # Use a recent date where we expect reports
    # 2026-01-19 seems to have data based on previous interactions
    target_date = "20260119"
    
    print(f"Verifying Market Filter on {target_date}...")
    
    # We will use the internal Logic to check what filtered list looks like
    # or we can mock request? But simpler to just run `fetch_disclosure_list` and apply filter manually to compare
    # and then run the collection method to see what it returns.
    
    # 1. Fetch RAW list first to see what SHOULD be filtered OUT
    raw_list = client.fetch_disclosure_list(target_date, target_date)
    if not raw_list or 'list' not in raw_list:
        print("No data returned from API.")
        return
        
    original_count = len(raw_list['list'])
    kospi_kosdaq_count = sum(1 for item in raw_list['list'] if item.get('corp_cls') in ['Y', 'K'])
    others_count = original_count - kospi_kosdaq_count
    
    print(f"Total Raw Items: {original_count}")
    print(f"Expected Items (Y/K): {kospi_kosdaq_count}")
    print(f"Expected Excluded (N/E): {others_count}")
    
    # 2. Run the actual collection method (using a filter that accepts everything to isolate market filter)
    # We'll use a dummy filter that returns everything, so we can see if the Client's internal market filter worked.
    def dummy_filter(data):
        return data # Pass through everything
        
    collected = client._collect_reports_with_filter(
        start_date=target_date,
        end_date=target_date,
        interval_days=1,
        filter_func=dummy_filter,
        report_type_name="Test-All-Markets"
    )
    
    print(f"\nCollected Items: {len(collected)}")
    
    # Verify
    all_valid = True
    for item in collected:
        if item.get('corp_cls') not in ['Y', 'K']:
            print(f"FAILURE: Found invalid market type {item.get('corp_cls')} in results!")
            all_valid = False
            
    if all_valid and len(collected) == kospi_kosdaq_count:
        print("\nSUCCESS: Filter logic works correctly.")
    else:
        print("\nFAILURE: count mismatch or invalid item found.")
        print(f"Collected: {len(collected)}, Expected: {kospi_kosdaq_count}")

if __name__ == "__main__":
    verify_market_filter()
