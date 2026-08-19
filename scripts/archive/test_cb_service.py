"""전환사채 서비스 통합 테스트"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.application.convertible_bond_service import ConvertibleBondService
from datetime import datetime, timedelta


def test_convertible_bond_service():
    """전환사채 서비스 통합 테스트"""
    sys.stdout.reconfigure(encoding='utf-8')
    
    print('=' * 80)
    print('🔍 전환사채 서비스 통합 테스트')
    print('=' * 80)
    
    # 서비스 초기화
    service = ConvertibleBondService()
    
    # 최근 1개월 데이터 수집
    today = datetime.now()
    start_date = (today - timedelta(days=30)).strftime('%Y%m%d')
    end_date = today.strftime('%Y%m%d')
    
    print(f'\n📆 수집 기간: {start_date} ~ {end_date}')
    
    # Daily 업데이트 실행
    service.daily_update(days_back=30)
    
    print('\n✅ 테스트 완료!')
    print(f'출력 파일: data/전환사채/전환사채.xlsx')


if __name__ == '__main__':
    test_convertible_bond_service()
