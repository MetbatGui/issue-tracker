"""무상증자 Excel -> SQLite 마이그레이션 스크립트 테스트

실제 BonusSharesExcelWriter로 생성한 Excel을 입력으로 사용해, 마이그레이션 후
row count parity(고유 접수번호 수 == DB row 수)가 지켜지는지 회귀 테스트로 고정합니다.
"""
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))

from src.domain import BonusSharesDecision
from src.domain.value_objects import StockInfo
from src.infrastructure.bonus_excel_writer import BonusSharesExcelWriter
from migrate_bonus_shares_to_sqlite import migrate


def _make_decision(rcept_no: str, year: int, company_name: str = "테스트회사") -> BonusSharesDecision:
    return BonusSharesDecision(
        source_filename=f"{company_name}_{rcept_no}.xml",
        company_name=company_name,
        new_shares=StockInfo(common=500, preferred=0),
        par_value=500,
        total_shares_before=10000,
        assign_per_share=0.5,
        board_resolution_date=date(year, 1, 1),
        disclosure_date=date(year, 1, 2),
        record_date=date(year, 1, 10),
        listing_date=date(year, 1, 25),
        report_name="주요사항보고서(무상증자결정)",
        is_correction=False,
        rcept_no=rcept_no,
        parent_rcp_no=None,
        original_disclosure_date=None,
    )


@pytest.fixture
def sample_excel(tmp_path):
    excel_path = tmp_path / "무상증자.xlsx"
    writer = BonusSharesExcelWriter(output_path=str(excel_path))
    decisions = [
        _make_decision("20230101000001", 2023, "회사A"),
        _make_decision("20240101000002", 2024, "회사B"),
        _make_decision("20240102000003", 2024, "회사C"),
    ]
    writer.write(decisions)
    return excel_path


class TestMigration:
    def test_row_count_parity(self, sample_excel, tmp_path):
        db_path = str(tmp_path / "무상증자.db")

        result = migrate(str(sample_excel), db_path)

        assert result["excel_rows"] == 3
        assert result["db_rows"] == 3
        assert result["match"] is True

    def test_migrated_data_is_queryable_via_repository(self, sample_excel, tmp_path):
        from src.infrastructure.bonus_shares_sqlite_repository import BonusSharesSqliteRepository

        db_path = str(tmp_path / "무상증자.db")
        migrate(str(sample_excel), db_path)

        repo = BonusSharesSqliteRepository(db_path)
        decisions = {d.rcept_no: d for d in repo.get_all()}

        assert len(decisions) == 3
        assert decisions["20240101000002"].company_name == "회사B"
        assert decisions["20240101000002"].disclosure_date == date(2024, 1, 2)
        assert decisions["20240101000002"].listing_date == date(2024, 1, 25)
