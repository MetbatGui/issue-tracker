import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.infrastructure import DartApiClient
from datetime import datetime, timedelta

def check_correction_reports():
    sys.stdout.reconfigure(encoding='utf-8')
    client = DartApiClient()
    
    today = datetime.now()
    start_date = (today - timedelta(days=60)).strftime('%Y%m%d') # Check 2 months
    end_date = today.strftime('%Y%m%d')
    
    print(f"Checking reports from {start_date} to {end_date}...")
    
    reports = client.collect_convertible_bond_reports(start_date, end_date)
    
    correction_count = 0
    for report in reports:
        if "기재정정" in report.get("report_nm", ""):
            correction_count += 1
            print(f"[FOUND] {report.get('corp_name')} - {report.get('report_nm')} ({report.get('rcept_no')})")
            
    print(f"Total reports: {len(reports)}")
    print(f"Correction reports: {correction_count}")

if __name__ == "__main__":
    check_correction_reports()
