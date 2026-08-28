"""CapitalIncreaseService의 DB SSOT 배선(parse_and_export_to_excel/export_to_excel/get_relation_map)
자체를 검증하는 테스트.

리포지토리와 마이그레이션 스크립트는 각각 test_capital_increase_sqlite_repository.py,
test_capital_increase_migration.py에서 단위 테스트했지만, 이 둘을 실제로 연결하는
서비스 계층 메서드는 그동안 수동 검증(실데이터 1회 실행)만 거쳤을 뿐 회귀 테스트가 없었음.
"""
from datetime import date
from pathlib import Path

import pytest

from src.application.capital_increase_services import CapitalIncreaseService
from src.domain import CapitalIncreaseDecision
from src.domain.value_objects import StockInfo, FundingPurpose
from src.infrastructure.dart_api import DownloadedXml


def _make_decision(rcept_no: str, parent_rcp_no=None, company_name: str = "테스트회사") -> CapitalIncreaseDecision:
    return CapitalIncreaseDecision(
        source_filename=f"{company_name}_{rcept_no}.xml",
        company_name=company_name,
        new_shares=StockInfo(common=100, preferred=0),
        par_value=500,
        total_shares_before=1000,
        issue_price=1000,
        funding=FundingPurpose(),
        method="일반공모",
        assign_per_share=0.1,
        board_resolution_date=date(2024, 1, 1),
        disclosure_date=date(2024, 1, 2),
        record_date=None,
        subscription_date=None,
        payment_date=None,
        rcept_no=rcept_no,
        parent_rcp_no=parent_rcp_no,
    )


@pytest.fixture
def service(tmp_path):
    return CapitalIncreaseService(
        data_directory=str(tmp_path / "data"),
        api_key="dummy-key",
        enable_google_drive=False,
    )


@pytest.fixture
def service_with_real_xml_samples(tmp_path):
    """실제 유상증자 XML 바이트로 파서 연동까지 실제로 태운다."""
    src_dir = Path("tests/fixtures/xml/유상증자")
    sample_files = list(src_dir.glob("*.xml"))[:2]
    if not sample_files:
        pytest.skip("유상증자 XML 샘플이 없습니다")

    service = CapitalIncreaseService(
        data_directory=str(tmp_path / "data"),
        api_key="dummy-key",
        enable_google_drive=False,
    )
    documents = [
        DownloadedXml(f.stem.rsplit("_", 1)[-1], f.name, f.read_bytes())
        for f in sample_files
    ]
    return service, documents


class TestGetRelationMap:
    def test_returns_only_entries_with_parent(self, service):
        service.repository.upsert([
            _make_decision("20240101000001", parent_rcp_no=None),
            _make_decision("20240101000002", parent_rcp_no="20240101000001"),
        ])

        relation_map = service.get_relation_map()

        assert relation_map == {"20240101000002": "20240101000001"}

    def test_empty_when_no_data(self, service):
        assert service.get_relation_map() == {}


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

    def test_is_correction_round_trips_through_db(self, service):
        decision = _make_decision("20240101000001")
        from dataclasses import replace
        decision = replace(decision, is_correction=True, report_name="주요사항보고서(유상증자결정)(기재정정)")

        service.repository.upsert([decision])
        got = service.repository.get_all()[0]

        assert got.is_correction is True
        assert got.report_name == "주요사항보고서(유상증자결정)(기재정정)"


class TestParseAndExportToExcelWiredEndToEnd:
    """실제 XML 파서 -> repository.upsert -> export_to_excel 전체 배선을 실제 샘플 파일로 검증."""

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
