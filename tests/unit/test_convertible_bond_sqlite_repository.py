"""ConvertibleBondSqliteRepository 테스트

DB SSOT 전환(전환사채, 세 번째 사례) 리포지토리 계층을 :memory: SQLite로 검증합니다.
구현 전에 먼저 작성하여 RED 확인 후 구현합니다.
"""
from datetime import date

import pytest

from src.domain import ConvertibleBondDecision
from src.domain.value_objects import FundingPurpose
from src.infrastructure.convertible_bond_sqlite_repository import ConvertibleBondSqliteRepository


def _make_decision(
    rcept_no: str,
    company_name: str = "테스트회사",
    parent_rcp_no=None,
    year: int = 2024,
) -> ConvertibleBondDecision:
    return ConvertibleBondDecision(
        source_filename=f"{company_name}_{rcept_no}.xml",
        company_name=company_name,
        sequence_number="13",
        bond_type="무기명식 이권부 무보증 사모 전환사채",
        face_value_total=5_000_000_000,
        funding=FundingPurpose(facility=0, operating=5_000_000_000, acquisition=0, other=0),
        interest_rate=None,
        maturity_date=date(year + 5, 12, 17),
        issue_method="사모",
        conversion_ratio=100.0,
        conversion_price=1945,
        conversion_shares=2_570_694,
        shares_ratio=4.84,
        conversion_start_date=date(year + 1, 12, 17),
        conversion_end_date=date(year + 5, 11, 17),
        subscription_date=date(year, 12, 11),
        payment_date=date(year, 12, 17),
        board_resolution_date=date(year, 12, 9),
        report_name="주요사항보고서(전환사채권발행결정)",
        is_correction=False,
        rcept_no=rcept_no,
        parent_rcp_no=parent_rcp_no,
        disclosure_date=date(year, 12, 9),
        original_disclosure_date=None,
    )


@pytest.fixture
def repo():
    return ConvertibleBondSqliteRepository(":memory:")


class TestUpsertAndGetAll:
    def test_roundtrip_preserves_core_fields(self, repo):
        decision = _make_decision("20241209000388")
        repo.upsert([decision])

        got = repo.get_all()[0]

        assert got.rcept_no == "20241209000388"
        assert got.company_name == "테스트회사"
        assert got.sequence_number == "13"
        assert got.bond_type == "무기명식 이권부 무보증 사모 전환사채"
        assert got.face_value_total == 5_000_000_000
        assert got.issue_method == "사모"
        assert got.conversion_ratio == 100.0
        assert got.conversion_price == 1945
        assert got.conversion_shares == 2_570_694
        assert got.shares_ratio == 4.84
        assert got.maturity_date == date(2029, 12, 17)
        assert got.conversion_start_date == date(2025, 12, 17)
        assert got.conversion_end_date == date(2029, 11, 17)
        assert got.subscription_date == date(2024, 12, 11)
        assert got.payment_date == date(2024, 12, 17)
        assert got.board_resolution_date == date(2024, 12, 9)
        assert got.disclosure_date == date(2024, 12, 9)
        assert got.report_name == "주요사항보고서(전환사채권발행결정)"
        assert got.is_correction is False

    def test_roundtrip_preserves_funding_purpose(self, repo):
        repo.upsert([_make_decision("20241209000388")])
        got = repo.get_all()[0]
        assert got.funding.facility == 0
        assert got.funding.operating == 5_000_000_000
        assert got.funding.acquisition == 0
        assert got.funding.debt_repayment == 0
        assert got.funding.business_acquisition == 0
        assert got.funding.other == 0

    def test_roundtrip_preserves_parent_rcp_no(self, repo):
        repo.upsert([_make_decision("20241209000001")])
        repo.upsert([_make_decision("20241217000002", parent_rcp_no="20241209000001")])

        got = {d.rcept_no: d for d in repo.get_all()}
        assert got["20241217000002"].parent_rcp_no == "20241209000001"
        assert got["20241209000001"].parent_rcp_no is None

    def test_upsert_returns_count(self, repo):
        count = repo.upsert([_make_decision("20241209000001"), _make_decision("20241209000002")])
        assert count == 2


class TestDedupeByRceptNo:
    def test_reupsert_same_rcept_no_updates_in_place(self, repo):
        repo.upsert([_make_decision("20241209000001", company_name="구버전")])
        repo.upsert([_make_decision("20241209000001", company_name="신버전")])

        result = repo.get_all()

        assert len(result) == 1
        assert result[0].company_name == "신버전"

    def test_mixed_new_and_existing_rcept_no(self, repo):
        repo.upsert([_make_decision("20241209000001")])
        repo.upsert([
            _make_decision("20241209000001", company_name="업데이트됨"),
            _make_decision("20241217000002", company_name="신규"),
        ])

        result = {d.rcept_no: d for d in repo.get_all()}
        assert len(result) == 2
        assert result["20241209000001"].company_name == "업데이트됨"
        assert result["20241217000002"].company_name == "신규"
