import os
import sys
import glob
from collections import Counter
from parser import DartXmlParser

# UTF-8 인코딩 설정 (윈도우 콘솔용)
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = "data/유상증자/xml"

def main():
    xml_files = glob.glob(os.path.join(BASE_DIR, "*.xml"))
    print(f"📂 총 {len(xml_files)}개의 XML 파일이 있습니다.\n")
    
    years = []
    successful_parses = 0
    failed_parses = 0
    filtered_companies = 0
    
    for xml_file in xml_files:
        decision = DartXmlParser.parse(xml_file)
        
        if decision:
            successful_parses += 1
            
            # 필터링: '유한책임회사' 제외
            if "유한책임회사" in decision.company_name:
                filtered_companies += 1
                continue
            
            if decision.disclosure_date:
                year = decision.disclosure_date.year
                years.append(year)
        else:
            failed_parses += 1
    
    print(f"✅ 성공적으로 파싱된 파일: {successful_parses}개")
    print(f"❌ 파싱 실패한 파일: {failed_parses}개")
    print(f"🚫 '유한책임회사'로 필터링된 항목: {filtered_companies}개")
    print(f"📊 최종 데이터 개수: {len(years)}개\n")
    
    # 연도별 분포
    year_counts = Counter(years)
    print("연도별 데이터 분포:")
    for year in sorted(year_counts.keys()):
        print(f"  {year}년: {year_counts[year]}건")
    
    print(f"\n총 {len(year_counts)}개의 연도: {sorted(year_counts.keys())}")

if __name__ == "__main__":
    main()
