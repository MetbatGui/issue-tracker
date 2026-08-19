"""전환사채 XML에서 자금조달 세부 항목 확인"""
import sys
from pathlib import Path
from lxml import etree

sys.path.insert(0, str(Path(__file__).parent.parent))

def check_funding_fields():
    """자금조달 관련 필드 확인"""
    sys.stdout.reconfigure(encoding='utf-8')
    
    xml_path = 'data/전환사채/xml/성호전자_20260106000570.xml'
    
    print('=' * 80)
    print('🔍 자금조달 관련 필드 확인')
    print('=' * 80)
    print(f'파일: {xml_path}\n')
    
    try:
        parser = etree.XMLParser(recover=True)
        tree = etree.parse(xml_path, parser)
        root = tree.getroot()
        
        # 자금 관련 ACODE 찾기
        funding_codes = ['FND_USE1', 'FND_USE2', 'FND_USE3', 'ANC_ACQ_PRC', 'ANC_ACQ_AMT']
        
        print('📊 자금 관련 필드:')
        print('-' * 80)
        
        for code in funding_codes:
            nodes = root.findall(f".//TE[@ACODE='{code}']")
            if nodes:
                for i, node in enumerate(nodes, 1):
                    text = node.text.strip() if node.text else '-'
                    print(f'{code} ({i}): {text}')
        
        # 추가로 FND로 시작하는 모든 ACODE 찾기
        print('\n\n📋 모든 FND 관련 ACODE:')
        print('-' * 80)
        
        all_te = root.findall('.//TE[@ACODE]')
        fnd_codes = {}
        
        for node in all_te:
            acode = node.get('ACODE')
            if 'FND' in acode or 'ANC' in acode:
                text = node.text.strip() if node.text else '-'
                if acode not in fnd_codes:
                    fnd_codes[acode] = []
                fnd_codes[acode].append(text)
        
        for code, values in sorted(fnd_codes.items()):
            print(f'\n{code}:')
            for i, val in enumerate(values, 1):
                print(f'  {i}. {val}')
        
    except Exception as e:
        print(f'오류: {e}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    check_funding_fields()
