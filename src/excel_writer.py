import os
import sys
import glob
import pandas as pd
from parser import DartXmlParser

# UTF-8 인코딩 설정 (윈도우 콘솔용)
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


# ==========================================
# [설정] 경로 및 파일명
# ==========================================
BASE_DIR = "data/유상증자/xml"
OUTPUT_FILE = "data/유상증자/유상증자.xlsx"

# ==========================================
# [설정] 엑셀 헤더 정의 (순서대로)
# ==========================================
EXCEL_COLUMNS = [
    "일자",                 # 공시일
    "종목명",
    "유상증자공시일",
    "신주발행주식수",       # 보통주 기준
    "1주당 액면가",
    "증자전 발행주식총수",
    "시설자금",
    "운영자금",
    "타법인증권",
    "기타자금",
    "증자방식",
    "신주의 발행가액",      # 예정 발행가
    "발행확정가액",         # (공란)
    "신주배정기준일",
    "1주당 신주배정주식수",
    "청약예정일",           # 구주주 청약 시작일 기준
    "납입일",
    "신주상장일",           # (공란)
    "이사회결의일"
]

def format_date(date_obj):
    """날짜 객체를 YYYY-MM-DD 문자열로 변환"""
    return date_obj.strftime("%Y-%m-%d") if date_obj else ""

def format_number(num):
    """숫자가 0이면 빈 문자열, 아니면 숫자 반환 (선택 사항)"""
    # 0도 엑셀에 기록하고 싶다면 그냥 num 반환
    return num

def main():
    # 1. XML 파일 목록 가져오기
    xml_files = glob.glob(os.path.join(BASE_DIR, "*.xml"))
    
    if not xml_files:
        print("❌ 처리할 XML 파일이 없습니다.")
        return

    print(f"📂 {len(xml_files)}개의 XML 파일을 처리합니다...")

    data_rows = []

    # 2. 파일 순회 및 파싱
    for xml_file in xml_files:
        decision = DartXmlParser.parse(xml_file)
        
        if decision:
            # 필터링: '유한책임회사' 제외
            if "유한책임회사" in decision.company_name:
                continue
            
            # 날짜 포맷팅
            disclosure_dt = format_date(decision.disclosure_date)
            
            row = {
                "일자": disclosure_dt,
                "종목명": decision.company_name,
                "유상증자공시일": disclosure_dt,
                "신주발행주식수": format_number(decision.new_shares.common),
                "1주당 액면가": format_number(decision.par_value),
                "증자전 발행주식총수": format_number(decision.total_shares_before),
                "시설자금": format_number(decision.funding.facility),
                "운영자금": format_number(decision.funding.operating),
                "타법인증권": format_number(decision.funding.acquisition),
                "기타자금": format_number(decision.funding.other),
                "증자방식": decision.method,
                "신주의 발행가액": format_number(decision.issue_price),
                "발행확정가액": "",  # 초기 공시에는 보통 없음
                "신주배정기준일": format_date(decision.record_date),
                "1주당 신주배정주식수": decision.assign_per_share if decision.assign_per_share > 0 else "",
                "청약예정일": format_date(decision.subscription_date),
                "납입일": format_date(decision.payment_date),
                "신주상장일": "",    # 초기 공시에는 보통 없음
                "이사회결의일": format_date(decision.board_resolution_date),
                "연도": decision.disclosure_date.year if decision.disclosure_date else None
            }
            data_rows.append(row)

    # 3. DataFrame 생성
    df = pd.DataFrame(data_rows, columns=EXCEL_COLUMNS + ["연도"])

    # 4. 연도별로 데이터 분리
    if not os.path.exists(os.path.dirname(OUTPUT_FILE)):
        os.makedirs(os.path.dirname(OUTPUT_FILE))

    # 연도 없는 데이터 필터링
    df = df[df["연도"].notna()]
    
    # 연도별로 그룹화
    years = sorted(df["연도"].unique())
    
    # 5. 엑셀 저장 (연도별 시트)
    with pd.ExcelWriter(OUTPUT_FILE, engine='openpyxl') as writer:
        for year in years:
            year_df = df[df["연도"] == year][EXCEL_COLUMNS]  # 연도 컬럼 제외
            sheet_name = str(int(year))
            year_df.to_excel(writer, sheet_name=sheet_name, index=False, startrow=1)
            print(f"  📄 {sheet_name} 시트: {len(year_df)}건")

    print(f"\n✅ 엑셀 생성 완료: {OUTPUT_FILE}")
    print(f"📊 총 {len(df)}건의 데이터가 {len(years)}개 시트에 저장되었습니다.")
    print(f"📅 생성된 시트: {', '.join([str(int(y)) for y in years])}")
    
    # 결과 미리보기 (주요 컬럼만)
    print("\n[미리보기]")
    print(df[["종목명", "증자방식", "신주발행주식수", "운영자금", "납입일", "연도"]].head())

if __name__ == "__main__":
    main()