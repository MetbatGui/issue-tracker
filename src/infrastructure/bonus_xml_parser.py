"""무상증자 XML 파싱 인프라스트럭처

DART XML 파일을 파싱하여 무상증자 도메인 모델로 변환합니다.
"""
import os
from datetime import datetime
from typing import Optional
from lxml import etree
from dataclasses import replace

from ..domain import BonusSharesDecision, StockInfo
from .common_xml_parser import BaseXmlParser


__all__ = ["BonusSharesXmlParser"]


class BonusSharesXmlParser(BaseXmlParser):
    """무상증자 DART XML 파서
    
    XML 파일에서 데이터를 추출하여 무상증자 도메인 모델로 변환합니다.
    """

    @classmethod
    def parse(cls, xml_source, rcept_no: Optional[str] = None, parent_rcp_no: Optional[str] = None, source_filename: Optional[str] = None) -> Optional[BonusSharesDecision]:
        """XML 파일을 파싱하여 무상증자 도메인 객체로 변환합니다.
        
        Args:
            xml_source: XML 파일 경로 또는 메모리 file-like 객체
            rcept_no: 접수번호 (제공되지 않으면 파일명에서 추출 시도)
            parent_rcp_no: 상위 공시(이전 정정 공시) 접수번호
            
        Returns:
            파싱된 무상증자 결정 객체. 파싱 실패 시 None
        """
        try:
            parser = etree.XMLParser(recover=True)
            tree = etree.parse(xml_source, parser)
            root = tree.getroot()

            # 공통 정보 추출 (회사명, 보고서명, 정정여부, 파일명 기반 rcept_no)
            common_info = cls._extract_common_info(source_filename or str(xml_source), root)

            # 주식 수량 (신주)
            cst_node = root.find(".//TE[@ACODE='CST_CNT']")
            pst_node = root.find(".//TE[@ACODE='PST_CNT']")
            stock_info = StockInfo(
                common=cls._clean_int(cls._get_text(cst_node)),
                preferred=cls._clean_int(cls._get_text(pst_node))
            )

            # 금액 및 기존 주식
            par_val_node = root.find(".//TE[@ACODE='FVAL']")
            bfr_stock_node = root.find(".//TE[@ACODE='BFR_CST_CNT']")

            # 비율 (NEW_ASN_CNT 또는 NEW_ASN_CST)
            ratio_node = root.find(".//TE[@ACODE='NEW_ASN_CNT']")
            if ratio_node is None:
                ratio_node = root.find(".//TE[@ACODE='NEW_ASN_CST']")

            # 날짜 정보
            drc_node = root.find(".//TU[@AUNIT='DRC_DT']")  # 이사회결의일
            dis_node = root.find(".//TU[@AUNIT='DIS_DT']")  # 공시일
            rec_node = root.find(".//TU[@AUNIT='ALL_BS_DT']")  # 신주배정기준일
            
            # 신주의 상장 예정일 (LST_DT -> LST_PLN_DT -> 텍스트 검색 순)
            lst_date = None
            
            # 1. LST_DT 시도
            lst_node = root.find(".//TU[@AUNIT='LST_DT']")
            lst_date = cls._parse_date(lst_node)

            # 2. LST_PLN_DT 시도
            if not lst_date:
                lst_pln_node = root.find(".//TU[@AUNIT='LST_PLN_DT']")
                lst_date = cls._parse_date(lst_pln_node)

            # 3. 텍스트 레이블("신주의 상장 예정일")로 검색 시도
            if not lst_date:
                # "신주의 상장 예정일" 텍스트를 포함하는 TD 태그 검색
                for td in root.iter("TD"):
                    text = "".join(td.itertext())
                    if "신주의 상장 예정일" in text:
                        # 바로 다음 형제 TU 태그 찾기
                        next_tag = td.getnext()
                        if next_tag is not None and next_tag.tag == "TU":
                            lst_date = cls._parse_date(next_tag)
                            if lst_date:
                                break

            # rcept_no 처리 Priority: 
            # 1. Argument로 전달받은 값
            # 2. 파일명에서 추출한 값 (common_info)
            final_rcept_no = rcept_no if rcept_no else common_info["rcept_no_from_filename"]

            decision = BonusSharesDecision(
                source_filename=common_info["source_filename"],
                company_name=common_info["company_name"],
                new_shares=stock_info,
                par_value=cls._clean_int(cls._get_text(par_val_node)),
                total_shares_before=cls._clean_int(cls._get_text(bfr_stock_node)),
                assign_per_share=cls._clean_float(cls._get_text(ratio_node)),
                board_resolution_date=cls._parse_date(drc_node),
                disclosure_date=cls._parse_date(dis_node),
                record_date=cls._parse_date(rec_node),
                listing_date=lst_date,
                report_name=common_info["report_name"],
                is_correction=common_info["is_correction"],
                rcept_no=final_rcept_no,
                parent_rcp_no=parent_rcp_no
            )

            # 공시일(DIS_DT)이 없으면 rcept_no에서 유추
            if not decision.disclosure_date:
                date_str = None
                # 1. rcept_no의 앞 8자리
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
            # print(f"[Parser Error] {file_path}: {e}")
            return None
