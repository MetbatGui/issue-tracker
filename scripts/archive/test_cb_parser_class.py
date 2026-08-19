"""전환사채 XML 파서 테스트"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.infrastructure.convertible_bond_xml_parser import ConvertibleBondXmlParser


def test_cb_parser():
    """전환사채 XML 파서 테스트"""
    sys.stdout.reconfigure(encoding='utf-8')
    
    xml_path = 'data/전환사채/xml/성호전자_20260106000570.xml'
    
    print('=' * 80)
    print('🔍 전환사채 XML 파서 테스트')
    print('=' * 80)
    print(f'파일: {xml_path}\n')
    
    # 파싱
    decision = ConvertibleBondXmlParser.parse(xml_path)
    
    if decision:
        print('✅ 파싱 성공!\n')
        print('📊 추출된 데이터:')
        print('-' * 80)
        
        # 모든 필드 출력
        fields = [
            ('상호', decision.company_name),
            ('회차', decision.sequence_number),
            ('종류', decision.bond_type),
            ('사채의 권면총액', f'{decision.face_value_total:,}원' if decision.face_value_total else None),
            ('자금조달의 목적', decision.funding_purpose),
            ('사채의 이율', f'{decision.interest_rate}%' if decision.interest_rate is not None else None),
            ('사채의 만기일', decision.maturity_date),
            ('사채발행방법', decision.issue_method),
            ('전환비율', f'{decision.conversion_ratio}%' if decision.conversion_ratio is not None else None),
            ('전환가액', f'{decision.conversion_price:,}원' if decision.conversion_price else None),
            ('전환주식수', f'{decision.conversion_shares:,}주' if decision.conversion_shares else None),
            ('주식총수 대비 비율', f'{decision.shares_ratio}%' if decision.shares_ratio is not None else None),
            ('전환청구기간시작일', decision.conversion_start_date),
            ('전환청구기간종료일', decision.conversion_end_date),
            ('청약일', decision.subscription_date),
            ('납입일', decision.payment_date),
            ('이사회결의일', decision.board_resolution_date),
            ('보고서명', decision.report_name),
            ('정정여부', '정정' if decision.is_correction else '최초'),
            ('접수번호', decision.rcept_no),
            ('공시일', decision.disclosure_date),
        ]
        
        for name, value in fields:
            print(f'{name:20s}: {value}')
        
        # 검증
        print('\n\n✅ 검증 결과:')
        print('-' * 80)
        
        required_fields = [
            decision.company_name,
            decision.sequence_number,
            decision.bond_type,
            decision.face_value_total,
            decision.conversion_price,
            decision.conversion_shares,
            decision.board_resolution_date,
        ]
        
        filled = sum(1 for f in required_fields if f is not None)
        print(f'필수 필드 채워짐: {filled}/{len(required_fields)}개')
        
        return decision
    else:
        print('❌ 파싱 실패')
        return None


if __name__ == '__main__':
    test_cb_parser()
