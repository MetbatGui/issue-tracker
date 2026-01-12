"""도메인 모델 (Domain Models)

비즈니스 엔티티를 표현합니다.
"""
from dataclasses import dataclass
from datetime import date
from typing import Optional

from .value_objects import StockInfo, FundingPurpose


__all__ = ["CapitalIncreaseDecision"]


@dataclass(frozen=True)
class CapitalIncreaseDecision:
    """유상증자 결정 데이터 엔티티
    
    Attributes:
        source_filename: 원본 XML 파일명
        company_name: 회사명
        new_shares: 신주 발행 정보
        par_value: 1주당 액면가
        total_shares_before: 증자 전 발행주식 총수 (보통주 기준)
        issue_price: 신주 발행가액 (예정)
        funding: 자금 조달 목적
        method: 증자 방식
        assign_per_share: 1주당 신주배정주식수
        board_resolution_date: 이사회결의일
        disclosure_date: 공시일
        record_date: 신주배정기준일
        subscription_date: 청약예정일 (시작일)
        payment_date: 납입일
    """
    source_filename: str
    company_name: str
    new_shares: StockInfo
    par_value: int
    total_shares_before: int
    issue_price: int
    funding: FundingPurpose
    method: str
    assign_per_share: float
    board_resolution_date: Optional[date]
    disclosure_date: Optional[date]
    record_date: Optional[date]
    subscription_date: Optional[date]
    payment_date: Optional[date]
    report_name: Optional[str] = None
    is_correction: bool = False

    def is_limited_liability_company(self) -> bool:
        """유한책임회사 여부를 확인합니다."""
        return "유한책임회사" in self.company_name

    @property
    def year(self) -> Optional[int]:
        """공시일 기준 연도를 반환합니다."""
        return self.disclosure_date.year if self.disclosure_date else None


@dataclass(frozen=True)
class BonusSharesDecision:
    """무상증자 결정 데이터 엔티티
    
    Attributes:
        source_filename: 원본 XML 파일명
        company_name: 회사명
        new_shares: 신주 발행 정보 (종류와 수)
        par_value: 1주당 액면가액
        total_shares_before: 증자전 발행주식총수
        assign_per_share: 1주당 신주배정 주식수
        board_resolution_date: 이사회결의일
        disclosure_date: 공시일 (일자)
        record_date: 신주배정기준일
        listing_date: 신주의 상장 예정일
    """
    source_filename: str
    company_name: str
    new_shares: StockInfo
    par_value: int
    total_shares_before: int
    assign_per_share: float
    board_resolution_date: Optional[date]
    disclosure_date: Optional[date]
    record_date: Optional[date]
    listing_date: Optional[date]
    report_name: Optional[str] = None
    is_correction: bool = False

    def is_limited_liability_company(self) -> bool:
        """유한책임회사 여부를 확인합니다."""
        return "유한책임회사" in self.company_name

    @property
    def year(self) -> Optional[int]:
        """공시일 기준 연도를 반환합니다."""
        return self.disclosure_date.year if self.disclosure_date else None

