"""전환사채 공시를 다양한 공시 유형(pblntf_ty)으로 검색"""
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
import requests
from collections import defaultdict

def search_cb_by_all_types():
    """모든 공시 유형에서 전환사채 관련 공시를 검색합니다."""
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
    
    # 공시 유형별로 검색
    pblntf_types = {
        'A': '정기공시',
        'B': '주요사항보고',
        'C': '발행공시',
        'D': '지분공시',
        'E': '기타공시',
        'F': '외부감사관련',
        'G': '펀드공시',
        'H': '자산유동화',
        'I': '거래소공시',
        'J': '공정위공시'
    }
    
    all_results = {}
    
    for pblntf_ty, type_name in pblntf_types.items():
        print(f'\n🔍 [{pblntf_ty}] {type_name} 검색 중...')
        
        url = 'https://opendart.fss.or.kr/api/list.json'
        params = {
            'crtfc_key': api_key,
            'bgn_de': start_date,
            'end_de': end_date,
            'pblntf_ty': pblntf_ty,
            'page_no': 1,
            'page_count': 100
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if data['status'] != '000':
            print(f'   ⚠️  {data.get("message", "오류")}')
            continue
        
        # 전환사채 관련 공시 필터링
        cb_reports = []
        for item in data.get('list', []):
            report_nm = item.get('report_nm', '')
            if '전환사채' in report_nm and '발행결정' in report_nm:
                cb_reports.append(item)
        
        if cb_reports:
            all_results[type_name] = cb_reports
            print(f'   ✅ 전환사채 발행결정 관련: {len(cb_reports)}건')
            
            # 공시명 집계
            report_names = defaultdict(int)
            for item in cb_reports:
                report_names[item['report_nm']] += 1
            
            for report_nm, count in sorted(report_names.items(), key=lambda x: x[1], reverse=True):
                print(f'      - {report_nm}: {count}건')
        else:
            print(f'   ❌ 전환사채 발행결정 관련 공시 없음')
    
    # 전체 요약
    print(f'\n\n📊 전체 요약')
    print('=' * 80)
    
    total_count = sum(len(reports) for reports in all_results.values())
    print(f'총 발견 건수: {total_count}건')
    
    for type_name, reports in all_results.items():
        print(f'\n[{type_name}] {len(reports)}건')
        
        # 예시 3건
        for i, item in enumerate(reports[:3], 1):
            print(f'  {i}. {item["corp_name"]} - {item["report_nm"]}')
    
    # 결론
    print(f'\n\n💡 결론')
    print('=' * 80)
    if len(all_results) == 1 and '주요사항보고' in all_results:
        print('✅ 전환사채 발행결정은 "주요사항보고서"에만 존재합니다.')
    elif len(all_results) > 1:
        print('⚠️  전환사채 발행결정이 여러 공시 유형에 존재합니다:')
        for type_name in all_results.keys():
            print(f'   - {type_name}')

if __name__ == '__main__':
    search_cb_by_all_types()
