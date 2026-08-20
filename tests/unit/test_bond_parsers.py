"""전환사채(CB)/신주인수권부사채(BW) 파서 특성화(characterization) 테스트

리팩토링(ACODE 매핑 테이블화) 전후 동작이 동일함을 보장하기 위한 회귀 안전망입니다.
알려진 실제 DART 샘플 파일의 필드 값을 고정하여 검증합니다.
"""
from datetime import date
from pathlib import Path

import pytest

from src.infrastructure import ConvertibleBondXmlParser
from src.infrastructure.bond_with_warrant_xml_parser import BondWithWarrantXmlParser


CB_XML_DIR = Path("data/전환사채/xml")
BW_XML_DIR = Path("data/신주인수권부사채/xml")

CB_SAMPLE = CB_XML_DIR / "3S_20241209000388.xml"
BW_SAMPLE = BW_XML_DIR / "BGF에코머티리얼즈_20211104000334.xml"


class TestConvertibleBondXmlParser:
    """전환사채 파서 특성화 테스트"""

    @pytest.fixture
    def decision(self):
        if not CB_SAMPLE.exists():
            pytest.skip(f"샘플 파일 없음: {CB_SAMPLE}")
        return ConvertibleBondXmlParser.parse(str(CB_SAMPLE))

    def test_known_field_values(self, decision):
        """알려진 샘플 파일(3S, 2024-12-09)의 필드 값 고정"""
        assert decision is not None
        assert decision.sequence_number == "13"
        assert decision.bond_type == "무기명식 이권부 무보증 사모 전환사채"
        assert decision.face_value_total == 5_000_000_000
        assert decision.conversion_ratio == 100.0
        assert decision.conversion_price == 1_945
        assert decision.conversion_shares == 2_570_694
        assert decision.shares_ratio == 4.84
        assert decision.maturity_date == date(2029, 12, 17)
        assert decision.issue_method == "사모"
        assert decision.conversion_start_date == date(2025, 12, 17)
        assert decision.conversion_end_date == date(2029, 11, 17)
        assert decision.subscription_date == date(2024, 12, 11)
        assert decision.payment_date == date(2024, 12, 17)
        assert decision.board_resolution_date == date(2024, 12, 9)

    def test_funding_purpose(self, decision):
        """자금조달목적 필드: 운영자금만 채워진 케이스"""
        assert decision.funding.facility == 0
        assert decision.funding.operating == 5_000_000_000
        assert decision.funding.business_acquisition == 0
        assert decision.funding.acquisition == 0
        assert decision.funding.debt_repayment == 0
        assert decision.funding.other == 0

    def test_parse_all_samples(self):
        """전체 샘플 파일이 예외 없이 파싱되고, 핵심 필드 결측률이 낮음을 확인"""
        xml_files = list(CB_XML_DIR.glob("*.xml"))
        if not xml_files:
            pytest.skip("CB 샘플 XML이 없습니다")

        decisions = [d for d in (ConvertibleBondXmlParser.parse(str(f)) for f in xml_files) if d]
        assert len(decisions) == len(xml_files), "일부 파일이 파싱 실패함"

        none_ratio = sum(1 for d in decisions if d.conversion_ratio is None)
        none_price = sum(1 for d in decisions if d.conversion_price is None)
        # 대다수 파일에서 전환비율/전환가액이 채워져 있어야 함 (ACODE 매핑 정확성 검증)
        assert none_ratio / len(decisions) < 0.05
        assert none_price / len(decisions) < 0.05


class TestBondWithWarrantXmlParser:
    """신주인수권부사채 파서 특성화 테스트"""

    @pytest.fixture
    def decision(self):
        if not BW_SAMPLE.exists():
            pytest.skip(f"샘플 파일 없음: {BW_SAMPLE}")
        return BondWithWarrantXmlParser.parse(str(BW_SAMPLE))

    def test_known_field_values(self, decision):
        """알려진 샘플 파일(BGF에코머티리얼즈, 2021-11-04)의 필드 값 고정"""
        assert decision is not None
        assert decision.sequence_number == "4"
        assert decision.bond_type == "기명식 무보증 비분리형 사모 신주인수권부사채"
        assert decision.face_value_total == 43_500_000_000
        assert decision.exercise_ratio == 100.0
        assert decision.exercise_price == 8_713
        assert decision.exercise_shares == 4_992_540
        assert decision.shares_ratio == 19.12
        assert decision.maturity_date == date(2024, 12, 22)
        assert decision.issue_method == "사모"
        assert decision.exercise_start_date == date(2022, 12, 22)
        assert decision.exercise_end_date == date(2024, 12, 21)
        assert decision.subscription_date == date(2021, 11, 4)
        assert decision.payment_date == date(2021, 12, 22)
        assert decision.board_resolution_date == date(2021, 11, 4)

    def test_parse_all_samples(self):
        """전체 샘플 파일이 예외 없이 파싱되고, 핵심 필드 결측률이 낮음을 확인"""
        xml_files = list(BW_XML_DIR.glob("*.xml"))
        if not xml_files:
            pytest.skip("BW 샘플 XML이 없습니다")

        decisions = [d for d in (BondWithWarrantXmlParser.parse(str(f)) for f in xml_files) if d]
        assert len(decisions) == len(xml_files), "일부 파일이 파싱 실패함"

        none_ratio = sum(1 for d in decisions if d.exercise_ratio is None)
        none_price = sum(1 for d in decisions if d.exercise_price is None)
        assert none_ratio / len(decisions) < 0.05
        assert none_price / len(decisions) < 0.05
