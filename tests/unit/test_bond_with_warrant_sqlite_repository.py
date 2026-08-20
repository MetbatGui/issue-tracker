"""BondWithWarrantSqliteRepository 테스트

DB SSOT 전환(신주인수권부사채, 네 번째 사례이자 마지막 - CB와 스키마가 거의 동일) 리포지토리
계층을 :memory: SQLite로 검증합니다. 구현 전에 먼저 작성하여 RED 확인 후 구현합니다.
"""
from datetime import date

import pytest

from src.domain import BondWithWarrantDecision
from src.domain.value_objects import FundingPurpose
from src.infrastructure.bond_with_warrant_sqlite_repository import BondWithWarrantSqliteRepository


def _make_decision(
    rcept_no: str,
    company_name: str = "테스트회사",
    parent_rcp_no=None,
    year: int = 2024,
) -> BondWithWarrantDecision:
    return BondWithWarrantDecision(
        source_filename=f"{company_name}_{rcept_no}.xml",
        company_name=company_name,
        sequence_number="4",
        bond_type="기명식 무보증 비분리형 사모 신주인수권부사채",
        face_value_total=43_500_000_000,
        funding=FundingPurpose(facility=0, operating=43_500_000_000, acquisition=0, other=0),
        interest_rate=None,
        maturity_date=date(year + 3, 12, 22),
        issue_method="사모",
        exercise_ratio=100.0,
        exercise_price=8713,
        exercise_shares=4_992_540,
        shares_ratio=19.12,
        exercise_start_date=date(year + 1, 12, 22),
        exercise_end_date=date(year + 3, 12, 21),
        subscription_date=date(year, 11, 4),
        payment_date=date(year, 12, 22),
        board_resolution_date=date(year, 11, 4),
        report_name="주요사항보고서(신주인수권부사채권발행결정)",
        is_correction=False,
        rcept_no=rcept_no,
        parent_rcp_no=parent_rcp_no,
        disclosure_date=date(year, 11, 4),
        original_disclosure_date=None,
    )


@pytest.fixture
def repo():
    return BondWithWarrantSqliteRepository(":memory:")


class TestUpsertAndGetAll:
    def test_roundtrip_preserves_core_fields(self, repo):
        decision = _make_decision("20241104000334")
        repo.upsert([decision])

        got = repo.get_all()[0]

        assert got.rcept_no == "20241104000334"
        assert got.company_name == "테스트회사"
        assert got.sequence_number == "4"
        assert got.bond_type == "기명식 무보증 비분리형 사모 신주인수권부사채"
        assert got.face_value_total == 43_500_000_000
        assert got.issue_method == "사모"
        assert got.exercise_ratio == 100.0
        assert got.exercise_price == 8713
        assert got.exercise_shares == 4_992_540
        assert got.shares_ratio == 19.12
        assert got.maturity_date == date(2027, 12, 22)
        assert got.exercise_start_date == date(2025, 12, 22)
        assert got.exercise_end_date == date(2027, 12, 21)
        assert got.subscription_date == date(2024, 11, 4)
        assert got.payment_date == date(2024, 12, 22)
        assert got.board_resolution_date == date(2024, 11, 4)
        assert got.disclosure_date == date(2024, 11, 4)
        assert got.report_name == "주요사항보고서(신주인수권부사채권발행결정)"
        assert got.is_correction is False

    def test_roundtrip_preserves_funding_purpose(self, repo):
        repo.upsert([_make_decision("20241104000334")])
        got = repo.get_all()[0]
        assert got.funding.facility == 0
        assert got.funding.operating == 43_500_000_000
        assert got.funding.acquisition == 0
        assert got.funding.debt_repayment == 0
        assert got.funding.business_acquisition == 0
        assert got.funding.other == 0

    def test_roundtrip_preserves_parent_rcp_no(self, repo):
        repo.upsert([_make_decision("20241104000001")])
        repo.upsert([_make_decision("20241105000002", parent_rcp_no="20241104000001")])

        got = {d.rcept_no: d for d in repo.get_all()}
        assert got["20241105000002"].parent_rcp_no == "20241104000001"
        assert got["20241104000001"].parent_rcp_no is None

    def test_upsert_returns_count(self, repo):
        count = repo.upsert([_make_decision("20241104000001"), _make_decision("20241104000002")])
        assert count == 2


class TestDedupeByRceptNo:
    def test_reupsert_same_rcept_no_updates_in_place(self, repo):
        repo.upsert([_make_decision("20241104000001", company_name="구버전")])
        repo.upsert([_make_decision("20241104000001", company_name="신버전")])

        result = repo.get_all()

        assert len(result) == 1
        assert result[0].company_name == "신버전"

    def test_mixed_new_and_existing_rcept_no(self, repo):
        repo.upsert([_make_decision("20241104000001")])
        repo.upsert([
            _make_decision("20241104000001", company_name="업데이트됨"),
            _make_decision("20241105000002", company_name="신규"),
        ])

        result = {d.rcept_no: d for d in repo.get_all()}
        assert len(result) == 2
        assert result["20241104000001"].company_name == "업데이트됨"
        assert result["20241105000002"].company_name == "신규"
