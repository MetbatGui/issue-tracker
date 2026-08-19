"""파서 교체 검증 스크립트"""
import sys
import glob
import os
from pathlib import Path

# src 모듈 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.infrastructure import ConvertibleBondXmlParser

def verify_parser_upgrade():
    sys.stdout.reconfigure(encoding='utf-8')
    
    xml_dir = "data/전환사채/xml"
    xml_files = glob.glob(os.path.join(xml_dir, "*.xml"))
    
    print(f"Total XML files: {len(xml_files)}")
    
    success_count = 0
    failure_count = 0
    maturity_date_count = 0
    
    for xml_file in xml_files:
        decision = ConvertibleBondXmlParser.parse(xml_file)
        
        if decision:
            success_count += 1
            if decision.maturity_date:
                maturity_date_count += 1
            else:
                print(f"⚠️ No Maturity Date: {os.path.basename(xml_file)}")
        else:
            failure_count += 1
            print(f"❌ Failed: {os.path.basename(xml_file)}")
            
    print("-" * 20)
    print(f"Success: {success_count}")
    print(f"Failure: {failure_count}")
    print(f"Parsing Rate: {success_count / len(xml_files) * 100:.2f}%")
    print(f"Maturity Date Rate: {maturity_date_count / success_count * 100:.2f}% ({maturity_date_count}/{success_count})")

if __name__ == "__main__":
    verify_parser_upgrade()
