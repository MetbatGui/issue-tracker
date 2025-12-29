"""엑셀 파일 작성 인프라스트럭처

유상증자 데이터를 연도별 시트로 구분하여 엑셀 파일로 저장합니다.
"""
import os
from pathlib import Path
from typing import List

import pandas as pd

from ..domain import CapitalIncreaseDecision


__all__ = ["ExcelWriter"]


class ExcelWriter:
    """유상증자 데이터 엑셀 작성기
    
    도메인 모델 리스트를 받아 연도별 시트로 분리하여 엑셀 파일을 생성합니다.
    """

    EXCEL_COLUMNS = [
        "일자",
        "종목명",
        "유상증자공시일",
        "신주발행주식수",
        "1주당 액면가",
        "증자전 발행주식총수",
        "시설자금",
        "운영자금",
        "타법인증권",
        "기타자금",
        "증자방식",
        "신주의 발행가액",
        "발행확정가액",
        "신주배정기준일",
        "1주당 신주배정주식수",
        "청약예정일",
        "납입일",
        "신주상장일",
        "이사회결의일"
    ]

    def __init__(self, output_path: str = "data/유상증자/유상증자.xlsx"):
        """엑셀 작성기를 초기화합니다.
        
        Args:
            output_path: 엑셀 파일 저장 경로
        """
        self.output_path = Path(output_path)

    @staticmethod
    def _format_date(date_obj) -> str:
        """날짜 객체를 YYYY-MM-DD 문자열로 변환합니다."""
        return date_obj.strftime("%Y-%m-%d") if date_obj else ""

    def _to_row_dict(self, decision: CapitalIncreaseDecision) -> dict:
        """도메인 모델을 엑셀 행 딕셔너리로 변환합니다.
        
        Args:
            decision: 유상증자 결정 객체
            
        Returns:
            엑셀 행 딕셔너리
        """
        disclosure_dt = self._format_date(decision.disclosure_date)

        return {
            "일자": disclosure_dt,
            "종목명": decision.company_name,
            "유상증자공시일": disclosure_dt,
            "신주발행주식수": decision.new_shares.common,
            "1주당 액면가": decision.par_value,
            "증자전 발행주식총수": decision.total_shares_before,
            "시설자금": decision.funding.facility,
            "운영자금": decision.funding.operating,
            "타법인증권": decision.funding.acquisition,
            "기타자금": decision.funding.other,
            "증자방식": decision.method,
            "신주의 발행가액": decision.issue_price,
            "발행확정가액": "",
            "신주배정기준일": self._format_date(decision.record_date),
            "1주당 신주배정주식수": decision.assign_per_share if decision.assign_per_share > 0 else "",
            "청약예정일": self._format_date(decision.subscription_date),
            "납입일": self._format_date(decision.payment_date),
            "신주상장일": "",
            "이사회결의일": self._format_date(decision.board_resolution_date),
            "연도": decision.year
        }

    def write(self, decisions: List[CapitalIncreaseDecision]) -> None:
        """유상증자 결정 목록을 엑셀 파일로 저장합니다.
        
        Args:
            decisions: 유상증자 결정 객체 리스트
        """
        # 딕셔너리 리스트로 변환
        data_rows = [self._to_row_dict(d) for d in decisions]

        # DataFrame 생성
        df = pd.DataFrame(data_rows, columns=self.EXCEL_COLUMNS + ["연도"])

        # 출력 디렉토리 생성
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        # 연도 없는 데이터 필터링
        df = df[df["연도"].notna()]

        # 연도별로 그룹화
        years = sorted(df["연도"].unique())

        # 엑셀 저장 (연도별 시트)
        with pd.ExcelWriter(self.output_path, engine='openpyxl') as writer:
            for year in years:
                year_df = df[df["연도"] == year][self.EXCEL_COLUMNS]  # 연도 컬럼 제외
                sheet_name = str(int(year))
                year_df.to_excel(writer, sheet_name=sheet_name, index=False, startrow=1)
                print(f"  📄 {sheet_name} 시트: {len(year_df)}건")

        print(f"\n✅ 엑셀 생성 완료: {self.output_path}")
        print(f"📊 총 {len(df)}건의 데이터가 {len(years)}개 시트에 저장되었습니다.")
        print(f"📅 생성된 시트: {', '.join([str(int(y)) for y in years])}")
