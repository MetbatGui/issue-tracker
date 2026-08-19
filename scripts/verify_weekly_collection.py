"""
일주일치 데이터 수집을 통해 DART 연결 안정성을 검증하는 스크립트입니다.
(전환사채 수집 버전)
"""
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.application.convertible_bond_service import ConvertibleBondService

def verify_weekly_collection():
    print("=" * 60)
    print("🧪 DART 연결 안정성 검증 (최근 7일 - 전환사채)")
    print("=" * 60)

    # 1. Setup Service
    # Note: enable_google_drive=False to avoid unnecessary uploads during test
    service = ConvertibleBondService(
        data_directory="data/verification_test_cb",
        enable_google_drive=False 
    )

    # 2. Date Range (Last 7 days)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    start_str = start_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")
    
    print(f"기간: {start_str} ~ {end_str}")
    
    try:
        # 3. Process
        # download_reports_with_history runs the collection and specifically triggers 
        # the history scraper when it finds correction reports.
        downloaded, relation_map = service.download_reports_with_history(
            service.api_client.collect_convertible_bond_reports,
            start_date=start_str,
            end_date=end_str
        )
        
        print("\n✅ 검증 완료: 예외 발생 없음")
        print(f"다운로드된 파일 수: {len(downloaded)}")
        print(f"수집된 관계 수: {len(relation_map)}")

    except Exception as e:
        print(f"\n❌ 검증 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_weekly_collection()

