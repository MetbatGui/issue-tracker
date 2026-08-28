"""무상증자 파싱 테스트

무상증자 관련 보고서 필터링 및 XML 파싱 테스트입니다.
"""
import pytest
from pathlib import Path
from src.infrastructure import DartApiClient, BonusSharesXmlParser


class TestBonusSharesFiltering:
    """무상증자 필터링 로직 테스트"""
    
    def test_filter_bonus_shares_reports(self):
        """무상증자 보고서 필터링 테스트"""
        # Given: 다양한 보고서 타입
        mock_data = [
            {"report_nm": "무상증자결정", "corp_name": "테스트1"},
            {"report_nm": "무상증자결정(자율공시)(종속회사의주요경영사항)", "corp_name": "테스트2"},
            {"report_nm": "주요사항보고서(무상증자결정)", "corp_name": "테스트3"},
            {"report_nm": "주요사항보고서(무상증자결정)(기재정정)", "corp_name": "테스트4"},
            {"report_nm": "주요사항보고서(유무상증자결정)", "corp_name": "테스트5"},
            {"report_nm": "유상증자결정", "corp_name": "제외1"},
            {"report_nm": "주요사항보고서(유상증자결정)", "corp_name": "제외2"},
        ]
        
        # When: 필터링 실행
        filtered = DartApiClient.filter_bonus_shares_reports(mock_data)
        
        # Then: 단독 무상증자 관련 공시만 필터링됨.
        # 유무상증자는 DualIncreaseService가 별도로 수집한다.
        assert len(filtered) == 4
        corp_names = [item["corp_name"] for item in filtered]
        assert "제외1" not in corp_names
        assert "제외2" not in corp_names
        assert "테스트1" in corp_names
        assert "테스트5" not in corp_names
    
    def test_filter_empty_list(self):
        """빈 리스트 필터링 테스트"""
        # Given: 빈 리스트
        mock_data = []
        
        # When: 필터링 실행
        filtered = DartApiClient.filter_bonus_shares_reports(mock_data)
        
        # Then: 빈 리스트 반환
        assert filtered == []
    
    def test_filter_no_match(self):
        """매칭되는 항목이 없을 때 테스트"""
        # Given: 무상증자 관련이 아닌 보고서들만
        mock_data = [
            {"report_nm": "주요사항보고서(유상증자결정)", "corp_name": "테스트1"},
            {"report_nm": "자기주식처분결정", "corp_name": "테스트2"},
        ]
        
        # When: 필터링 실행
        filtered = DartApiClient.filter_bonus_shares_reports(mock_data)
        
        # Then: 빈 리스트 반환
        assert filtered == []


class TestBonusSharesParsing:
    """무상증자 XML 파싱 테스트"""
    
    @pytest.fixture
    def data_dir(self):
        """저장소에 포함된 XML fixture 디렉토리 경로"""
        return Path("tests/fixtures/xml/무상증자")
    
    def test_xml_files_exist(self, data_dir):
        """XML 파일이 존재하는지 확인"""
        # Given: 데이터 디렉토리
        xml_dir = data_dir
        
        # When: XML 파일 검색
        xml_files = list(xml_dir.glob("*.xml"))
        
        # Then: 로컬 샘플 데이터가 있는 환경에서만 검증한다.
        if not xml_files:
            pytest.skip(f"XML 샘플 데이터가 없습니다: {xml_dir}")
        print(f"\n발견된 XML 파일: {len(xml_files)}개")
    
    def test_parse_single_xml(self, data_dir):
        """단일 XML 파일 파싱 테스트"""
        # Given: XML 파일 하나 선택
        xml_dir = data_dir
        xml_files = list(xml_dir.glob("*.xml"))
        
        if not xml_files:
            pytest.skip("XML 파일이 없습니다")
        
        first_xml = xml_files[0]
        
        # When: 파일 파싱
        decision = BonusSharesXmlParser.parse(str(first_xml))
        
        # Then: 파싱 성공
        assert decision is not None, f"파싱 실패: {first_xml.name}"
        print(f"\n파싱 성공: {first_xml.name}")
        print(f"  회사명: {decision.company_name}")
        print(f"  파일명: {decision.source_filename}")
    
    def test_parse_all_xml_files(self, data_dir):
        """모든 XML 파일 파싱 및 통계"""
        # Given: 모든 XML 파일
        xml_dir = data_dir
        xml_files = list(xml_dir.glob("*.xml"))
        
        if not xml_files:
            pytest.skip("XML 파일이 없습니다")
        
        # When: 모든 파일 파싱
        parsed_count = 0
        failed_count = 0
        decisions = []
        
        for xml_file in xml_files:
            try:
                decision = BonusSharesXmlParser.parse(str(xml_file))
                if decision:
                    parsed_count += 1
                    decisions.append(decision)
                else:
                    failed_count += 1
            except Exception as e:
                failed_count += 1
                print(f"\n[FAIL] 파싱 실패: {xml_file.name} - {e}")
        
        # Then: 통계 출력
        print(f"\n[파싱 통계]:")
        print(f"  - 총 파일 수: {len(xml_files)}개")
        print(f"  - 파싱 성공: {parsed_count}개")
        print(f"  - 파싱 실패: {failed_count}개")
        print(f"  - 유효한 데이터: {len(decisions)}개")
        
        assert parsed_count > 0, "파싱된 파일이 없습니다"
    
    def test_parsed_data_validation(self, data_dir):
        """파싱된 데이터의 필드 검증"""
        # Given: 모든 XML 파일 파싱
        xml_dir = data_dir
        xml_files = list(xml_dir.glob("*.xml"))
        
        if not xml_files:
            pytest.skip("XML 파일이 없습니다")
        
        decisions = []
        for xml_file in xml_files:
            try:
                decision = BonusSharesXmlParser.parse(str(xml_file))
                if decision:
                    decisions.append(decision)
            except Exception:
                continue
        
        assert len(decisions) > 0, "유효한 파싱 데이터가 없습니다"
        
        # When & Then: 각 결정의 필드 검증
        print(f"\n검증할 데이터: {len(decisions)}건")
        
        for i, decision in enumerate(decisions[:5], 1):  # 처음 5개만 상세 출력
            # 필수 필드 존재 확인
            assert decision.company_name, f"회사명이 없습니다: {decision.source_filename}"
            assert decision.source_filename, "소스 파일명이 없습니다"
            assert decision.new_shares is not None, f"신주 정보가 없습니다: {decision.company_name}"
            
            # 타입 검증
            assert isinstance(decision.company_name, str)
            assert isinstance(decision.par_value, int)
            assert isinstance(decision.total_shares_before, int)
            
            print(f"\n[OK] [{i}] {decision.company_name}")
            print(f"   - 액면가: {decision.par_value:,}원")
            print(f"   - 기존 발행주식: {decision.total_shares_before:,}주")
            print(f"   - 보통주: {decision.new_shares.common:,}주")
            if decision.new_shares.preferred > 0:
                print(f"   - 우선주: {decision.new_shares.preferred:,}주")
            if decision.assign_per_share > 0:
                print(f"   - 배정 비율: 1:{decision.assign_per_share}")
        
        if len(decisions) > 5:
            print(f"\n... 외 {len(decisions) - 5}건 더 있음")
