"""BonusSharesService의 DB SSOT 배선(parse_and_export_to_excel/export_to_excel/get_relation_map)
자체를 검증하는 테스트. (CapitalIncreaseService 쪽 배선 테스트와 동일한 이유로 작성)
"""
import shutil
from datetime import date
from pathlib import Path

import pytest

from src.application.bonus_services import BonusSharesService
from src.domain import BonusSharesDecision
from src.domain.value_objects import StockInfo


def _make_decision(rcept_no: str, parent_rcp_no=None, company_name: str = "테스트회사") -> BonusSharesDecision:
    return BonusSharesDecision(
        source_filename=f"{company_name}_{rcept_no}.xml",
        company_name=company_name,
        new_shares=StockInfo(common=500, preferred=0),
        par_value=500,
        total_shares_before=10000,
        assign_per_share=0.5,
        board_resolution_date=date(2024, 1, 1),
        disclosure_date=date(2024, 1, 2),
        record_date=None,
        listing_date=None,
        rcept_no=rcept_no,
        parent_rcp_no=parent_rcp_no,
    )


@pytest.fixture
def service(tmp_path):
    return BonusSharesService(
        data_directory=str(tmp_path / "data"),
        api_key="dummy-key",
        enable_google_drive=False,
    )


@pytest.fixture
def service_with_real_xml_samples(tmp_path):
    """실제 무상증자 XML 샘플 2개를 임시 데이터 디렉토리에 복사해 파서 연동까지 실제로 태운다."""
    src_dir = Path("data/무상증자/xml")
    sample_files = list(src_dir.glob("*.xml"))[:2]
    if not sample_files:
        pytest.skip("무상증자 XML 샘플이 없습니다")

    data_dir = tmp_path / "data"
    xml_dir = data_dir / "xml"
    xml_dir.mkdir(parents=True)
    for f in sample_files:
        shutil.copy(f, xml_dir / f.name)

    return BonusSharesService(
        data_directory=str(data_dir),
        api_key="dummy-key",
        enable_google_drive=False,
    )


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
        service = service_with_real_xml_samples

        count = service.parse_and_export_to_excel()

        assert count >= 1
        db_rows = service.repository.get_all()
        assert len(db_rows) == count
        assert service.excel_path.exists()

    def test_second_run_without_new_xml_is_idempotent(self, service_with_real_xml_samples):
        service = service_with_real_xml_samples

        first_count = service.parse_and_export_to_excel()
        second_count = service.parse_and_export_to_excel()

        assert first_count == second_count
        assert len(service.repository.get_all()) == first_count
