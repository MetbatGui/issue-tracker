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
                        # 혹은 부모의 다음 TU (구조에 따라 다를 수 있음, 일단 sibling 우선)

            # 회사명 파싱 (CRP_NM -> COMPANY-NAME -> 파일명)
            company_name_node = root.find(".//TE[@ACODE='CRP_NM']")
            company_name = cls._get_text(company_name_node)
            
            if not company_name:
                header_name_node = root.find(".//COMPANY-NAME")
                company_name = cls._get_text(header_name_node)
            
            if not company_name:
                # 파일명에서 추출 (예: "DS단석_2024..." -> "DS단석")
                base_name = os.path.basename(file_path)
                company_name = base_name.split("_")[0]

            # 보고서명 파싱 및 기재정정 여부 확인
            doc_name_node = root.find(".//DOCUMENT-NAME")
            report_name = cls._get_text(doc_name_node)
            
            # 기재정정 여부 판단
            # 1. 문서 명에 '기재정정' 포함
            # 2. CORRECTION 태그 존재
            # 3. TITLE 태그에 '기재정정' 포함
            is_correction = False
            if report_name and "기재정정" in report_name:
                is_correction = True
            elif root.find(".//CORRECTION") is not None:
                is_correction = True
            else:
                for title in root.iter("TITLE"):
                    if "기재정정" in cls._get_text(title):
                        is_correction = True
                        break

            decision = BonusSharesDecision(
                source_filename=os.path.basename(file_path),
                company_name=company_name,
                new_shares=stock_info,
                par_value=cls._clean_int(cls._get_text(par_val_node)),
                total_shares_before=cls._clean_int(cls._get_text(bfr_stock_node)),
                assign_per_share=cls._clean_float(cls._get_text(ratio_node)),
                board_resolution_date=cls._parse_date(drc_node),
                disclosure_date=cls._parse_date(dis_node),
                record_date=cls._parse_date(rec_node),
                listing_date=lst_date,
                report_name=report_name,
                is_correction=is_correction
            )

            # 공시일(DIS_DT)이 없으면 파일명에서 추출 시도
            if not decision.disclosure_date:
                import re
                # 파일명 형식: "회사명_YYYYMMDDnnnnnn.xml"
                match = re.search(r'_(\d{8})\d+\.xml$', os.path.basename(file_path))
                if match:
                    date_str = match.group(1)
                    try:
                        extracted_date = datetime.strptime(date_str, "%Y%m%d").date()
                        # dataclass는 frozen=True이므로 replace로 새로운 객체 생성
                        from dataclasses import replace
                        decision = replace(decision, disclosure_date=extracted_date)
                    except ValueError:
                        pass

            return decision
        except Exception as e:
            print(f"[Parser Error] {file_path}: {e}")
            return None
