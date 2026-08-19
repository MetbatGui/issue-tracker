import os
import shutil
from pathlib import Path

def archive_unused_scripts():
    scripts_dir = Path("scripts")
    archive_dir = scripts_dir / "archive"
    archive_dir.mkdir(exist_ok=True)
    
    # List of files to keep (active util scripts)
    keep_files = [
        "verify_weekly_collection.py", # Useful for periodic checks
        "cleanup_scripts.py",          # This script
        "__init__.py"
    ]
    
    # List of known temporary/analysis scripts to archive
    files_to_archive = [
        "inspect_xml_structure.py",
        "analyze_cb_xml.py",
        "analyze_cb_xml_fields.py",
        "check_correction_reports.py",
        "check_excel_parent.py",
        "check_funding_fields.py",
        "check_maturity_date.py",
        "compare_cb_types.py",
        "debug_correction_history.py",
        "fetch_cb_example.py",
        "investigate_all_funding.py",
        "search_cb_all_types.py",
        "test_cb_collection.py",
        "test_cb_excel_writer.py",
        "test_cb_parser_class.py",
        "test_cb_parser_prototype.py",
        "test_cb_service.py",
        "verify_parser.py"
    ]
    
    print(f"Archiving scripts to {archive_dir}...")
    
    count = 0
    for filename in files_to_archive:
        src = scripts_dir / filename
        if src.exists():
            dst = archive_dir / filename
            try:
                shutil.move(str(src), str(dst))
                print(f"  Moved: {filename}")
                count += 1
            except Exception as e:
                print(f"  Failed to move {filename}: {e}")
                
    print(f"Done. Archived {count} files.")

if __name__ == "__main__":
    archive_unused_scripts()
