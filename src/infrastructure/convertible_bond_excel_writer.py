"""전환사채 엑셀 파일 작성 인프라스트럭처

전환사채 데이터를 연도별 시트로 구분하여 엑셀 파일로 저장합니다.
"""
import os
from pathlib import Path
from typing import List

import pandas as pd

from ..domain import ConvertibleBondDecision
from .excel_utils import apply_auto_column_width


__all__ = ["ConvertibleBondExcelWriter"]


class ConvertibleBondExcelWriter:
    """전환사채 데이터 엑셀 작성기
    
    전환사채 도메인 모델 리스트를 받아 연도별 시트로 분리하여 엑셀 파일을 생성합니다.
    """

    EXCEL_COLUMNS = [
        "공시일",
        "상호",
        "기재정정여부",
        "회차",
        "종류",
        "사채의 권면(전자등록)총액",
        "권면(전자등록)총액",
        "시설자금",
        "운영자금",
        "영업양수자금",
        "타법인증권",
        "채무상환자금",
        "기타자금",
        "사채의 만기일",
        "사채발행방법",
        "전환비율",
        "전환가액",
        "전환에 따라 발행할 주식수",
        "주식총수 대비 비율",
        "전환청구기간시작일",
        "전환청구기간종료일",
        "청약일",
        "납입일",
        "이사회결의일",
        "접수번호",
        "상위접수번호",
        "최초공시일"
    ]

    def __init__(self, output_path: str = "data/전환사채/전환사채.xlsx"):
        """엑셀 작성기를 초기화합니다.
        
        Args:
            output_path: 엑셀 파일 저장 경로
        """
        self.output_path = Path(output_path)

    @staticmethod
    def _format_date(date_obj) -> str:
        """날짜 객체를 YYYY-MM-DD 문자열로 변환합니다."""
        return date_obj.strftime("%Y-%m-%d") if date_obj else ""

    def _to_row_dict(self, decision: ConvertibleBondDecision) -> dict:
        """도메인 모델을 엑셀 행 딕셔너리로 변환합니다.
        
        Args:
            decision: 전환사채 결정 객체
            
        Returns:
            엑셀 행 딕셔너리
        """
        return {
            "공시일": self._format_date(decision.disclosure_date),
            "상호": decision.company_name,
            "기재정정여부": "[기재정정]" if decision.is_correction else "",
            "회차": decision.sequence_number if decision.sequence_number else "",
            "종류": decision.bond_type if decision.bond_type else "",
            "사채의 권면(전자등록)총액": decision.face_value_total if decision.face_value_total else "",
            "권면(전자등록)총액": decision.face_value_total if decision.face_value_total else "",
            "시설자금": decision.funding.facility if decision.funding and decision.funding.facility else "",
            "운영자금": decision.funding.operating if decision.funding and decision.funding.operating else "",
            "영업양수자금": decision.funding.business_acquisition if decision.funding and decision.funding.business_acquisition else "",
            "타법인증권": decision.funding.acquisition if decision.funding and decision.funding.acquisition else "",
            "채무상환자금": decision.funding.debt_repayment if decision.funding and decision.funding.debt_repayment else "",
            "기타자금": decision.funding.other if decision.funding and decision.funding.other else "",
            "사채의 만기일": self._format_date(decision.maturity_date),
            "사채발행방법": decision.issue_method if decision.issue_method else "",
            "전환비율": decision.conversion_ratio if decision.conversion_ratio is not None else "",
            "전환가액": decision.conversion_price if decision.conversion_price else "",
            "전환에 따라 발행할 주식수": decision.conversion_shares if decision.conversion_shares else "",
            "주식총수 대비 비율": decision.shares_ratio if decision.shares_ratio is not None else "",
            "전환청구기간시작일": self._format_date(decision.conversion_start_date),
            "전환청구기간종료일": self._format_date(decision.conversion_end_date),
            "청약일": self._format_date(decision.subscription_date),
            "납입일": self._format_date(decision.payment_date),
            "이사회결의일": self._format_date(decision.board_resolution_date),
            "접수번호": decision.rcept_no if decision.rcept_no else "",
            "상위접수번호": decision.parent_rcp_no if decision.parent_rcp_no else "",
            "최초공시일": self._format_date(decision.original_disclosure_date),
            "연도": decision.year
        }

    def write(self, decisions: List[ConvertibleBondDecision]) -> None:
        """전환사채 결정 목록을 엑셀 파일로 저장합니다.
        
        Args:
            decisions: 전환사채 결정 객체 리스트
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
                
                print(f"  [{sheet_name}] 시트: {len(year_df)}건")

        print(f"\n[SUCCESS] 엑셀 생성 완료: {self.output_path}")
        print(f"[INFO] 총 {len(df)}건의 데이터가 {len(years)}개 시트에 저장되었습니다.")
        print(f"[INFO] 생성된 시트: {', '.join([str(int(y)) for y in years])}")
