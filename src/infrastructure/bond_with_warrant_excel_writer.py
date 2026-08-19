"""신주인수권부사채 엑셀 파일 작성 인프라스트럭처

신주인수권부사채 데이터를 연도별 시트로 구분하여 엑셀 파일로 저장합니다.
"""
from ..domain import BondWithWarrantDecision
from .common_excel_writer import BaseBondExcelWriter


__all__ = ["BondWithWarrantExcelWriter"]


class BondWithWarrantExcelWriter(BaseBondExcelWriter):
    """신주인수권부사채 데이터 엑셀 작성기

    신주인수권부사채 도메인 모델 리스트를 받아 연도별 시트로 분리하여 엑셀 파일을 생성합니다.
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
        "신주인수권 비율",
        "행사가액",
        "행사에 따라 발행할 주식수",
        "주식총수 대비 비율",
        "권리행사기간 시작일",
        "권리행사기간 종료일",
        "청약일",
        "납입일",
        "이사회결의일",
        "접수번호",
        "상위접수번호",
        "최초공시일"
    ]

    def __init__(self, output_path: str = "data/신주인수권부사채/신주인수권부사채.xlsx"):
        """엑셀 작성기를 초기화합니다.

        Args:
            output_path: 엑셀 파일 저장 경로
        """
        super().__init__(output_path)

    def _to_row_dict(self, decision: BondWithWarrantDecision) -> dict:
        """도메인 모델을 엑셀 행 딕셔너리로 변환합니다.

        Args:
            decision: 신주인수권부사채 결정 객체

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
            "신주인수권 비율": decision.exercise_ratio if decision.exercise_ratio is not None else "",
            "행사가액": decision.exercise_price if decision.exercise_price else "",
            "행사에 따라 발행할 주식수": decision.exercise_shares if decision.exercise_shares else "",
            "주식총수 대비 비율": decision.shares_ratio if decision.shares_ratio is not None else "",
            "권리행사기간 시작일": self._format_date(decision.exercise_start_date),
            "권리행사기간 종료일": self._format_date(decision.exercise_end_date),
            "청약일": self._format_date(decision.subscription_date),
            "납입일": self._format_date(decision.payment_date),
            "이사회결의일": self._format_date(decision.board_resolution_date),
            "접수번호": decision.rcept_no if decision.rcept_no else "",
            "상위접수번호": decision.parent_rcp_no if decision.parent_rcp_no else "",
            "최초공시일": self._format_date(decision.original_disclosure_date),
            "연도": decision.year
        }
