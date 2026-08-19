"""전환사채 Excel Writer 테스트"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.infrastructure.convertible_bond_xml_parser import ConvertibleBondXmlParser
from src.infrastructure.convertible_bond_excel_writer import ConvertibleBondExcelWriter


def test_cb_excel_writer():
    """전환사채 Excel Writer 테스트"""
    sys.stdout.reconfigure(encoding='utf-8')
    
    print('=' * 80)
    print('🔍 전환사채 Excel Writer 테스트')
    print('=' * 80)
    
    # 1. XML 파일 목록 가져오기
    xml_dir = Path('data/전환사채/xml')
    xml_files = list(xml_dir.glob('*.xml'))
    
    print(f'\nXML 파일 수: {len(xml_files)}개')
    
    # 2. XML 파싱
    print('\n📊 XML 파싱 중...')
    decisions = []
    
    for xml_file in xml_files[:10]:  # 테스트용으로 10개만
        decision = ConvertibleBondXmlParser.parse(str(xml_file))
        if decision:
            decisions.append(decision)
    
    print(f'파싱 성공: {len(decisions)}건')
    
    # 3. Excel 저장
    print('\n💾 Excel 저장 중...')
    writer = ConvertibleBondExcelWriter(output_path='data/전환사채/전환사채_test.xlsx')
    writer.write(decisions)
    
    print('\n✅ 테스트 완료!')
    print(f'출력 파일: data/전환사채/전환사채_test.xlsx')
    
    # 4. 샘플 데이터 출력
    if decisions:
        print('\n📋 첫 번째 데이터 샘플:')
        print('-' * 80)
        d = decisions[0]
        print(f'상호: {d.company_name}')
        print(f'회차: {d.sequence_number}')
        print(f'전환가액: {d.conversion_price:,}원' if d.conversion_price else '전환가액: -')
        print(f'전환주식수: {d.conversion_shares:,}주' if d.conversion_shares else '전환주식수: -')
        print(f'이사회결의일: {d.board_resolution_date}')


if __name__ == '__main__':
    test_cb_excel_writer()
