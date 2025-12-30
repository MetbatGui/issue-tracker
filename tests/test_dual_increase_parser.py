"""유무상증자 파서 테스트"""
import pytest
from pathlib import Path
from src.infrastructure.dual_increase_xml_parser import DualIncreaseXmlParser


def test_dual_increase_parser():
    """유무상증자 파서가 유상증자와 무상증자 객체를 모두 반환하는지 테스트"""
    # 유무상증자 XML 디렉토리에서 첫 번째 파일 선택
    xml_dir = Path("data/유무상증자/xml")
    xml_files = sorted(xml_dir.glob("*.xml"))
    
    assert len(xml_files) > 0, "유무상증자 XML 파일이 없습니다"
    
    # 첫 번째 파일 파싱
    sample_file = xml_files[0]
    capital, bonus = DualIncreaseXmlParser.parse(str(sample_file))
    
    # 두 객체 모두 생성되어야 함
    assert capital is not None, f"{sample_file.name}: 유상증자 객체가 None입니다"
    assert bonus is not None, f"{sample_file.name}: 무상증자 객체가 None입니다"
    
    # 동일한 기본 정보 확인
    assert capital.company_name == bonus.company_name
    assert capital.disclosure_date == bonus.disclosure_date
    assert capital.source_filename == bonus.source_filename
    
    # 유상증자 특화 필드 확인
    assert hasattr(capital, 'issue_price')
    assert hasattr(capital, 'funding')
    assert hasattr(capital, 'method')
    assert hasattr(capital, 'payment_date')
    assert hasattr(capital, 'subscription_date')
    
    # 무상증자 특화 필드 확인
    assert hasattr(bonus, 'listing_date')
    
    print(f"✓ 테스트 성공: {sample_file.name}")
    print(f"  회사명: {capital.company_name}")
    print(f"  공시일: {capital.disclosure_date}")
    print(f"  유상증자 발행가액: {capital.issue_price:,}원")
    print(f"  무상증자 상장예정일: {bonus.listing_date}")


def test_multiple_dual_increase_files():
    """여러 유무상증자 파일들이 정상적으로 파싱되는지 테스트"""
    xml_dir = Path("data/유무상증자/xml")
    xml_files = sorted(xml_dir.glob("*.xml"))
    
    success_count = 0
    fail_count = 0
    
    for xml_file in xml_files[:5]:  # 처음 5개만 테스트
        capital, bonus = DualIncreaseXmlParser.parse(str(xml_file))
        
        if capital and bonus:
            success_count += 1
        else:
            fail_count += 1
            print(f"  ⚠️  파싱 실패: {xml_file.name}")
    
    print(f"\n파싱 결과: 성공 {success_count}건, 실패 {fail_count}건")
    assert success_count > 0, "하나 이상의 파일이 성공적으로 파싱되어야 합니다"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
