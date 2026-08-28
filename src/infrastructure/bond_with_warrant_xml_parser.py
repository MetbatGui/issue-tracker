"""신주인수권부사채 XML 파싱 인프라스트럭처

DART XML 파일을 파싱하여 신주인수권부사채 도메인 모델로 변환합니다.
"""
from datetime import datetime
from typing import Optional
from lxml import etree
from dataclasses import replace

from ..domain import BondWithWarrantDecision
from .common_xml_parser import BaseXmlParser


__all__ = ["BondWithWarrantXmlParser"]


class BondWithWarrantXmlParser(BaseXmlParser):
    """신주인수권부사채 DART XML 파서
    
    XML 파일에서 데이터를 추출하여 신주인수권부사채 도메인 모델로 변환합니다.
    """

    @classmethod
    def parse(cls, xml_source, rcept_no: Optional[str] = None, parent_rcp_no: Optional[str] = None, source_filename: Optional[str] = None) -> Optional[BondWithWarrantDecision]:
        """XML 파일을 파싱하여 도메인 객체로 변환합니다.
        
        Args:
            xml_source: XML 파일 경로 또는 메모리 file-like 객체
            rcept_no: 접수번호 (제공되지 않으면 파일명에서 추출 시도)
            parent_rcp_no: 상위 공시(이전 정정 공시) 접수번호
            
        Returns:
            파싱된 신주인수권부사채 결정 객체. 파싱 실패 시 None
        """
        try:
            # recover 모드를 사용하여 Entity 에러 무시
            parser = etree.XMLParser(recover=True)
            tree = etree.parse(xml_source, parser)
            root = tree.getroot()

            # 공통 정보 추출
            common_info = cls._extract_common_info(source_filename or str(xml_source), root)

            # ACODE 기반 필드 (TE 노드)
            # XML ACODE는 CB와 동일한 EXE_RT/EXE_PRC/STK_CNT/STK_RT/SB_BGN_DT/SB_END_DT를 사용함
            # (data/신주인수권부사채/xml 샘플 534건 전수 파싱 검증 완료)
            te_fields = cls._extract_fields(root, "TE", "ACODE", [
                ("sequence_number", "SEQ_NO", str),
                ("bond_type", "PL_KND", str),
                ("face_value_total", "DNM_SUM", cls._clean_int),
                ("facility_fund", "FND_USE1", cls._clean_int),
                ("operating_fund", "FND_USE2", cls._clean_int),
                ("business_acquisition_fund", "FND_USE_SQ", cls._clean_int),
                ("acquisition_fund", "ANC_ACQ_PRC", cls._clean_int),
                ("debt_repayment_fund", "FND_USE_RD", cls._clean_int),
                ("other_fund", "FND_USE3", cls._clean_int),
                ("exercise_ratio", "EXE_RT", cls._clean_float),
                ("exercise_price", "EXE_PRC", cls._clean_int),
                ("exercise_shares", "STK_CNT", cls._clean_int),
                ("shares_ratio", "STK_RT", cls._clean_float),
            ])

            # AUNIT 기반 필드 (TU 노드: 날짜/방법)
            tu_fields = cls._extract_fields(root, "TU", "AUNIT", [
                ("maturity_date", "EXP_DT", cls._parse_korean_date),
                ("issue_method", "ISSU_MTH", str),
                ("exercise_start_date", "SB_BGN_DT", cls._parse_korean_date),
                ("exercise_end_date", "SB_END_DT", cls._parse_korean_date),
                ("subscription_date", "SBSC_DT", cls._parse_korean_date),
                ("payment_date", "PYM_DT", cls._parse_korean_date),
                ("board_resolution_date", "DRC_DT", cls._parse_korean_date),
            ])

            # 자금조달 목적 (FundingPurpose)
            from ..domain.value_objects import FundingPurpose
            funding = FundingPurpose(
                facility=te_fields["facility_fund"] or 0,
                operating=te_fields["operating_fund"] or 0,
                acquisition=te_fields["acquisition_fund"] or 0,
                debt_repayment=te_fields["debt_repayment_fund"] or 0,
                business_acquisition=te_fields["business_acquisition_fund"] or 0,
                other=te_fields["other_fund"] or 0
            )

            final_rcept_no = rcept_no if rcept_no else common_info["rcept_no_from_filename"]

            decision = BondWithWarrantDecision(
                source_filename=common_info["source_filename"],
                company_name=common_info["company_name"],
                sequence_number=te_fields["sequence_number"],
                bond_type=te_fields["bond_type"],
                face_value_total=te_fields["face_value_total"],
                funding=funding,
                interest_rate=None,
                maturity_date=tu_fields["maturity_date"],
                issue_method=tu_fields["issue_method"],
                exercise_ratio=te_fields["exercise_ratio"],
                exercise_price=te_fields["exercise_price"],
                exercise_shares=te_fields["exercise_shares"],
                shares_ratio=te_fields["shares_ratio"],
                exercise_start_date=tu_fields["exercise_start_date"],
                exercise_end_date=tu_fields["exercise_end_date"],
                subscription_date=tu_fields["subscription_date"],
                payment_date=tu_fields["payment_date"],
                board_resolution_date=tu_fields["board_resolution_date"],
                report_name=common_info["report_name"],
                is_correction=common_info["is_correction"],
                rcept_no=final_rcept_no,
                parent_rcp_no=parent_rcp_no
            )

            if not decision.disclosure_date:
                date_str = None
                if decision.rcept_no and len(decision.rcept_no) >= 8:
                    date_str = decision.rcept_no[:8]
                
                if date_str:
                    try:
                        extracted_date = datetime.strptime(date_str, "%Y%m%d").date()
                        decision = replace(decision, disclosure_date=extracted_date)
                    except ValueError:
                        pass

            return decision
        except Exception as e:
            return None
