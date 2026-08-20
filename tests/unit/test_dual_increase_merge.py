"""DualIncreaseService._merge_to_main_excel 특성화(characterization) 테스트

리팩토링(단계별 헬퍼 메서드 분리) 전후 동작이 동일함을 보장하기 위한 회귀 안전망입니다.
"""
from datetime import date

import pandas as pd
import pytest

from src.application.dual_increase_service import DualIncreaseService
from src.domain import CapitalIncreaseDecision
from src.domain.value_objects import StockInfo, FundingPurpose


@pytest.fixture
def service(tmp_path):
    return DualIncreaseService(
        data_directory=str(tmp_path / "data"),
        api_key="dummy-key",
        enable_google_drive=False,
    )


def _make_decision(rcept_no: str, company_name: str, disclosure_year: int) -> CapitalIncreaseDecision:
    return CapitalIncreaseDecision(
        source_filename=f"{company_name}_{rcept_no}.xml",
        company_name=company_name,
        new_shares=StockInfo(common=1000, preferred=0),
        par_value=500,
        total_shares_before=10000,
        issue_price=1000,
        funding=FundingPurpose(facility=0, operating=1000, acquisition=0, other=0),
        method="일반공모",
        assign_per_share=0.1,
        board_resolution_date=date(disclosure_year, 1, 1),
        disclosure_date=date(disclosure_year, 1, 2),
        record_date=date(disclosure_year, 1, 10),
        subscription_date=date(disclosure_year, 1, 15),
        payment_date=date(disclosure_year, 1, 20),
        rcept_no=rcept_no,
    )


class TestMergeToMainExcel:
    def test_creates_file_with_new_decisions(self, service, tmp_path):
        """기존 파일이 없을 때: 신규 데이터만으로 파일 생성"""
        out = tmp_path / "out.xlsx"
        decisions = [
            _make_decision("20240101000001", "회사A", 2024),
            _make_decision("20240101000002", "회사B", 2024),
        ]

        service._merge_to_main_excel(out, decisions, is_capital=True)

        assert out.exists()
        df = pd.read_excel(out, sheet_name="2024", header=1)
        assert set(df["접수번호"].astype(str)) == {"20240101000001", "20240101000002"}

    def test_merges_with_existing_and_dedupes_by_rcept_no(self, service, tmp_path):
        """기존 파일이 있을 때: 병합 + 접수번호 기준 중복 제거(최신 데이터 우선)"""
        out = tmp_path / "out.xlsx"

        # 1차: 초기 데이터 저장
        service._merge_to_main_excel(
            out,
            [_make_decision("20240101000001", "회사A-구버전", 2024)],
            is_capital=True,
        )

        # 2차: 같은 접수번호를 다른 회사명으로 재파싱한 데이터 + 새로운 데이터
        service._merge_to_main_excel(
            out,
            [
                _make_decision("20240101000001", "회사A-신버전", 2024),
                _make_decision("20250101000002", "회사C", 2025),
            ],
            is_capital=True,
        )

        df_2024 = pd.read_excel(out, sheet_name="2024", header=1)
        df_2025 = pd.read_excel(out, sheet_name="2025", header=1)

        # 접수번호 중복 없이 1건만 남고, 최신(신버전) 데이터로 덮어써져야 함
        assert len(df_2024) == 1
        assert df_2024.iloc[0]["종목명"] == "회사A-신버전"
        assert len(df_2025) == 1
        assert df_2025.iloc[0]["종목명"] == "회사C"

    def test_no_existing_file_and_no_new_decisions_is_noop(self, service, tmp_path):
        """기존 파일도 없고 신규 데이터도 없으면 파일을 생성하지 않음"""
        out = tmp_path / "out.xlsx"
        service._merge_to_main_excel(out, [], is_capital=True)
        assert not out.exists()
