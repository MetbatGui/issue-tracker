import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.infrastructure import DartApiClient
import lxml.etree as etree

def inspect_xml(file_path):
    print(f"Inspecting: {file_path}")
    try:
        parser = etree.XMLParser(recover=True)
        tree = etree.parse(str(file_path), parser)
        root = tree.getroot()
        
        print("\n[All Tags and Attributes]")
        for elem in root.iter():
            # Skip heavy text nodes for readability, just show attributes and tag
            attrs = ", ".join([f'{k}="{v}"' for k, v in elem.attrib.items()])
            text = elem.text.strip() if elem.text else ""
            if len(text) > 50:
                text = text[:50] + "..."
            
            # Highlight interesting tags
            prefix = "  "
            if "CLS" in elem.tag or "CODE" in elem.tag or "TYPE" in elem.tag:
                prefix = ">>"
            for k, v in elem.attrib.items():
                if "CLS" in k or "CODE" in k or "TYPE" in k or "UNIT" in k:
                     if "CLS" in v or "CODE" in v or "TYPE" in v:
                        prefix = "!!"

            print(f"{prefix} Tag: {elem.tag}, Attrs: {{{attrs}}}, Text: {text}")

    except Exception as e:
        print(f"Error parsing XML: {e}")

def main():
    # 1. Download a fresh report (Capital Increase)
    # Use a date range likely to have data
    client = DartApiClient()
    
    print("Downloading a sample report...")
    # Just grab *any* recent report to inspect structure
    # Try getting a list first to pick a valid rcept_no
    import datetime
    end_date = datetime.datetime.now().strftime("%Y%m%d")
    start_date = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime("%Y%m%d")
    
    reports = client.collect_capital_increase_reports(start_date, end_date)
    
    if not reports:
        print("No reports found in the last 7 days. Extending search...")
        start_date = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime("%Y%m%d")
        reports = client.collect_capital_increase_reports(start_date, end_date)

    if not reports:
        print("Still no reports found. Cannot verify XML structure.")
        return

    target_report = reports[0]
    rcept_no = target_report['rcept_no']
    corp_name = target_report['corp_name']
    
    print(f"Target: {corp_name} ({rcept_no})")
    
    download_path = client.download_document_xml(rcept_no, corp_name)
    
    if download_path:
        inspect_xml(download_path)
    else:
        print("Failed to download XML.")

if __name__ == "__main__":
    main()
