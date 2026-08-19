"""전환사채 데이터 수집 테스트"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.dart_api import DartApiClient


def test_collect_convertible_bonds():
    """최근 한 달간 전환사채권발행결정 공시를 수집합니다."""
    sys.stdout.reconfigure(encoding='utf-8')
    
    # 날짜 계산
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    start_str = start_date.strftime('%Y%m%d')
    end_str = end_date.strftime('%Y%m%d')
    
    print(f'전환사채 데이터 수집 테스트')
    print(f'기간: {start_str} ~ {end_str} (최근 30일)')
    print('=' * 80)
    
    # DartApiClient 초기화
    client = DartApiClient(save_directory="data/전환사채")
    
    # 전환사채 데이터 수집
    reports = client.collect_convertible_bond_reports(
        start_date=start_str,
        end_date=end_str,
        interval_days=90
    )
    
    print(f'\n\n수집 결과 요약')
    print('=' * 80)
    print(f'총 수집 건수: {len(reports)}건')
    
    if reports:
        print(f'\n수집된 공시 목록:')
        print('-' * 80)
        
        for i, report in enumerate(reports, 1):
            print(f'\n{i}. {report["corp_name"]}')
            print(f'   - 공시명: {report["report_nm"]}')
            print(f'   - 접수번호: {report["rcept_no"]}')
            print(f'   - 접수일자: {report["rcept_dt"]}')
            if 'xml_path' in report:
                print(f'   - XML: {report["xml_path"]}')
        
        # 공시 유형별 집계
        print(f'\n\n공시 유형별 집계:')
        print('-' * 80)
        
        report_types = {}
        for report in reports:
            report_nm = report['report_nm']
            report_types[report_nm] = report_types.get(report_nm, 0) + 1
        
        for report_nm, count in sorted(report_types.items(), key=lambda x: x[1], reverse=True):
            print(f'{report_nm}: {count}건')
    else:
        print('\n수집된 공시가 없습니다.')
    
    return reports


if __name__ == '__main__':
    test_collect_convertible_bonds()
