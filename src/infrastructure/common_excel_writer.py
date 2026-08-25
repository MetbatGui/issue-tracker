"""Common Excel Writer Infrastructure

Shared write logic for bond-type DART reports (Convertible Bond, Bond with Warrant).
"""
from pathlib import Path
from typing import List

import pandas as pd

from .excel_utils import apply_auto_column_width
from ..logger import get_logger

__all__ = ["BaseBondExcelWriter"]


class BaseBondExcelWriter:
    """사채형 보고서(전환사채/신주인수권부사채)의 공통 엑셀 작성 로직.

    서브클래스는 EXCEL_COLUMNS와 _to_row_dict()를 정의합니다.
    """

    EXCEL_COLUMNS: List[str] = []

    def __init__(self, output_path: str):
        self.output_path = Path(output_path)
        self.logger = get_logger(self.__class__.__name__)

    @staticmethod
    def _format_date(date_obj) -> str:
        """날짜 객체를 YYYY-MM-DD 문자열로 변환합니다."""
        return date_obj.strftime("%Y-%m-%d") if date_obj else ""

    def _to_row_dict(self, decision) -> dict:
        """도메인 모델을 엑셀 행 딕셔너리로 변환합니다. 서브클래스에서 구현합니다."""
        raise NotImplementedError

    def write(self, decisions: List) -> None:
        """결정 목록을 연도별 시트로 구분하여 엑셀 파일로 저장합니다.

        Args:
            decisions: 결정 객체 리스트
        """
        # 딕셔너리 리스트로 변환
        data_rows = [self._to_row_dict(d) for d in decisions]

        # DataFrame 생성
        df = pd.DataFrame(data_rows, columns=self.EXCEL_COLUMNS + ["연도"])

        # 출력 디렉토리 생성
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        # 연도 없는 데이터 필터링
        df = df[df["연도"].notna()]

        # 공시일 기준 오름차순 정렬 (과거순)
        df = df.sort_values(by="공시일", ascending=True)

        # 연도별로 그룹화
        years = sorted(df["연도"].unique(), reverse=True)  # 최신 연도부터

        # 엑셀 저장 (연도별 시트)
        with pd.ExcelWriter(self.output_path, engine='openpyxl') as writer:
            for year in years:
                year_df = df[df["연도"] == year][self.EXCEL_COLUMNS]  # 연도 컬럼 제외
                sheet_name = str(int(year))
                year_df.to_excel(writer, sheet_name=sheet_name, index=False, startrow=0)

                # 컬럼 너비 자동 조정
                apply_auto_column_width(writer.sheets[sheet_name])

                self.logger.info(f"[{sheet_name}] 시트: {len(year_df)}건")

        self.logger.info(f"엑셀 생성 완료: {self.output_path}")
        self.logger.info(f"총 {len(df)}건의 데이터가 {len(years)}개 시트에 저장되었습니다.")
        self.logger.info(f"생성된 시트: {', '.join([str(int(y)) for y in years])}")
