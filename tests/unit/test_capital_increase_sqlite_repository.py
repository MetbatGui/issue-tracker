"""CapitalIncreaseSqliteRepository 테스트

DB SSOT 전환(유상증자 파일럿)의 리포지토리 계층을 :memory: SQLite로 검증합니다.
구현 전에 먼저 작성하여 RED 확인 후 구현합니다.
"""
from datetime import date

import pytest

from src.domain import CapitalIncreaseDecision
from src.domain.value_objects import StockInfo, FundingPurpose
from src.infrastructure.capital_increase_sqlite_repository import CapitalIncreaseSqliteRepository


def _make_decision(
    rcept_no: str,
    company_name: str = "테스트회사",
    parent_rcp_no=None,
    disclosure_year: int = 2024,
) -> CapitalIncreaseDecision:
    return CapitalIncreaseDecision(
        source_filename=f"{company_name}_{rcept_no}.xml",
        company_name=company_name,
        new_shares=StockInfo(common=1000, preferred=50),
        par_value=500,
        total_shares_before=10000,
        issue_price=1200,
        funding=FundingPurpose(facility=100, operating=200, acquisition=0, other=10),
        method="일반공모",
        assign_per_share=0.1,
        board_resolution_date=date(disclosure_year, 1, 1),
        disclosure_date=date(disclosure_year, 1, 2),
        record_date=date(disclosure_year, 1, 10),
        subscription_date=date(disclosure_year, 1, 15),
        payment_date=date(disclosure_year, 1, 20),
        report_name="주요사항보고서(유상증자결정)",
        is_correction=False,
        rcept_no=rcept_no,
        parent_rcp_no=parent_rcp_no,
        original_disclosure_date=None,
    )


@pytest.fixture
def repo():
    return CapitalIncreaseSqliteRepository(":memory:")


class TestUpsertAndGetAll:
    def test_roundtrip_preserves_core_fields(self, repo):
        decision = _make_decision("20240101000001")
        repo.upsert([decision])

        result = repo.get_all()

        assert len(result) == 1
        got = result[0]
        assert got.rcept_no == "20240101000001"
        assert got.company_name == "테스트회사"
        assert got.par_value == 500
        assert got.total_shares_before == 10000
        assert got.issue_price == 1200
        assert got.method == "일반공모"
        assert got.assign_per_share == 0.1
        assert got.board_resolution_date == date(2024, 1, 1)
        assert got.disclosure_date == date(2024, 1, 2)
        assert got.record_date == date(2024, 1, 10)
        assert got.subscription_date == date(2024, 1, 15)
        assert got.payment_date == date(2024, 1, 20)
        assert got.report_name == "주요사항보고서(유상증자결정)"
        assert got.is_correction is False

    def test_roundtrip_preserves_stock_info_including_preferred(self, repo):
        """현재 Excel 파이프라인에서 버려지는 우선주 수량이 DB에는 보존되어야 함"""
        repo.upsert([_make_decision("20240101000001")])
        got = repo.get_all()[0]
        assert got.new_shares.common == 1000
        assert got.new_shares.preferred == 50

    def test_roundtrip_preserves_funding_purpose(self, repo):
        repo.upsert([_make_decision("20240101000001")])
        got = repo.get_all()[0]
        assert got.funding.facility == 100
        assert got.funding.operating == 200
        assert got.funding.acquisition == 0
        assert got.funding.other == 10
        assert got.funding.debt_repayment == 0
        assert got.funding.business_acquisition == 0

    def test_roundtrip_preserves_parent_rcp_no(self, repo):
        repo.upsert([_make_decision("20240101000001")])
        repo.upsert([_make_decision("20240102000002", parent_rcp_no="20240101000001")])

        got = {d.rcept_no: d for d in repo.get_all()}
        assert got["20240102000002"].parent_rcp_no == "20240101000001"
        assert got["20240101000001"].parent_rcp_no is None

    def test_upsert_returns_count(self, repo):
        count = repo.upsert([_make_decision("20240101000001"), _make_decision("20240101000002")])
        assert count == 2


class TestDedupeByRceptNo:
    def test_reupsert_same_rcept_no_updates_in_place(self, repo):
        repo.upsert([_make_decision("20240101000001", company_name="구버전")])
        repo.upsert([_make_decision("20240101000001", company_name="신버전")])

        result = repo.get_all()

        assert len(result) == 1
        assert result[0].company_name == "신버전"

    def test_mixed_new_and_existing_rcept_no(self, repo):
        repo.upsert([_make_decision("20240101000001")])
        repo.upsert([
            _make_decision("20240101000001", company_name="업데이트됨"),
            _make_decision("20240102000002", company_name="신규"),
        ])

        result = {d.rcept_no: d for d in repo.get_all()}
        assert len(result) == 2
        assert result["20240101000001"].company_name == "업데이트됨"
        assert result["20240102000002"].company_name == "신규"


class TestManualFieldsProtected:
    """final_issue_price/listing_date는 도메인 모델에 없는 DB 전용(수동입력) 컬럼.
    자동 파이프라인 upsert가 절대 덮어쓰면 안 됨.
    """

    def test_reupsert_does_not_clear_manually_set_final_issue_price(self, repo):
        repo.upsert([_make_decision("20240101000001")])

        # 수동으로 값을 채운 상황을 시뮬레이션 (Excel에서 사람이 입력한 값을 마이그레이션으로 가져온 경우 등)
        # :memory: DB는 커넥션마다 별개 인스턴스이므로 repo가 물고 있는 커넥션을 직접 사용해야 함
        repo._conn.execute(
            "UPDATE capital_increase_decisions SET final_issue_price = ?, listing_date = ? WHERE rcept_no = ?",
            ("1,250", "2024-02-01", "20240101000001"),
        )
        repo._conn.commit()

        # 동일 rcept_no로 재파싱 데이터가 다시 upsert되어도
        repo.upsert([_make_decision("20240101000001", company_name="재파싱됨")])

        row = repo._conn.execute(
            "SELECT final_issue_price, listing_date FROM capital_increase_decisions WHERE rcept_no = ?",
            ("20240101000001",),
        ).fetchone()

        assert row == ("1,250", "2024-02-01")
