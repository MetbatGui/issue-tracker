"""BondWithWarrantService의 DB SSOT 배선(parse_and_export_to_excel/export_to_excel/get_relation_map)
자체를 검증하는 테스트. (다른 3개 서비스 배선 테스트와 동일한 이유로 작성)

이 서비스는 원래 data_directory를 생성자 인자로 받지 않았음 - DB SSOT 배선을 추가하면서
다른 4개 서비스와 동일하게 파라미터화(테스트 격리를 위해서도 필요).
"""
from datetime import date
from pathlib import Path

import pytest

from src.application.bond_with_warrant_service import BondWithWarrantService
from src.domain import BondWithWarrantDecision
from src.domain.value_objects import FundingPurpose
from src.infrastructure.dart_api import DownloadedXml


def _make_decision(rcept_no: str, parent_rcp_no=None, company_name: str = "테스트회사") -> BondWithWarrantDecision:
    return BondWithWarrantDecision(
        source_filename=f"{company_name}_{rcept_no}.xml",
        company_name=company_name,
        sequence_number="1",
        bond_type="기명식 무보증 비분리형 사모 신주인수권부사채",
        face_value_total=1_000_000_000,
        funding=FundingPurpose(operating=1_000_000_000),
        interest_rate=None,
        maturity_date=date(2027, 1, 1),
        issue_method="사모",
        exercise_ratio=100.0,
        exercise_price=1000,
        exercise_shares=1_000_000,
        shares_ratio=5.0,
        exercise_start_date=date(2025, 1, 1),
        exercise_end_date=date(2027, 1, 1),
        subscription_date=date(2024, 1, 5),
        payment_date=date(2024, 1, 10),
        board_resolution_date=date(2024, 1, 1),
        rcept_no=rcept_no,
        parent_rcp_no=parent_rcp_no,
        disclosure_date=date(2024, 1, 2),
    )


@pytest.fixture
def service(tmp_path):
    return BondWithWarrantService(
        dart_api_key="dummy-key",
        data_directory=str(tmp_path / "data"),
        enable_google_drive=False,
    )


@pytest.fixture
def service_with_real_xml_samples(tmp_path):
    """실제 BW XML 바이트로 파서 연동까지 실제로 태운다."""
    src_dir = Path("data/신주인수권부사채/xml")
    sample_files = list(src_dir.glob("*.xml"))[:2]
    if not sample_files:
        pytest.skip("신주인수권부사채 XML 샘플이 없습니다")

    service = BondWithWarrantService(
        dart_api_key="dummy-key",
        data_directory=str(tmp_path / "data"),
        enable_google_drive=False,
    )
    documents = [DownloadedXml(f.stem.rsplit("_", 1)[-1], f.name, f.read_bytes()) for f in sample_files]
    return service, documents


class TestGetRelationMap:
    def test_returns_only_entries_with_parent(self, service):
        service.repository.upsert([
            _make_decision("20240101000001", parent_rcp_no=None),
            _make_decision("20240101000002", parent_rcp_no="20240101000001"),
        ])

        relation_map = service.get_relation_map()

        assert relation_map == {"20240101000002": "20240101000001"}


class TestExportToExcel:
    def test_rebuilds_excel_from_db_without_reparsing(self, service):
        service.repository.upsert([
            _make_decision("20240101000001"),
            _make_decision("20240102000002"),
        ])

        count = service.export_to_excel()

        assert count == 2
        assert service.excel_path.exists()

    def test_no_data_does_not_create_excel(self, service):
        count = service.export_to_excel()
        assert count == 0
        assert not service.excel_path.exists()


class TestParseAndExportToExcelWiredEndToEnd:
    def test_parses_real_samples_into_db_and_excel(self, service_with_real_xml_samples):
        service, documents = service_with_real_xml_samples

        count = service.parse_and_export_to_excel(documents)

        assert count >= 1
        db_rows = service.repository.get_all()
        assert len(db_rows) == count
        assert service.excel_path.exists()

    def test_second_run_without_new_xml_is_idempotent(self, service_with_real_xml_samples):
        service, documents = service_with_real_xml_samples

        first_count = service.parse_and_export_to_excel(documents)
        second_count = service.parse_and_export_to_excel(documents)

        assert first_count == second_count
        assert len(service.repository.get_all()) == first_count
