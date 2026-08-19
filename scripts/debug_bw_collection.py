"""신주인수권부사채 API 수집 디버깅 스크립트"""
import os
import sys
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from dotenv import load_dotenv
from src.infrastructure.dart_api import DartApiClient

def debug_collection():
    load_dotenv()
    api_key = os.getenv("DART_API_KEY")
    if not api_key:
        print("[Error] DART_API_KEY가 설정되지 않았습니다.")
        return

    client = DartApiClient(api_key=api_key)
    
    # 2024년 1월 1일부터 1주일만 테스트
    start_date = "20240101"
    end_date = "20240107"
    
    print(f">>> API 직접 호출 테스트: {start_date} ~ {end_date}")
    try:
        reports = client.collect_bond_with_warrant_reports(start_date, end_date)
        print(f">>> 수집 성공: {len(reports)}건")
        for r in reports:
            print(f"  - {r.get('corp_name')}: {r.get('report_nm')}")
    except Exception as e:
        print(f">>> 에러 발생: {e}")

if __name__ == "__main__":
    debug_collection()
