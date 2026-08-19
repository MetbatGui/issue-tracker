"""전환사채 공시 유형 조사"""
import os
import sys
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from collections import defaultdict

def investigate_convertible_bond_types():
    """전환사채 관련 공시 유형을 조사합니다."""
    load_dotenv()
    api_key = os.getenv('DART_API_KEY')
    if not api_key:
        print('DART_API_KEY 환경변수가 설정되지 않았습니다. .env 파일을 확인하세요.')
        return None
    
    # 최근 3개월간 전환사채 관련 공시 검색 (API 제한)
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
        return None
    
    # 전환사채 관련 공시 유형 집계
    cb_types = defaultdict(lambda: {'count': 0, 'examples': []})
    
    for item in data.get('list', []):
        report_nm = item.get('report_nm', '')
        if '전환사채' in report_nm:
            cb_types[report_nm]['count'] += 1
            if len(cb_types[report_nm]['examples']) < 3:
                cb_types[report_nm]['examples'].append({
                    'corp_name': item['corp_name'],
                    'rcept_no': item['rcept_no'],
                    'rcept_dt': item['rcept_dt']
                })
    
    print(f'\n전환사채 관련 공시 유형 ({len(cb_types)}개):')
    print('=' * 80)
    
    for report_nm, info in sorted(cb_types.items(), key=lambda x: x[1]['count'], reverse=True):
        print(f'\n📋 {report_nm} ({info["count"]}건)')
        print('   예시:')
        for ex in info['examples']:
            print(f'   - {ex["corp_name"]} ({ex["rcept_dt"]}) - {ex["rcept_no"]}')
    
    # 첫 번째 유형의 첫 번째 예시 XML 다운로드
    if cb_types:
        first_type = sorted(cb_types.items(), key=lambda x: x[1]['count'], reverse=True)[0]
        report_nm, info = first_type
        
        if info['examples']:
            example = info['examples'][0]
            rcept_no = example['rcept_no']
            corp_name = example['corp_name']
            
            print(f'\n\n예시 XML 다운로드 중...')
            print(f'공시: {report_nm}')
            print(f'회사: {corp_name}')
            print(f'접수번호: {rcept_no}')
            
            xml_url = 'https://opendart.fss.or.kr/api/document.xml'
            xml_params = {
                'crtfc_key': api_key,
                'rcept_no': rcept_no
            }
            
            xml_response = requests.get(xml_url, params=xml_params)
            
            # XML 파일 저장
            output_path = f'data/전환사채/example_{rcept_no}.xml'
            os.makedirs('data/전환사채', exist_ok=True)
            
            with open(output_path, 'wb') as f:
                f.write(xml_response.content)
            
            print(f'\n✅ XML 저장 완료: {output_path}')
            print(f'   파일 크기: {len(xml_response.content):,} bytes')
            
            return output_path
    
    return None

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    investigate_convertible_bond_types()
