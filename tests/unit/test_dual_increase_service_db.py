"""DualIncreaseService의 DB SSOT 배선 테스트

DualIncreaseService는 자체 DB를 갖지 않고 CapitalIncreaseSqliteRepository/
BonusSharesSqliteRepository를 그대로 재사용합니다(유무상증자 공시를 파싱해서 유상/무상 두
결정으로 쪼갠 뒤, 이미 그 결정 타입을 저장하는 리포지토리에 얹는 구조 - 별도 스토리지를 둘
이유가 없음). 이 설계의 핵심 이점(오케스트레이션 순서 무관하게 병합됨)까지 검증합니다.
"""
from datetime import date
from pathlib import Path

import pytest

from src.application.dual_increase_service import DualIncreaseService
from src.application.capital_increase_services import CapitalIncreaseService
from src.application.bonus_services import BonusSharesService
from src.domain import CapitalIncreaseDecision, BonusSharesDecision
from src.domain.value_objects import StockInfo, FundingPurpose
from src.infrastructure.dart_api import DownloadedXml


def _make_capital_decision(rcept_no: str, parent_rcp_no=None) -> CapitalIncreaseDecision:
    return CapitalIncreaseDecision(
        source_filename=f"x_{rcept_no}.xml", company_name="테스트회사",
        new_shares=StockInfo(common=100, preferred=0), par_value=500,
        total_shares_before=1000, issue_price=1000, funding=FundingPurpose(),
        method="일반공모", assign_per_share=0.1,
        board_resolution_date=date(2024, 1, 1), disclosure_date=date(2024, 1, 2),
        record_date=None, subscription_date=None, payment_date=None,
        rcept_no=rcept_no, parent_rcp_no=parent_rcp_no,
    )


@pytest.fixture
def services(tmp_path):
    """DualIncreaseService와, 같은 DB를 바라보는 독립적인 CapitalIncreaseService/BonusSharesService.

    프로덕션에서는 항상 data/유상증자, data/무상증자를 가리키지만, 테스트에서는 격리를 위해
    capital_data_directory/bonus_data_directory로 재정의한다.
    """
    capital_dir = str(tmp_path / "capital")
    bonus_dir = str(tmp_path / "bonus")
    dual_dir = str(tmp_path / "dual")

    dual = DualIncreaseService(
        data_directory=dual_dir,
        capital_data_directory=capital_dir,
        bonus_data_directory=bonus_dir,
        api_key="dummy-key",
        enable_google_drive=False,
    )
    # dual과 별개로 생성한 "진짜" CI/Bonus 서비스 - 같은 DB 파일을 바라봐야 함
    standalone_capital = CapitalIncreaseService(
        data_directory=capital_dir, api_key="dummy-key", enable_google_drive=False,
    )
    standalone_bonus = BonusSharesService(
        data_directory=bonus_dir, api_key="dummy-key", enable_google_drive=False,
    )
    return dual, standalone_capital, standalone_bonus


@pytest.fixture
def dual_with_real_xml_samples(tmp_path):
    """실제 유무상증자 XML 바이트로 파서 연동까지 실제로 태운다."""
    src_dir = Path("tests/fixtures/xml/유무상증자")
    sample_files = list(src_dir.glob("*.xml"))[:2]
    if not sample_files:
        pytest.skip("유무상증자 XML 샘플이 없습니다")

    dual = DualIncreaseService(
        data_directory=str(tmp_path / "dual"),
        capital_data_directory=str(tmp_path / "capital"),
        bonus_data_directory=str(tmp_path / "bonus"),
        api_key="dummy-key",
        enable_google_drive=False,
    )
    documents = [DownloadedXml(f.stem.rsplit("_", 1)[-1], f.name, f.read_bytes()) for f in sample_files]
    return dual, documents


class TestNoDedicatedStorage:
    """Dual이 CI/Bonus의 리포지토리를 그대로 재사용하는지(자체 DB가 없는지) 확인."""

    def test_capital_decisions_land_in_capital_repository(self, services):
        dual, standalone_capital, _ = services

        dual.capital_service.repository.upsert([_make_capital_decision("20240101000001")])
        assert dual.capital_service.database_session.persist()

        refreshed_capital = CapitalIncreaseService(
            data_directory=str(standalone_capital.data_directory), api_key="dummy-key", enable_google_drive=False,
        )

        # 새 세션이 source storage의 최신 DB 작업 사본을 읽는다.
        got = refreshed_capital.repository.get_all()
        assert len(got) == 1
        assert got[0].rcept_no == "20240101000001"


class TestOrderIndependence:
    """오케스트레이션 순서와 무관하게 병합되어야 한다는 설계 목표를 직접 검증."""

    def test_capital_service_running_before_or_after_dual_gives_same_result(self, services):
        dual, standalone_capital, _ = services

        # CI가 자기 몫을 먼저 저장
        standalone_capital.repository.upsert([_make_capital_decision("20240101000001")])
        assert standalone_capital.database_session.persist()
        dual = DualIncreaseService(
            data_directory=str(dual.data_directory),
            capital_data_directory=str(standalone_capital.data_directory),
            bonus_data_directory=str(dual.bonus_service.data_directory),
            api_key="dummy-key", enable_google_drive=False,
        )
        # Dual이 나중에 자기 몫(유무상증자에서 파생된 유상분)을 저장
        dual.capital_service.repository.upsert([_make_capital_decision("20240102000002")])
        assert dual.capital_service.database_session.persist()

        refreshed_capital = CapitalIncreaseService(
            data_directory=str(standalone_capital.data_directory), api_key="dummy-key", enable_google_drive=False,
        )
        all_rows = {d.rcept_no for d in refreshed_capital.repository.get_all()}
        assert all_rows == {"20240101000001", "20240102000002"}


class TestGetRelationMap:
    def test_merges_capital_and_bonus_relation_maps(self, services):
        dual, standalone_capital, standalone_bonus = services

        standalone_capital.repository.upsert([
            _make_capital_decision("20240101000001"),
            _make_capital_decision("20240102000002", parent_rcp_no="20240101000001"),
        ])
        assert standalone_capital.database_session.persist()
        dual = DualIncreaseService(
            data_directory=str(dual.data_directory),
            capital_data_directory=str(standalone_capital.data_directory),
            bonus_data_directory=str(standalone_bonus.data_directory),
            api_key="dummy-key", enable_google_drive=False,
        )

        relation_map = dual.get_relation_map()

        assert relation_map == {"20240102000002": "20240101000001"}


class TestParseAndExportToExcelWiredEndToEnd:
    def test_parses_real_samples_into_capital_and_bonus_repositories(self, dual_with_real_xml_samples):
        dual, documents = dual_with_real_xml_samples

        count = dual.parse_and_export_to_excel(documents)

        assert count >= 1
        # 유상/무상 어느 한쪽이든 결과가 저장 + 엑셀이 각자 서비스의 파일로 생성돼야 함
        total_db_rows = len(dual.capital_service.repository.get_all()) + len(dual.bonus_service.repository.get_all())
        assert total_db_rows == count

    def test_second_run_without_new_xml_is_idempotent(self, dual_with_real_xml_samples):
        dual, documents = dual_with_real_xml_samples

        first_count = dual.parse_and_export_to_excel(documents)
        second_count = dual.parse_and_export_to_excel(documents)

        assert first_count == second_count
