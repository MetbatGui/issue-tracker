
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from src.infrastructure.dart_history_scraper import DartHistoryScraper

def verify_scraper():
    scraper = DartHistoryScraper()
    
    # Crowdworks Final Report
    target_rcp = "20260116000463"
    
    print(f"Scraping history for: {target_rcp} (Crowdworks)")
    
    history_ids = scraper.get_history_rcp_list(target_rcp)
    
    print(f"Found IDs: {history_ids}")
    
    expected_intermediate = "20251230000646"
    expected_original = "20251216000521"
    
    if expected_intermediate in history_ids:
        print(f"[SUCCESS] Intermediate report {expected_intermediate} FOUND.")
    else:
        print(f"[FAILURE] Intermediate report {expected_intermediate} NOT found.")
        
    if expected_original in history_ids:
        print(f"[SUCCESS] Original report {expected_original} FOUND.")
    else:
        print(f"[FAILURE] Original report {expected_original} NOT found.")

    # Check for UNRELATED Hanwha report
    unrelated_hanwha_id = "20251216000256"
    if unrelated_hanwha_id not in history_ids:
        print(f"[SUCCESS] Unrelated Hanwha report {unrelated_hanwha_id} CORRECTLY EXCLUDED.")
    else:
        print(f"[FAILURE] Unrelated Hanwha report {unrelated_hanwha_id} INCORRECTLY INCLUDED.")

if __name__ == "__main__":
    verify_scraper()
