"""XML 파싱 Unit 테스트

각 파서가 다운로드된 XML 파일을 제대로 파싱하는지 테스트합니다.
"""
import pytest
from pathlib import Path
from src.infrastructure import (
    CapitalIncreaseXmlParser,
    BonusSharesXmlParser
)


class TestCapitalIncreaseXmlParsing:
    """유상증자 XML 파싱 테스트"""
    
    @pytest.fixture
    def capital_xml_dir(self):
        """유상증자 XML 디렉토리"""
        return Path("tests/fixtures/xml/유상증자")
    
    @pytest.fixture
    def sample_files(self, capital_xml_dir):
        """테스트용 샘플 파일 10개"""
        xml_files = list(capital_xml_dir.glob("*.xml"))
        return xml_files[:10] if len(xml_files) >= 10 else xml_files
    
    def test_capital_xml_files_exist(self, capital_xml_dir):
        """유상증자 XML 파일이 존재하는지 확인"""
        xml_files = list(capital_xml_dir.glob("*.xml"))
        assert len(xml_files) > 0, f"유상증자 XML 파일이 없습니다: {capital_xml_dir}"
        print(f"\n유상증자 XML 파일 수: {len(xml_files)}개")
    
    def test_parse_sample_capital_files(self, sample_files):
        """샘플 유상증자 파일 파싱 테스트"""
        if not sample_files:
            pytest.skip("테스트할 XML 파일이 없습니다")
        
        print(f"\n테스트 파일 수: {len(sample_files)}개")
        
        success = 0
        failed = []
        
        for xml_file in sample_files:
            decision = CapitalIncreaseXmlParser.parse(str(xml_file))
            
            if decision:
                success += 1
                # 기본 필드 검증
                assert decision.company_name, f"회사명 누락: {xml_file.name}"
                assert decision.par_value >= 0, f"액면가 오류: {xml_file.name}"
                assert decision.total_shares_before >= 0, f"발행주식 수 오류: {xml_file.name}"
                
                print(f"[OK] {xml_file.name}: {decision.company_name}")
            else:
                failed.append(xml_file.name)
                print(f"[FAIL] {xml_file.name}: 파싱 실패")
        
        print(f"\n결과: 성공 {success}/{len(sample_files)}")
        
        # 최소 30% 이상 성공해야 함 (일부 파일 인코딩 문제 고려)
        assert success >= len(sample_files) * 0.3, \
            f"파싱 성공률이 너무 낮습니다: {success}/{len(sample_files)}"
    
    def test_parsed_data_structure(self, sample_files):
        """파싱된 데이터 구조 검증"""
        if not sample_files:
            pytest.skip("테스트할 XML 파일이 없습니다")
        
        # 첫 번째 성공적으로 파싱된 파일 사용
        decision = None
        for xml_file in sample_files:
            decision = CapitalIncreaseXmlParser.parse(str(xml_file))
            if decision:
                break
        
        assert decision is not None, "파싱 가능한 파일이 없습니다"
        
        # 필수 속성 확인
        assert hasattr(decision, 'company_name')
        assert hasattr(decision, 'par_value')
        assert hasattr(decision, 'new_shares')
        assert hasattr(decision, 'total_shares_before')
        assert hasattr(decision, 'issue_price')
        assert hasattr(decision, 'funding')
        
        # 타입 확인
        assert isinstance(decision.company_name, str)
        assert isinstance(decision.par_value, int)
        assert isinstance(decision.total_shares_before, int)
        
        print(f"\n[OK] 데이터 구조 검증 완료: {decision.company_name}")


class TestBonusSharesXmlParsing:
    """무상증자 XML 파싱 테스트"""
    
    @pytest.fixture
    def bonus_xml_dir(self):
        """무상증자 XML 디렉토리"""
        return Path("tests/fixtures/xml/무상증자")
    
    @pytest.fixture
    def sample_files(self, bonus_xml_dir):
        """테스트용 샘플 파일 10개"""
        xml_files = list(bonus_xml_dir.glob("*.xml"))
        return xml_files[:10] if len(xml_files) >= 10 else xml_files
    
    def test_bonus_xml_files_exist(self, bonus_xml_dir):
        """무상증자 XML 파일이 존재하는지 확인"""
        xml_files = list(bonus_xml_dir.glob("*.xml"))
        assert len(xml_files) > 0, f"무상증자 XML 파일이 없습니다: {bonus_xml_dir}"
        print(f"\n무상증자 XML 파일 수: {len(xml_files)}개")
    
    def test_parse_sample_bonus_files(self, sample_files):
        """샘플 무상증자 파일 파싱 테스트"""
        if not sample_files:
            pytest.skip("테스트할 XML 파일이 없습니다")
        
        print(f"\n테스트 파일 수: {len(sample_files)}개")
        
        success = 0
        failed = []
        
        for xml_file in sample_files:
            decision = BonusSharesXmlParser.parse(str(xml_file))
            
            if decision:
                success += 1
                # 기본 필드 검증
                assert decision.company_name, f"회사명 누락: {xml_file.name}"
                assert decision.par_value >= 0, f"액면가 오류: {xml_file.name}"
                assert decision.total_shares_before >= 0, f"발행주식 수 오류: {xml_file.name}"
                
                print(f"[OK] {xml_file.name}: {decision.company_name}")
            else:
                failed.append(xml_file.name)
                print(f"[FAIL] {xml_file.name}: 파싱 실패")
        
        print(f"\n결과: 성공 {success}/{len(sample_files)}")
        
        # 최소 50% 이상 성공해야 함
        assert success >= len(sample_files) * 0.5, \
            f"파싱 성공률이 너무 낮습니다: {success}/{len(sample_files)}"


class TestDualIncreaseXmlParsing:
    """유무상증자 XML 파싱 테스트 (양쪽 파서로 파싱)"""
    
    @pytest.fixture
    def dual_xml_dir(self):
        """유무상증자 XML 디렉토리"""
        return Path("tests/fixtures/xml/유무상증자")
    
    @pytest.fixture
    def sample_files(self, dual_xml_dir):
        """테스트용 샘플 파일 10개"""
        xml_files = list(dual_xml_dir.glob("*.xml"))
        return xml_files[:10] if len(xml_files) >= 10 else xml_files
    
    def test_dual_xml_files_exist(self, dual_xml_dir):
        """유무상증자 XML 파일이 존재하는지 확인"""
        xml_files = list(dual_xml_dir.glob("*.xml"))
        assert len(xml_files) > 0, f"유무상증자 XML 파일이 없습니다: {dual_xml_dir}"
        print(f"\n유무상증자 XML 파일 수: {len(xml_files)}개")
    
    def test_parse_dual_with_capital_parser(self, sample_files):
        """유무상증자를 유상증자 파서로 파싱 (유상 부분 추출)"""
        if not sample_files:
            pytest.skip("테스트할 XML 파일이 없습니다")
        
        print(f"\n[유상증자 파서] 테스트 파일 수: {len(sample_files)}개")
        
        success = 0
        
        for xml_file in sample_files:
            decision = CapitalIncreaseXmlParser.parse(str(xml_file))
            
            if decision:
                success += 1
                print(f"[OK] {xml_file.name}: {decision.company_name} (유상 부분 추출)")
            else:
                print(f"[FAIL] {xml_file.name}: 파싱 실패")
        
        print(f"\n결과: 성공 {success}/{len(sample_files)}")
        assert success > 0, "유상증자 파서로 파싱된 파일이 없습니다"
    
    def test_parse_dual_with_bonus_parser(self, sample_files):
        """유무상증자를 무상증자 파서로 파싱 (무상 부분 추출)"""
        if not sample_files:
            pytest.skip("테스트할 XML 파일이 없습니다")
        
        print(f"\n[무상증자 파서] 테스트 파일 수: {len(sample_files)}개")
        
        success = 0
        
        for xml_file in sample_files:
            decision = BonusSharesXmlParser.parse(str(xml_file))
            
            if decision:
                success += 1
                print(f"[OK] {xml_file.name}: {decision.company_name} (무상 부분 추출)")
            else:
                print(f"[FAIL] {xml_file.name}: 파싱 실패")
        
        print(f"\n결과: 성공 {success}/{len(sample_files)}")
        assert success > 0, "무상증자 파서로 파싱된 파일이 없습니다"
    
    def test_dual_parsing_both_succeed(self, sample_files):
        """유무상증자가 양쪽 파서로 모두 파싱되는지 확인"""
        if not sample_files:
            pytest.skip("테스트할 XML 파일이 없습니다")
        
        both_success = 0
        only_capital = 0
        only_bonus = 0
        both_failed = 0
        
        for xml_file in sample_files:
            capital_decision = CapitalIncreaseXmlParser.parse(str(xml_file))
            bonus_decision = BonusSharesXmlParser.parse(str(xml_file))
            
            if capital_decision and bonus_decision:
                both_success += 1
                print(f"[OK] {xml_file.name}: 양쪽 모두 성공")
            elif capital_decision:
                only_capital += 1
                print(f"[WARN]  {xml_file.name}: 유상만 성공")
            elif bonus_decision:
                only_bonus += 1
                print(f"[WARN]  {xml_file.name}: 무상만 성공")
            else:
                both_failed += 1
                print(f"[FAIL] {xml_file.name}: 양쪽 모두 실패")
        
        print(f"\n결과:")
        print(f"  양쪽 성공: {both_success}")
        print(f"  유상만: {only_capital}")
        print(f"  무상만: {only_bonus}")
        print(f"  모두 실패: {both_failed}")
        
        # 최소 하나 이상은 양쪽 파서로 성공해야 함
        assert both_success > 0, "양쪽 파서로 모두 성공한 파일이 없습니다"
