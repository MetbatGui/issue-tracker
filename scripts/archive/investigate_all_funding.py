"""전환사채 XML에서 모든 자금 관련 필드 조사"""
import sys
from pathlib import Path
from lxml import etree
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

def investigate_all_funding_fields():
    """여러 XML 파일에서 자금 관련 필드 조사"""
    sys.stdout.reconfigure(encoding='utf-8')
    
    xml_dir = Path('data/전환사채/xml')
    xml_files = list(xml_dir.glob('*.xml'))[:20]  # 20개 파일 조사
    
    print('=' * 80)
    print('🔍 전환사채 자금 관련 필드 전체 조사')
    print('=' * 80)
    print(f'조사 파일 수: {len(xml_files)}개\n')
    
    # 모든 자금 관련 ACODE 수집
    all_fund_codes = defaultdict(int)
    fund_examples = defaultdict(list)
    
    for xml_file in xml_files:
        try:
            parser = etree.XMLParser(recover=True)
            tree = etree.parse(str(xml_file), parser)
            root = tree.getroot()
            
            all_te = root.findall('.//TE[@ACODE]')
            
            for node in all_te:
                acode = node.get('ACODE')
                if 'FND' in acode or 'ANC' in acode:
                    text = node.text.strip() if node.text else '-'
                    if text != '-':  # 값이 있는 경우만
                        all_fund_codes[acode] += 1
                        if len(fund_examples[acode]) < 3:
                            fund_examples[acode].append((xml_file.stem, text))
        except:
            pass
    
    print('📊 발견된 자금 관련 ACODE (값이 있는 경우):')
    print('-' * 80)
    
    for code, count in sorted(all_fund_codes.items(), key=lambda x: x[1], reverse=True):
        print(f'\n{code}: {count}건')
        for file, val in fund_examples[code]:
            print(f'  - {file}: {val}')
    
    # 매핑 추천
    print('\n\n💡 칼럼 매핑 추천:')
    print('-' * 80)
    mapping = {
        'FND_USE1': '시설자금',
        'FND_USE2': '운영자금',
        'FND_USE3': '기타자금',
        'FND_USE_SQ': '영업양수자금',
        'FND_USE_RD': '채무상환자금',
        'ANC_ACQ_PRC': '타법인증권 취득자금'
    }
    
    for code, name in mapping.items():
        count = all_fund_codes.get(code, 0)
        print(f'{code:15s} → {name:20s} ({count}건)')

if __name__ == '__main__':
    investigate_all_funding_fields()
