"""전환사채 XML 파서 프로토타입 테스트"""
import sys
from pathlib import Path
from lxml import etree
import re
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

def clean_number(text):
    """숫자 문자열 정제 (쉼표 제거)"""
    if not text or text == '-':
        return None
    try:
        return int(text.replace(',', '').replace(' ', ''))
    except:
        return None

def clean_float(text):
    """실수 문자열 정제"""
    if not text or text == '-':
        return None
    try:
        return float(text.replace(',', '').replace(' ', ''))
    except:
        return None

def parse_korean_date(text):
    """한글 날짜 파싱: '2029년 01월 07일' -> '2029-01-07'"""
    if not text or text == '-':
        return None
    try:
        # 정규식으로 년월일 추출
        match = re.search(r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일', text)
        if match:
            year, month, day = match.groups()
            return f'{year}-{month.zfill(2)}-{day.zfill(2)}'
    except:
        pass
    return None

def test_parse_cb_xml():
    """전환사채 XML 파싱 테스트"""
    sys.stdout.reconfigure(encoding='utf-8')
    
    xml_path = 'data/전환사채/xml/성호전자_20260106000570.xml'
    
    print('=' * 80)
    print('🔍 전환사채 XML 파싱 테스트')
    print('=' * 80)
    print(f'파일: {xml_path}\n')
    
    try:
        parser = etree.XMLParser(recover=True)
        tree = etree.parse(xml_path, parser)
        root = tree.getroot()
        
        # 데이터 추출
        data = {}
        
        # 1. 상호
        company_node = root.find('.//COMPANY-NAME')
        data['상호'] = company_node.text if company_node is not None else None
        
        # 2. 회차
        seq_node = root.find(".//TE[@ACODE='SEQ_NO']")
        data['회차'] = seq_node.text if seq_node is not None else None
        
        # 3. 종류
        kind_node = root.find(".//TE[@ACODE='PL_KND']")
        data['종류'] = kind_node.text if kind_node is not None else None
        
        # 4. 사채의 권면(전자등록)총액
        dnm_node = root.find(".//TE[@ACODE='DNM_SUM']")
        data['사채의 권면(전자등록)총액'] = clean_number(dnm_node.text if dnm_node is not None else None)
        
        # 5. 권면(전자등록)총액 (동일)
        data['권면(전자등록)총액'] = data['사채의 권면(전자등록)총액']
        
        # 6. 자금조달의 목적
        fund_node = root.find(".//TE[@ACODE='ANC_ACQ_PRC']")
        data['자금조달의 목적'] = fund_node.text if fund_node is not None else None
        
        # 7. 사채의 이율
        rate_node = root.find(".//TE[@ACODE='PRFT_RATE']")
        data['사채의 이율'] = clean_float(rate_node.text if rate_node is not None else None)
        
        # 8. 사채의 만기일
        exp_node = root.find(".//TU[@AUNIT='EXP_DT']")
        data['사채의 만기일'] = parse_korean_date(exp_node.text if exp_node is not None else None)
        
        # 9. 사채발행방법
        method_node = root.find(".//TU[@AUNIT='ISSU_MTH']")
        data['사채발행방법'] = method_node.text if method_node is not None else None
        
        # 10. 전환비율
        exe_rt_node = root.find(".//TE[@ACODE='EXE_RT']")
        data['전환비율'] = clean_float(exe_rt_node.text if exe_rt_node is not None else None)
        
        # 11. 전환가액
        exe_prc_node = root.find(".//TE[@ACODE='EXE_PRC']")
        data['전환가액'] = clean_number(exe_prc_node.text if exe_prc_node is not None else None)
        
        # 12. 전환에 따라 발행할 주식수
        stk_cnt_node = root.find(".//TE[@ACODE='STK_CNT']")
        data['전환에 따라 발행할 주식수'] = clean_number(stk_cnt_node.text if stk_cnt_node is not None else None)
        
        # 13. 주식총수 대비 비율
        stk_rt_node = root.find(".//TE[@ACODE='STK_RT']")
        data['주식총수 대비 비율'] = clean_float(stk_rt_node.text if stk_rt_node is not None else None)
        
        # 14. 전환청구기간시작일
        sb_bgn_node = root.find(".//TU[@AUNIT='SB_BGN_DT']")
        data['전환청구기간시작일'] = parse_korean_date(sb_bgn_node.text if sb_bgn_node is not None else None)
        
        # 15. 전환청구기간종료일
        sb_end_node = root.find(".//TU[@AUNIT='SB_END_DT']")
        data['전환청구기간종료일'] = parse_korean_date(sb_end_node.text if sb_end_node is not None else None)
        
        # 16. 청약일
        sbsc_node = root.find(".//TU[@AUNIT='SBSC_DT']")
        data['청약일'] = parse_korean_date(sbsc_node.text if sbsc_node is not None else None)
        
        # 17. 납입일
        pym_node = root.find(".//TU[@AUNIT='PYM_DT']")
        data['납입일'] = parse_korean_date(pym_node.text if pym_node is not None else None)
        
        # 18. 이사회결의일
        drc_node = root.find(".//TU[@AUNIT='DRC_DT']")
        data['이사회결의일'] = parse_korean_date(drc_node.text if drc_node is not None else None)
        
        # 결과 출력
        print('📊 추출된 데이터:')
        print('-' * 80)
        
        for key, value in data.items():
            print(f'{key:25s}: {value}')
        
        # 검증
        print('\n\n✅ 검증 결과:')
        print('-' * 80)
        
        missing = [key for key, value in data.items() if value is None]
        found = [key for key, value in data.items() if value is not None]
        
        print(f'추출 성공: {len(found)}/18개')
        print(f'추출 실패: {len(missing)}/18개')
        
        if missing:
            print(f'\n누락된 칼럼:')
            for col in missing:
                print(f'  - {col}')
        
        return data
        
    except Exception as e:
        print(f'오류 발생: {e}')
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    test_parse_cb_xml()
