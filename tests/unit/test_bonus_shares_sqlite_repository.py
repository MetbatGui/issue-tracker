"""BonusSharesSqliteRepository 테스트

DB SSOT 전환(무상증자, 유상증자에 이은 두 번째 사례) 리포지토리 계층을 :memory: SQLite로 검증합니다.
구현 전에 먼저 작성하여 RED 확인 후 구현합니다.
"""
from datetime import date

import pytest

from src.domain import BonusSharesDecision
from src.domain.value_objects import StockInfo
from src.infrastructure.bonus_shares_sqlite_repository import BonusSharesSqliteRepository


def _make_decision(
    rcept_no: str,
    company_name: str = "테스트회사",
    parent_rcp_no=None,
    disclosure_year: int = 2024,
) -> BonusSharesDecision:
    return BonusSharesDecision(
        source_filename=f"{company_name}_{rcept_no}.xml",
        company_name=company_name,
        new_shares=StockInfo(common=500, preferred=20),
        par_value=500,
        total_shares_before=10000,
        assign_per_share=0.5,
        board_resolution_date=date(disclosure_year, 1, 1),
        disclosure_date=date(disclosure_year, 1, 2),
        record_date=date(disclosure_year, 1, 10),
        listing_date=date(disclosure_year, 1, 25),
        report_name="주요사항보고서(무상증자결정)",
        is_correction=False,
        rcept_no=rcept_no,
        parent_rcp_no=parent_rcp_no,
        original_disclosure_date=None,
    )


@pytest.fixture
def repo():
    return BonusSharesSqliteRepository(":memory:")


class TestUpsertAndGetAll:
    def test_roundtrip_preserves_core_fields(self, repo):
        decision = _make_decision("20240101000001")
        repo.upsert([decision])

        got = repo.get_all()[0]

        assert got.rcept_no == "20240101000001"
        assert got.company_name == "테스트회사"
        assert got.par_value == 500
        assert got.total_shares_before == 10000
        assert got.assign_per_share == 0.5
        assert got.board_resolution_date == date(2024, 1, 1)
        assert got.disclosure_date == date(2024, 1, 2)
        assert got.record_date == date(2024, 1, 10)
        assert got.listing_date == date(2024, 1, 25)
        assert got.report_name == "주요사항보고서(무상증자결정)"
        assert got.is_correction is False

    def test_roundtrip_preserves_stock_info_including_preferred(self, repo):
        """현재 Excel 파이프라인에서 버려지는 우선주 수량이 DB에는 보존되어야 함"""
        repo.upsert([_make_decision("20240101000001")])
        got = repo.get_all()[0]
        assert got.new_shares.common == 500
        assert got.new_shares.preferred == 20

    def test_roundtrip_preserves_parent_rcp_no(self, repo):
        repo.upsert([_make_decision("20240101000001")])
        repo.upsert([_make_decision("20240102000002", parent_rcp_no="20240101000001")])

        got = {d.rcept_no: d for d in repo.get_all()}
        assert got["20240102000002"].parent_rcp_no == "20240101000001"
        assert got["20240101000001"].parent_rcp_no is None

    def test_upsert_returns_count(self, repo):
        count = repo.upsert([_make_decision("20240101000001"), _make_decision("20240101000002")])
        assert count == 2

    def test_upsert_rolls_back_every_write_when_later_item_fails(self, repo):
        with pytest.raises(AttributeError):
            repo.upsert([_make_decision("20240101000001"), None])

        assert repo.get_all() == []


class TestDedupeByRceptNo:
    def test_reupsert_same_rcept_no_updates_in_place(self, repo):
        repo.upsert([_make_decision("20240101000001", company_name="구버전")])
        repo.upsert([_make_decision("20240101000001", company_name="신버전")])

        result = repo.get_all()

        assert len(result) == 1
        assert result[0].company_name == "신버전"

    def test_reupsert_updates_listing_date(self, repo):
        """listing_date는 유상증자의 manual-only 필드와 달리 실제 파싱값이라 재upsert 시 갱신되어야 함"""
        repo.upsert([_make_decision("20240101000001")])
        updated = _make_decision("20240101000001")
        from dataclasses import replace
        updated = replace(updated, listing_date=date(2024, 2, 1))
        repo.upsert([updated])

        got = repo.get_all()[0]
        assert got.listing_date == date(2024, 2, 1)
