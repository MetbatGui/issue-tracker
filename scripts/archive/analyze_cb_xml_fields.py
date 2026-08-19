"""전환사채 XML 파싱 테스트 - 필요한 칼럼 추출 확인"""
import sys
from pathlib import Path
from lxml import etree
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

def check_required_columns():
    """엑셀 칼럼 구조와 XML에서 추출 가능한 데이터 확인"""
    sys.stdout.reconfigure(encoding='utf-8')
    
    # 1. 엑셀 칼럼 구조 확인
    print('=' * 80)
    print('📋 전환사채 엑셀 필요 칼럼 목록')
    print('=' * 80)
    
    df = pd.read_excel('data/전환사채/전환사채.xlsx', header=1)
    required_columns = df.columns.tolist()
    
    for i, col in enumerate(required_columns, 1):
        print(f'{i:2d}. {col}')
    
    # 2. XML 샘플 분석
    print('\n\n' + '=' * 80)
    print('🔍 XML 샘플 분석 (성호전자_20260106000570.xml)')
    print('=' * 80)
    
    xml_path = 'data/전환사채/xml/성호전자_20260106000570.xml'
    
    try:
        parser = etree.XMLParser(recover=True)
        tree = etree.parse(xml_path, parser)
        root = tree.getroot()
        
        # 회사명
        company_node = root.find('.//COMPANY-NAME')
        company_name = company_node.text if company_node is not None else None
        print(f'\n회사명: {company_name}')
        
        # 보고서명
        doc_name_node = root.find('.//DOCUMENT-NAME')
        doc_name = doc_name_node.text if doc_name_node is not None else None
        print(f'보고서명: {doc_name}')
        
        # 모든 TE, TU 태그 찾기 (ACODE, AUNIT 속성 확인)
        print('\n\n📊 XML에서 발견된 주요 데이터 필드:')
        print('-' * 80)
        
        # TE 태그 (ACODE)
        te_nodes = root.findall('.//TE[@ACODE]')
        print(f'\n[TE 태그 - ACODE 속성] ({len(te_nodes)}개)')
        
        te_data = {}
        for node in te_nodes:
            acode = node.get('ACODE')
            text = node.text.strip() if node.text else ''
            if text:
                te_data[acode] = text
                print(f'  {acode}: {text[:50]}...' if len(text) > 50 else f'  {acode}: {text}')
        
        # TU 태그 (AUNIT)
        tu_nodes = root.findall('.//TU[@AUNIT]')
        print(f'\n[TU 태그 - AUNIT 속성] ({len(tu_nodes)}개)')
        
        tu_data = {}
        for node in tu_nodes:
            aunit = node.get('AUNIT')
            text = node.text.strip() if node.text else ''
            if text:
                tu_data[aunit] = text
                print(f'  {aunit}: {text[:50]}...' if len(text) > 50 else f'  {aunit}: {text}')
        
        # 3. 칼럼 매핑 가능성 분석
        print('\n\n' + '=' * 80)
        print('🔗 칼럼 매핑 가능성 분석')
        print('=' * 80)
        
        # 예상 매핑
        mapping_hints = {
            '상호': 'COMPANY-NAME 태그',
            '회차': 'TE[@ACODE] 중 회차 관련',
            '종류': 'TE[@ACODE] 중 종류 관련',
            '사채의 권면(전자등록)총액': 'TE[@ACODE] 중 총액 관련',
            '전환비율': 'TE[@ACODE] 중 비율 관련',
            '전환가액': 'TE[@ACODE] 중 가액 관련',
            '전환에 따라 발행할 주식수': 'TE[@ACODE] 중 주식수 관련',
            '이사회결의일': 'TU[@AUNIT] 중 날짜 관련',
        }
        
        print('\n예상 매핑:')
        for col, hint in mapping_hints.items():
            print(f'  {col} ← {hint}')
        
        return te_data, tu_data, required_columns
        
    except Exception as e:
        print(f'오류 발생: {e}')
        import traceback
        traceback.print_exc()
        return None, None, required_columns

if __name__ == '__main__':
    check_required_columns()
