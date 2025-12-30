"""유무상증자 XML 파싱 인프라스트럭처

DART XML 파일을 파싱하여 유상증자와 무상증자 도메인 모델을 모두 변환합니다.
"""
import os
from datetime import datetime
from typing import Optional, Tuple
from lxml import etree

from ..domain import CapitalIncreaseDecision, BonusSharesDecision, StockInfo, FundingPurpose


__all__ = ["DualIncreaseXmlParser"]


class DualIncreaseXmlParser:
    """유무상증자 DART XML 파서
    
    XML 파일에서 데이터를 추출하여 유상증자와 무상증자 도메인 모델로 변환합니다.
    """

    @staticmethod
    def _clean_int(text: str) -> int:
        """문자열을 정수로 변환합니다.
        
        Args:
            text: 변환할 문자열 (쉼표 포함 가능)
            
        Returns:
            변환된 정수값. 변환 실패 시 0 반환
        """
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
        """문자열을 실수로 변환합니다.
        
        Args:
            text: 변환할 문자열 (쉼표 포함 가능)
            
        Returns:
            변환된 실수값. 변환 실패 시 0.0 반환
        """
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
        """XML 노드에서 날짜를 추출합니다.
        
        Args:
            node: XML 노드 (lxml Element)
            
        Returns:
            파싱된 날짜 객체. 파싱 실패 시 None
        """
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
        """XML 노드에서 안전하게 텍스트를 추출합니다.
        
        Args:
            node: XML 노드 (lxml Element)
            
        Returns:
            추출된 텍스트. 노드가 None이면 빈 문자열
        """
        if node is None:
            return ""
        return "".join(node.itertext()).strip()

    @classmethod
    def parse(cls, file_path: str) -> Tuple[Optional[CapitalIncreaseDecision], Optional[BonusSharesDecision]]:
        """XML 파일을 파싱하여 유상증자와 무상증자 도메인 객체로 변환합니다.
        
        Args:
            file_path: XML 파일 경로
            
        Returns:
            (유상증자 결정 객체, 무상증자 결정 객체) 튜플. 파싱 실패 시 (None, None)
        """
        try:
            # recover 모드를 사용하여 Entity 에러 무시
            parser = etree.XMLParser(recover=True)
            tree = etree.parse(file_path, parser)
            root = tree.getroot()

            # 기본 정보
            crp_nm_node = root.find(".//TE[@ACODE='CRP_NM']")
            company_name = cls._get_text(crp_nm_node)

            if not company_name:
                header_name_node = root.find(".//COMPANY-NAME")
                company_name = cls._get_text(header_name_node)
            
            if not company_name:
                # 파일명에서 추출
                base_name = os.path.basename(file_path)
                company_name = base_name.split("_")[0]

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
            par_value = cls._clean_int(cls._get_text(par_val_node))
            total_shares_before = cls._clean_int(cls._get_text(bfr_stock_node))

            # 비율 (NEW_ASN_CNT 또는 NEW_ASN_CST)
            ratio_node = root.find(".//TE[@ACODE='NEW_ASN_CNT']")
            if ratio_node is None:
                ratio_node = root.find(".//TE[@ACODE='NEW_ASN_CST']")
            assign_per_share = cls._clean_float(cls._get_text(ratio_node))

            # 날짜 정보
            drc_node = root.find(".//TU[@AUNIT='DRC_DT']")
            dis_node = root.find(".//TU[@AUNIT='DIS_DT']")
            rec_node = root.find(".//TU[@AUNIT='ALL_BS_DT']")

            board_resolution_date = cls._parse_date(drc_node)
            disclosure_date = cls._parse_date(dis_node)
            record_date = cls._parse_date(rec_node)

            # 유상증자 특화 데이터
            iss_price_node = root.find(".//TE[@ACODE='CST_ISS_VAL']")
            issue_price = cls._clean_int(cls._get_text(iss_price_node))

            # 자금 용도
            fund_info = FundingPurpose(
                facility=cls._clean_int(cls._get_text(root.find(".//TE[@ACODE='FND_USE1']"))),
                operating=cls._clean_int(cls._get_text(root.find(".//TE[@ACODE='FND_USE2']"))),
                acquisition=cls._clean_int(cls._get_text(root.find(".//TE[@ACODE='ANC_ACQ_AMT']"))),
                other=cls._clean_int(cls._get_text(root.find(".//TE[@ACODE='FND_USE3']")))
            )

            # 방식
            method_node = root.find(".//TU[@AUNIT='CI_MTH']")
            method = cls._get_text(method_node)

            # 유상증자 추가 날짜
            pym_node = root.find(".//TU[@AUNIT='PYM_DT']")
            sub_node = root.find(".//TU[@AUNIT='SH_BGN_DT']")
            payment_date = cls._parse_date(pym_node)
            subscription_date = cls._parse_date(sub_node)

            # 무상증자 추가 날짜 (LST_DT 또는 LST_PLN_DT)
            lst_node = root.find(".//TU[@AUNIT='LST_DT']")
            if lst_node is None:
                lst_node = root.find(".//TU[@AUNIT='LST_PLN_DT']")
            listing_date = cls._parse_date(lst_node)

            # 유상증자 객체 생성
            capital_increase = CapitalIncreaseDecision(
                source_filename=os.path.basename(file_path),
                company_name=company_name,
                new_shares=stock_info,
                par_value=par_value,
                total_shares_before=total_shares_before,
                issue_price=issue_price,
                funding=fund_info,
                method=method,
                assign_per_share=assign_per_share,
                board_resolution_date=board_resolution_date,
                disclosure_date=disclosure_date,
                record_date=record_date,
                subscription_date=subscription_date,
                payment_date=payment_date
            )

            # 무상증자 객체 생성
            bonus_shares = BonusSharesDecision(
                source_filename=os.path.basename(file_path),
                company_name=company_name,
                new_shares=stock_info,
                par_value=par_value,
                total_shares_before=total_shares_before,
                assign_per_share=assign_per_share,
                board_resolution_date=board_resolution_date,
                disclosure_date=disclosure_date,
                record_date=record_date,
                listing_date=listing_date
            )

            # 공시일(DIS_DT)이 없으면 파일명에서 추출 시도
            if not capital_increase.disclosure_date:
                import re
                # 파일명 형식: "회사명_YYYYMMDDnnnnnn.xml"
                match = re.search(r'_(\d{8})\d+\.xml$', os.path.basename(file_path))
                if match:
                    date_str = match.group(1)
                    try:
                        extracted_date = datetime.strptime(date_str, "%Y%m%d").date()
                        # dataclass는 frozen=True이므로 replace로 새로운 객체 생성
                        from dataclasses import replace
                        capital_increase = replace(capital_increase, disclosure_date=extracted_date)
                        bonus_shares = replace(bonus_shares, disclosure_date=extracted_date)
                    except ValueError:
                        pass

            return (capital_increase, bonus_shares)

        except Exception as e:
            print(f"[Parser Error] {file_path}: {e}")
            return (None, None)
