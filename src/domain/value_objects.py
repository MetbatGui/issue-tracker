"""도메인 값 객체 (Value Objects)

불변 객체로 구현되며 비즈니스 개념을 표현합니다.
"""
from dataclasses import dataclass


__all__ = ["StockInfo", "FundingPurpose"]


@dataclass(frozen=True)
class StockInfo:
    """주식 수량 정보
    
    Attributes:
        common: 보통주 수량
        preferred: 우선주 수량
    """
    common: int
    preferred: int

    @property
    def total(self) -> int:
        """전체 주식 수량을 반환합니다."""
        return self.common + self.preferred


@dataclass(frozen=True)
class FundingPurpose:
    """자금 조달 목적
    
    Attributes:
        facility: 시설자금
        operating: 운영자금
        acquisition: 타법인증권 취득자금
        debt_repayment: 채무상환자금
        business_acquisition: 영업양수자금
        other: 기타자금
    """
    facility: int = 0
    operating: int = 0
    acquisition: int = 0
    debt_repayment: int = 0
    business_acquisition: int = 0
    other: int = 0

    @property
    def total(self) -> int:
        """전체 자금 규모를 반환합니다."""
        return (self.facility + self.operating + self.acquisition +
                self.debt_repayment + self.business_acquisition + self.other)
