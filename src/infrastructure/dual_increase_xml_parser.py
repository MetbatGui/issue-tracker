"""유무상증자 XML 파싱 인프라스트럭처

DART XML 파일을 파싱하여 유상증자와 무상증자 도메인 모델을 모두 변환합니다.
"""
import os
from datetime import datetime
from typing import Optional, Tuple
from lxml import etree
from dataclasses import replace

from ..domain import CapitalIncreaseDecision, BonusSharesDecision, StockInfo, FundingPurpose
from .common_xml_parser import BaseXmlParser


__all__ = ["DualIncreaseXmlParser"]


class DualIncreaseXmlParser(BaseXmlParser):
    """유무상증자 DART XML 파서
    
    XML 파일에서 데이터를 추출하여 유상증자와 무상증자 도메인 모델로 변환합니다.
    """

    @classmethod
    def parse(cls, file_path: str, rcept_no: Optional[str] = None, parent_rcp_no: Optional[str] = None) -> Tuple[Optional[CapitalIncreaseDecision], Optional[BonusSharesDecision]]:
        """XML 파일을 파싱하여 유상증자와 무상증자 도메인 객체로 변환합니다.
        
        Args:
            file_path: XML 파일 경로
            rcept_no: 접수번호 (제공되지 않으면 파일명에서 추출 시도)
            parent_rcp_no: 상위 공시(이전 정정 공시) 접수번호
            
        Returns:
            (유상증자 결정 객체, 무상증자 결정 객체) 튜플. 파싱 실패 시 (None, None)
        """
        try:
            # recover 모드를 사용하여 Entity 에러 무시
            parser = etree.XMLParser(recover=True)
            tree = etree.parse(file_path, parser)
            root = tree.getroot()

            # 공통 정보 추출 (회사명, 보고서명, 정정여부, 파일명 기반 rcept_no)
            common_info = cls._extract_common_info(file_path, root)

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

            # rcept_no 처리 Priority: 
            # 1. Argument로 전달받은 값
            # 2. 파일명에서 추출한 값 (common_info)
            final_rcept_no = rcept_no if rcept_no else common_info["rcept_no_from_filename"]

            # 유상증자 객체 생성
            capital_increase = CapitalIncreaseDecision(
                source_filename=common_info["source_filename"],
                company_name=common_info["company_name"],
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
                payment_date=payment_date,
                report_name=common_info["report_name"],
                is_correction=common_info["is_correction"],
                rcept_no=final_rcept_no,
                parent_rcp_no=parent_rcp_no
            )

            # 무상증자 객체 생성
            bonus_shares = BonusSharesDecision(
                source_filename=common_info["source_filename"],
                company_name=common_info["company_name"],
                new_shares=stock_info,
                par_value=par_value,
                total_shares_before=total_shares_before,
                assign_per_share=assign_per_share,
                board_resolution_date=board_resolution_date,
                disclosure_date=disclosure_date,
                record_date=record_date,
                listing_date=listing_date,
                report_name=common_info["report_name"],
                is_correction=common_info["is_correction"],
                rcept_no=final_rcept_no,
                parent_rcp_no=parent_rcp_no
            )

            # 공시일(DIS_DT)이 없으면 rcept_no에서 유추
            if not capital_increase.disclosure_date:
                date_str = None
                if capital_increase.rcept_no and len(capital_increase.rcept_no) >= 8:
                    date_str = capital_increase.rcept_no[:8]
                
                if date_str:
                    try:
                        extracted_date = datetime.strptime(date_str, "%Y%m%d").date()
                        capital_increase = replace(capital_increase, disclosure_date=extracted_date)
                        bonus_shares = replace(bonus_shares, disclosure_date=extracted_date)
                    except ValueError:
                        pass

            return (capital_increase, bonus_shares)

        except Exception as e:
            # print(f"[Parser Error] {file_path}: {e}")
            return (None, None)

