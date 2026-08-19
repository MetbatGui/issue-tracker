"""전환사채 XML 구조 분석"""
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

def analyze_cb_xml():
    """전환사채 XML 파일의 구조를 분석합니다."""
    sys.stdout.reconfigure(encoding='utf-8')
    
    xml_path = Path('data/전환사채/example_20260121000001.xml')
    
    try:
        # ZIP 파일인지 확인하고 압축 해제
        if zipfile.is_zipfile(xml_path):
            print(f'ZIP 파일 감지: {xml_path}')
            print('압축 해제 중...')
            
            with zipfile.ZipFile(xml_path, 'r') as zip_ref:
                # ZIP 내부 파일 목록
                file_list = zip_ref.namelist()
                print(f'ZIP 내부 파일: {file_list}')
                
                # 첫 번째 파일 추출
                xml_filename = file_list[0]
                xml_content = zip_ref.read(xml_filename).decode('utf-8')
                
                # 압축 해제된 파일 저장
                extracted_path = xml_path.parent / f'extracted_{xml_path.stem}.xml'
                with open(extracted_path, 'w', encoding='utf-8') as f:
                    f.write(xml_content)
                
                print(f'압축 해제 완료: {extracted_path}')
                xml_path = extracted_path
        
        # XML 파싱
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        print(f'XML 파일 분석: {xml_path}')
        print('=' * 80)
        print(f'\nRoot tag: {root.tag}')
        print(f'Root attributes: {root.attrib}')
        
        # 첫 100줄 출력
        with open(xml_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            print(f'\n\n첫 100줄 출력 (총 {len(lines)}줄):')
            print('=' * 80)
            for i, line in enumerate(lines[:100], 1):
                print(f'{i:3d}: {line.rstrip()}')
        
    except Exception as e:
        print(f'오류 발생: {e}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    analyze_cb_xml()
