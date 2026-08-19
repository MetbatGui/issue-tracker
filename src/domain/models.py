"""도메인 모델 (Domain Models)

비즈니스 엔티티를 표현합니다.
"""
from dataclasses import dataclass
from datetime import date
from typing import Optional

from .value_objects import StockInfo, FundingPurpose


__all__ = ["CapitalIncreaseDecision", "BonusSharesDecision", "ConvertibleBondDecision", "BondWithWarrantDecision"]


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
    rcept_no: str = ""
    parent_rcp_no: Optional[str] = None
    original_disclosure_date: Optional[date] = None

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
    rcept_no: str = ""
    parent_rcp_no: Optional[str] = None
    original_disclosure_date: Optional[date] = None

    def is_limited_liability_company(self) -> bool:
        """유한책임회사 여부를 확인합니다."""
        return "유한책임회사" in self.company_name

    @property
    def year(self) -> Optional[int]:
        """공시일 기준 연도를 반환합니다."""
        return self.disclosure_date.year if self.disclosure_date else None


@dataclass(frozen=True)
class ConvertibleBondDecision:
    """전환사채 발행 결정 데이터 엔티티
    
    Attributes:
        source_filename: 원본 XML 파일명
        company_name: 회사명 (상호)
        sequence_number: 회차
        bond_type: 종류
        face_value_total: 사채의 권면(전자등록)총액
        facility_fund: 시설자금
        operating_fund: 운영자금
        acquisition_fund: 타법인증권 취득자금
        other_fund: 기타자금
        interest_rate: 사채의 이율
        maturity_date: 사채의 만기일
        issue_method: 사채발행방법
        conversion_ratio: 전환비율
        conversion_price: 전환가액
        conversion_shares: 전환에 따라 발행할 주식수
        shares_ratio: 주식총수 대비 비율
        conversion_start_date: 전환청구기간시작일
        conversion_end_date: 전환청구기간종료일
        subscription_date: 청약일
        payment_date: 납입일
        board_resolution_date: 이사회결의일
    """
    source_filename: str
    company_name: str
    sequence_number: Optional[str]
    bond_type: Optional[str]
    face_value_total: Optional[int]
    funding: Optional[FundingPurpose]
    interest_rate: Optional[float]
    maturity_date: Optional[date]
    issue_method: Optional[str]
    conversion_ratio: Optional[float]
    conversion_price: Optional[int]
    conversion_shares: Optional[int]
    shares_ratio: Optional[float]
    conversion_start_date: Optional[date]
    conversion_end_date: Optional[date]
    subscription_date: Optional[date]
    payment_date: Optional[date]
    board_resolution_date: Optional[date]
    report_name: Optional[str] = None
    is_correction: bool = False
    rcept_no: str = ""
    parent_rcp_no: Optional[str] = None
    disclosure_date: Optional[date] = None
    original_disclosure_date: Optional[date] = None

    @property
    def year(self) -> Optional[int]:
        """공시일 기준 연도를 반환합니다."""
        return self.disclosure_date.year if self.disclosure_date else None


@dataclass(frozen=True)
class BondWithWarrantDecision:
    """신주인수권부사채 발행 결정 데이터 엔티티
    
    Attributes:
        source_filename: 원본 XML 파일명
        company_name: 회사명 (상호)
        sequence_number: 회차
        bond_type: 종류
        face_value_total: 사채의 권면(전자등록)총액
        funding: 자금 조달 목적
        interest_rate: 사채의 이율
        maturity_date: 사채의 만기일
        issue_method: 사채발행방법
        exercise_ratio: 신주인수권 행사비율 (전환비율 대응)
        exercise_price: 행사가액 (전환가액 대응)
        exercise_shares: 행사에 따라 발행할 주식수 (전환주식수 대응)
        shares_ratio: 주식총수 대비 비율
        exercise_start_date: 권리행사기간 시작일
        exercise_end_date: 권리행사기간 종료일
        subscription_date: 청약일
        payment_date: 납입일
        board_resolution_date: 이사회결의일
    """
    source_filename: str
    company_name: str
    sequence_number: Optional[str]
    bond_type: Optional[str]
    face_value_total: Optional[int]
    funding: Optional[FundingPurpose]
    interest_rate: Optional[float]
    maturity_date: Optional[date]
    issue_method: Optional[str]
    exercise_ratio: Optional[float]
    exercise_price: Optional[int]
    exercise_shares: Optional[int]
    shares_ratio: Optional[float]
    exercise_start_date: Optional[date]
    exercise_end_date: Optional[date]
    subscription_date: Optional[date]
    payment_date: Optional[date]
    board_resolution_date: Optional[date]
    report_name: Optional[str] = None
    is_correction: bool = False
    rcept_no: str = ""
    parent_rcp_no: Optional[str] = None
    disclosure_date: Optional[date] = None
    original_disclosure_date: Optional[date] = None

    @property
    def year(self) -> Optional[int]:
        """공시일 기준 연도를 반환합니다."""
        return self.disclosure_date.year if self.disclosure_date else None
