"""무상증자 엑셀 파일 작성 인프라스트럭처

무상증자 데이터를 연도별 시트로 구분하여 엑셀 파일로 저장합니다.
"""
import os
from pathlib import Path
from typing import List

import pandas as pd

from ..domain import BonusSharesDecision
from .excel_utils import apply_auto_column_width


__all__ = ["BonusSharesExcelWriter"]


class BonusSharesExcelWriter:
    """무상증자 데이터 엑셀 작성기
    
    무상증자 도메인 모델 리스트를 받아 연도별 시트로 분리하여 엑셀 파일을 생성합니다.
    """

    EXCEL_COLUMNS = [
        "일자",
        "종목명",
        "기재정정여부",
        "접수번호",
        "상위접수번호",
        "이사회결의일",
        "신주의 종류와 수",
        "1주당 액면가액",
        "증자전 발행주식총수",
        "신주배정기준일",
        "1주당 신주배정 주식수",
        "신주의 상장 예정일",
        "최초공시일"
    ]

    def __init__(self, output_path: str = "data/무상증자/무상증자.xlsx"):
        """엑셀 작성기를 초기화합니다.
        
        Args:
            output_path: 엑셀 파일 저장 경로
        """
        self.output_path = Path(output_path)

    @staticmethod
    def _format_date(date_obj) -> str:
        """날짜 객체를 YYYY-MM-DD 문자열로 변환합니다."""
        return date_obj.strftime("%Y-%m-%d") if date_obj else ""

    @staticmethod
    def _format_stock_info(stock_info) -> str:
        """주식 정보를 문자열(보통주 수량)로 변환합니다."""
        # 보통주 수량만 쉼표 포함 숫자로 표기
        if stock_info.common > 0:
            return f"{stock_info.common:,}"
        return "0"

    def _to_row_dict(self, decision: BonusSharesDecision) -> dict:
        """도메인 모델을 엑셀 행 딕셔너리로 변환합니다.
        
        Args:
            decision: 무상증자 결정 객체
            
        Returns:
            엑셀 행 딕셔너리
        """
        disclosure_dt = self._format_date(decision.disclosure_date)

        return {
            "일자": disclosure_dt,
            "종목명": decision.company_name,
            "기재정정여부": "[기재정정]" if decision.is_correction else "",
            "접수번호": decision.rcept_no,
            "상위접수번호": decision.parent_rcp_no if decision.parent_rcp_no else "",
            "이사회결의일": self._format_date(decision.board_resolution_date),
            "신주의 종류와 수": self._format_stock_info(decision.new_shares),
            "1주당 액면가액": decision.par_value,
            "증자전 발행주식총수": decision.total_shares_before,
            "신주배정기준일": self._format_date(decision.record_date),
            "1주당 신주배정 주식수": decision.assign_per_share if decision.assign_per_share > 0 else "",
            "신주의 상장 예정일": self._format_date(decision.listing_date),
            "최초공시일": self._format_date(decision.original_disclosure_date),
            "연도": decision.year
        }

    def write(self, decisions: List[BonusSharesDecision]) -> None:
        """무상증자 결정 목록을 엑셀 파일로 저장합니다.
        
        Args:
            decisions: 무상증자 결정 객체 리스트
        """
        # 딕셔너리 리스트로 변환
        data_rows = [self._to_row_dict(d) for d in decisions]

        # DataFrame 생성
        df = pd.DataFrame(data_rows, columns=self.EXCEL_COLUMNS + ["연도"])

        # 출력 디렉토리 생성
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        # 연도 없는 데이터 필터링
        df = df[df["연도"].notna()]

        # 일자 기준 오름차순 정렬
        df = df.sort_values(by="일자", ascending=True)

        # 연도별로 그룹화
        years = sorted(df["연도"].unique())

        # 엑셀 저장 (연도별 시트)
        with pd.ExcelWriter(self.output_path, engine='openpyxl') as writer:
            for year in years:
                year_df = df[df["연도"] == year][self.EXCEL_COLUMNS]  # 연도 컬럼 제외
                sheet_name = str(int(year))
                year_df.to_excel(writer, sheet_name=sheet_name, index=False, startrow=1)
                
                # 컬럼 너비 자동 조정
                apply_auto_column_width(writer.sheets[sheet_name])
                
                print(f"  [{sheet_name}] 시트: {len(year_df)}건")

        print(f"\n[SUCCESS] 엑셀 생성 완료: {self.output_path}")
        print(f"[INFO] 총 {len(df)}건의 데이터가 {len(years)}개 시트에 저장되었습니다.")
        print(f"[INFO] 생성된 시트: {', '.join([str(int(y)) for y in years])}")
