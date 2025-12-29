"""무상증자 XML 파싱 인프라스트럭처

DART XML 파일을 파싱하여 무상증자 도메인 모델로 변환합니다.
"""
import os
from datetime import datetime
from typing import Optional
from lxml import etree

from ..domain import BonusSharesDecision, StockInfo


__all__ = ["BonusSharesXmlParser"]


class BonusSharesXmlParser:
    """무상증자 DART XML 파서
    
    XML 파일에서 데이터를 추출하여 무상증자 도메인 모델로 변환합니다.
    """

    @staticmethod
    def _clean_int(text: str) -> int:
        """문자열을 정수로 변환합니다."""
        if not text:
            return 0
        clean_text = text.replace(",", "").strip()
        if clean_text in ("-", ""):
            return 0
        try:
            return int(clean_text)
        except ValueError:
            return 0

    @staticmethod
    def _clean_float(text: str) -> float:
        """문자열을 실수로 변환합니다."""
        if not text:
            return 0.0
        clean_text = text.replace(",", "").strip()
        if clean_text in ("-", ""):
            return 0.0
        try:
            return float(clean_text)
        except ValueError:
            return 0.0

    @staticmethod
    def _parse_date(node) -> Optional[datetime.date]:
        """XML 노드에서 날짜를 추출합니다."""
        if node is None:
            return None

        # AUNITVALUE 속성 (YYYYMMDD) 우선
        date_str = node.get("AUNITVALUE")

        # 속성이 없으면 텍스트에서 숫자만 추출
        if not date_str:
            raw_text = "".join(node.itertext()).strip()
            date_str = "".join(filter(str.isdigit, raw_text))

        # 날짜 변환
        if date_str and len(date_str) == 8:
            try:
                return datetime.strptime(date_str, "%Y%m%d").date()
            except ValueError:
                return None
        return None

    @staticmethod
    def _get_text(node) -> str:
        """XML 노드에서 안전하게 텍스트를 추출합니다."""
        if node is None:
            return ""
        return "".join(node.itertext()).strip()

    @classmethod
    def parse(cls, file_path: str) -> Optional[BonusSharesDecision]:
        """XML 파일을 파싱하여 무상증자 도메인 객체로 변환합니다.
        
        Args:
            file_path: XML 파일 경로
            
        Returns:
            파싱된 무상증자 결정 객체. 파싱 실패 시 None
        """
        try:
            parser = etree.XMLParser(recover=True)
            tree = etree.parse(file_path, parser)
            root = tree.getroot()

            # 기본 정보
            crp_nm_node = root.find(".//TE[@ACODE='CRP_NM']")

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

            # 비율
            ratio_node = root.find(".//TE[@ACODE='NEW_ASN_CNT']")

            # 날짜 정보
            drc_node = root.find(".//TU[@AUNIT='DRC_DT']")  # 이사회결의일
            dis_node = root.find(".//TU[@AUNIT='DIS_DT']")  # 공시일
            rec_node = root.find(".//TU[@AUNIT='ALL_BS_DT']")  # 신주배정기준일
            lst_node = root.find(".//TU[@AUNIT='LST_DT']")  # 신주상장예정일

            return BonusSharesDecision(
                source_filename=os.path.basename(file_path),
                company_name=cls._get_text(crp_nm_node) or "Unknown",
                new_shares=stock_info,
                par_value=cls._clean_int(cls._get_text(par_val_node)),
                total_shares_before=cls._clean_int(cls._get_text(bfr_stock_node)),
                assign_per_share=cls._clean_float(cls._get_text(ratio_node)),
                board_resolution_date=cls._parse_date(drc_node),
                disclosure_date=cls._parse_date(dis_node),
                record_date=cls._parse_date(rec_node),
                listing_date=cls._parse_date(lst_node)
            )
        except Exception as e:
            print(f"[Parser Error] {file_path}: {e}")
            return None
