"""신주인수권부사채 수집 및 엑셀 저장 테스트 스크립트"""
import os
import sys
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from dotenv import load_dotenv
from src.application.bond_with_warrant_service import BondWithWarrantService

def test_bw_collection():
    load_dotenv()
    api_key = os.getenv("DART_API_KEY")
    if not api_key:
        print("[Error] DART_API_KEY가 설정되지 않았습니다.")
        return

    # 최근 1개월 데이터 수집 테스트
    service = BondWithWarrantService(api_key)
    
    # 최근 1개월 데이터 수집 테스트
    print(">>> 신주인수권부사채 수집 테스트 시작...", flush=True)
    service.parse_and_export_to_excel(start_date="20251220")
    print(">>> 테스트 완료.", flush=True)

if __name__ == "__main__":
    test_bw_collection()
