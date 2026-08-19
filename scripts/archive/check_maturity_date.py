"""사채 만기일(EXP_DT) 파싱 여부 확인 스크립트"""
import glob
import os
import xml.etree.ElementTree as ET

def check_maturity_date_parsing():
    xml_dir = "data/전환사채/xml"
    xml_files = glob.glob(os.path.join(xml_dir, "*.xml"))
    
    print(f"Total XML files: {len(xml_files)}")
    
    missing_exp_dt = []
    
    for xml_file in xml_files:
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            exp_node = root.find(".//TU[@AUNIT='EXP_DT']")
            if exp_node is None:
                missing_exp_dt.append(os.path.basename(xml_file))
                
        except Exception as e:
            print(f"Error parsing {xml_file}: {e}")
            
    print(f"Files missing EXP_DT: {len(missing_exp_dt)}")
    
    if missing_exp_dt:
        print("\nTOP 5 Files missing EXP_DT:")
        for f in missing_exp_dt[:5]:
            print(f"- {f}")
            
    # 통계
    success_rate = (len(xml_files) - len(missing_exp_dt)) / len(xml_files) * 100
    print(f"\nParsing Success Rate: {success_rate:.2f}%")

if __name__ == "__main__":
    check_maturity_date_parsing()
