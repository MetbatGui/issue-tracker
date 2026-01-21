
import os
import sys
import shutil
import json
from pathlib import Path

# Add project root to path
sys.path.append(os.getcwd())

from src.application.capital_increase_services import CapitalIncreaseService

def verify_full_history_flow():
    # Setup test directory
    test_dir = Path("data/test_history_flow")
    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir(parents=True)
    
    print(f"Test Directory: {test_dir}")
    
    # Initialize Service
    service = CapitalIncreaseService(
        data_directory=str(test_dir),
        enable_google_drive=False
    )
    
    # Target: Crowdworks Final Report (2026-01-16)
    start_date = "20260116"
    end_date = "20260116"
    
    print(f"\n[Step 1] Downloading reports for {start_date}...")
    # Now returns (files, map)
    downloaded, relation_map = service.download_reports(start_date, end_date)
    
    print(f"Downloaded files: {len(downloaded)}")
    print(f"In-Memory Map: {json.dumps(relation_map, indent=2)}")

    # Verify Map Content (In-Memory)
    if relation_map.get("20260116000463") == "20251230000646":
        print("[SUCCESS] Final -> Intermediate link found in memory.")
    else:
        print(f"[FAILURE] Final -> Intermediate link MISSING in memory.")
        
    # Verify XMLs
    print("\n[Step 2] Verifying downloaded XMLs...")
    expected_ids = ["20260116000463", "20251230000646", "20251216000521"]
    xml_files = list((test_dir / "xml").glob("*.xml"))
    found_ids = []
    for f in xml_files:
        for eid in expected_ids:
            if eid in f.name:
                found_ids.append(eid)
    
    if set(expected_ids).issubset(set(found_ids)):
        print(f"[SUCCESS] All expected XMLs found: {expected_ids}")
    else:
        print(f"[FAILURE] Missing XMLs. Found: {found_ids}")

    # Verify Parsing & Excel Persistance
    print("\n[Step 3] Parsing and Exporting to Excel...")
    # Logic: daily_update flow -> download returns map -> merge_and_save uses map -> write to excel
    # Here we simulate the daily update flow manually
    
    new_decisions = []
    for xml_file in xml_files:
        decision = service._parse_file_with_map(str(xml_file), relation_map)
        if decision:
            new_decisions.append(decision)
            
    service._merge_and_save(new_decisions, relation_map)
    
    excel_path = test_dir / "유상증자.xlsx"
    if excel_path.exists():
        print(f"[SUCCESS] Excel file created at {excel_path}")
        
        # Verify persistence
        print("\n[Step 4] Verifying Persistence (Load from Excel)...")
        loaded_map = service._load_map_from_excel()
        print(f"Loaded Map from Excel: {json.dumps(loaded_map, indent=2)}")
        
        if loaded_map.get("20260116000463") == "20251230000646":
            print("[SUCCESS] Relation persisted in Excel.")
        else:
            print("[FAILURE] Relation NOT persisted in Excel.")
            
    else:
        print("[FAILURE] Excel file NOT found.")

if __name__ == "__main__":
    verify_full_history_flow()
