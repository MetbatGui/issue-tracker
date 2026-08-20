"""신주인수권부사채 Excel -> SQLite 마이그레이션 스크립트 테스트

실제 BondWithWarrantExcelWriter로 생성한 Excel을 입력으로 사용해, 마이그레이션 후
row count parity(고유 접수번호 수 == DB row 수)가 지켜지는지 회귀 테스트로 고정합니다.
"""
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))

from src.domain import BondWithWarrantDecision
from src.domain.value_objects import FundingPurpose
from src.infrastructure.bond_with_warrant_excel_writer import BondWithWarrantExcelWriter
from migrate_bond_with_warrant_to_sqlite import migrate


def _make_decision(rcept_no: str, year: int, company_name: str = "테스트회사") -> BondWithWarrantDecision:
    return BondWithWarrantDecision(
        source_filename=f"{company_name}_{rcept_no}.xml",
        company_name=company_name,
        sequence_number="1",
        bond_type="기명식 무보증 비분리형 사모 신주인수권부사채",
        face_value_total=1_000_000_000,
        funding=FundingPurpose(facility=0, operating=1_000_000_000, acquisition=0,
                                debt_repayment=0, business_acquisition=0, other=0),
        interest_rate=None,
        maturity_date=date(year + 3, 1, 1),
        issue_method="사모",
        exercise_ratio=100.0,
        exercise_price=1000,
        exercise_shares=1_000_000,
        shares_ratio=5.0,
        exercise_start_date=date(year + 1, 1, 1),
        exercise_end_date=date(year + 3, 1, 1),
        subscription_date=date(year, 1, 5),
        payment_date=date(year, 1, 10),
        board_resolution_date=date(year, 1, 1),
        report_name="주요사항보고서(신주인수권부사채권발행결정)",
        is_correction=False,
        rcept_no=rcept_no,
        parent_rcp_no=None,
        disclosure_date=date(year, 1, 2),
        original_disclosure_date=None,
    )


@pytest.fixture
def sample_excel(tmp_path):
    excel_path = tmp_path / "신주인수권부사채.xlsx"
    writer = BondWithWarrantExcelWriter(output_path=str(excel_path))
    decisions = [
        _make_decision("20230101000001", 2023, "회사A"),
        _make_decision("20240101000002", 2024, "회사B"),
        _make_decision("20240102000003", 2024, "회사C"),
    ]
    writer.write(decisions)
    return excel_path


class TestMigration:
    def test_row_count_parity(self, sample_excel, tmp_path):
        db_path = str(tmp_path / "신주인수권부사채.db")

        result = migrate(str(sample_excel), db_path)

        assert result["excel_rows"] == 3
        assert result["db_rows"] == 3
        assert result["match"] is True

    def test_migrated_data_is_queryable_via_repository(self, sample_excel, tmp_path):
        from src.infrastructure.bond_with_warrant_sqlite_repository import BondWithWarrantSqliteRepository

        db_path = str(tmp_path / "신주인수권부사채.db")
        migrate(str(sample_excel), db_path)

        repo = BondWithWarrantSqliteRepository(db_path)
        decisions = {d.rcept_no: d for d in repo.get_all()}

        assert len(decisions) == 3
        assert decisions["20240101000002"].company_name == "회사B"
        assert decisions["20240101000002"].disclosure_date == date(2024, 1, 2)
        assert decisions["20240101000002"].funding.operating == 1_000_000_000
