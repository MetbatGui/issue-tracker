"""전환사채발행결정 vs 전환사채권발행결정 비교 조사"""
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
import requests
from collections import defaultdict

def compare_cb_report_types():
    """전환사채발행결정과 전환사채권발행결정을 비교 조사합니다."""
    sys.stdout.reconfigure(encoding='utf-8')
    load_dotenv()
    
    api_key = os.getenv('DART_API_KEY')
    if not api_key:
        print('DART_API_KEY 환경변수가 설정되지 않았습니다.')
        return
    
    # 최근 3개월간 검색
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=90)).strftime('%Y%m%d')
    
    print(f'조사 기간: {start_date} ~ {end_date}')
    print('=' * 80)
    
    url = 'https://opendart.fss.or.kr/api/list.json'
    params = {
        'crtfc_key': api_key,
        'bgn_de': start_date,
        'end_de': end_date,
        'pblntf_ty': 'B',  # 주요사항보고서
        'page_no': 1,
        'page_count': 100
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    if data['status'] != '000':
        print(f'API 오류: {data}')
        return
    
    # 전환사채 관련 공시 분류
    cb_with_gwon = []  # 전환사채권발행결정
    cb_without_gwon = []  # 전환사채발행결정
    other_cb = []  # 기타 전환사채 관련
    
    for item in data.get('list', []):
        report_nm = item.get('report_nm', '')
        
        if '전환사채권발행결정' in report_nm:
            cb_with_gwon.append(item)
        elif '전환사채발행결정' in report_nm:
            cb_without_gwon.append(item)
        elif '전환사채' in report_nm:
            other_cb.append(item)
    
    print(f'\n📊 검색 결과:')
    print('=' * 80)
    print(f'1. "전환사채권발행결정" 포함: {len(cb_with_gwon)}건')
    print(f'2. "전환사채발행결정" 포함 (권 제외): {len(cb_without_gwon)}건')
    print(f'3. 기타 전환사채 관련: {len(other_cb)}건')
    
    if cb_with_gwon:
        print(f'\n\n📋 전환사채권발행결정 예시 (최대 5건):')
        print('-' * 80)
        for i, item in enumerate(cb_with_gwon[:5], 1):
            print(f'{i}. {item["corp_name"]} - {item["report_nm"]}')
    
    if cb_without_gwon:
        print(f'\n\n📋 전환사채발행결정 (권 제외) 예시 (최대 5건):')
        print('-' * 80)
        for i, item in enumerate(cb_without_gwon[:5], 1):
            print(f'{i}. {item["corp_name"]} - {item["report_nm"]}')
    
    if other_cb:
        print(f'\n\n📋 기타 전환사채 관련 공시 유형:')
        print('-' * 80)
        other_types = defaultdict(int)
        for item in other_cb:
            other_types[item['report_nm']] += 1
        
        for report_nm, count in sorted(other_types.items(), key=lambda x: x[1], reverse=True):
            print(f'{report_nm}: {count}건')
    
    # 결론
    print(f'\n\n💡 결론:')
    print('=' * 80)
    if len(cb_with_gwon) > 0 and len(cb_without_gwon) == 0:
        print('✅ DART에서는 "전환사채권발행결정"만 사용됩니다.')
        print('   "전환사채발행결정" (권 제외)은 존재하지 않습니다.')
    elif len(cb_without_gwon) > 0:
        print('⚠️  "전환사채발행결정" (권 제외)도 존재합니다!')
        print('   두 가지 유형을 모두 수집해야 합니다.')
    else:
        print('❌ 최근 3개월간 전환사채 관련 공시가 없습니다.')

if __name__ == '__main__':
    compare_cb_report_types()
