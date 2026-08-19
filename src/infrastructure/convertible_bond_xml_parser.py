"""전환사채 XML 파싱 인프라스트럭처

DART XML 파일을 파싱하여 전환사채 도메인 모델로 변환합니다.
"""
import os
import re
from datetime import datetime
from typing import Optional
from lxml import etree
from dataclasses import replace

from ..domain import ConvertibleBondDecision
from .common_xml_parser import BaseXmlParser


__all__ = ["ConvertibleBondXmlParser"]


class ConvertibleBondXmlParser(BaseXmlParser):
    """전환사채 DART XML 파서
    
    XML 파일에서 데이터를 추출하여 전환사채 도메인 모델로 변환합니다.
    """

    @classmethod
    def parse(cls, file_path: str, rcept_no: Optional[str] = None, parent_rcp_no: Optional[str] = None) -> Optional[ConvertibleBondDecision]:
        """XML 파일을 파싱하여 도메인 객체로 변환합니다.
        
        Args:
            file_path: XML 파일 경로
            rcept_no: 접수번호 (제공되지 않으면 파일명에서 추출 시도)
            parent_rcp_no: 상위 공시(이전 정정 공시) 접수번호
            
        Returns:
            파싱된 전환사채 결정 객체. 파싱 실패 시 None
        """
        try:
            # recover 모드를 사용하여 Entity 에러 무시
            parser = etree.XMLParser(recover=True)
            tree = etree.parse(file_path, parser)
            root = tree.getroot()

            # 공통 정보 추출 (회사명, 보고서명, 정정여부, 파일명 기반 rcept_no)
            common_info = cls._extract_common_info(file_path, root)

            # 1. 회차
            seq_node = root.find(".//TE[@ACODE='SEQ_NO']")
            sequence_number = cls._get_text(seq_node) if seq_node is not None else None
            
            # 2. 종류
            kind_node = root.find(".//TE[@ACODE='PL_KND']")
            bond_type = cls._get_text(kind_node) if kind_node is not None else None
            
            # 3. 사채의 권면(전자등록)총액
            dnm_node = root.find(".//TE[@ACODE='DNM_SUM']")
            face_value_total = cls._clean_int(cls._get_text(dnm_node)) if dnm_node is not None else None
            
            # 4. 자금조달 목적 (4개 필드로 분리)
            # 시설자금
            facility_node = root.find(".//TE[@ACODE='FND_USE1']")
            facility_fund = cls._clean_int(cls._get_text(facility_node)) if facility_node is not None else None
            
            # 운영자금
            operating_node = root.find(".//TE[@ACODE='FND_USE2']")
            operating_fund = cls._clean_int(cls._get_text(operating_node)) if operating_node is not None else None
            
            # 영업양수자금
            business_acq_node = root.find(".//TE[@ACODE='FND_USE_SQ']")
            business_acquisition_fund = cls._clean_int(cls._get_text(business_acq_node)) if business_acq_node is not None else None
            
            # 타법인증권 취득자금
            acquisition_node = root.find(".//TE[@ACODE='ANC_ACQ_PRC']")
            acquisition_fund = cls._clean_int(cls._get_text(acquisition_node)) if acquisition_node is not None else None
            
            # 채무상환자금
            debt_node = root.find(".//TE[@ACODE='FND_USE_RD']")
            debt_repayment_fund = cls._clean_int(cls._get_text(debt_node)) if debt_node is not None else None
            
            # 기타자금
            other_node = root.find(".//TE[@ACODE='FND_USE3']")
            other_fund = cls._clean_int(cls._get_text(other_node)) if other_node is not None else None
            
            # 5. 사채의 만기일
            exp_node = root.find(".//TU[@AUNIT='EXP_DT']")
            maturity_date = cls._parse_korean_date(cls._get_text(exp_node)) if exp_node is not None else None
            
            # 6. 사채발행방법
            method_node = root.find(".//TU[@AUNIT='ISSU_MTH']")
            issue_method = cls._get_text(method_node) if method_node is not None else None
            
            # 7. 전환비율
            exe_rt_node = root.find(".//TE[@ACODE='EXE_RT']")
            conversion_ratio = cls._clean_float(cls._get_text(exe_rt_node)) if exe_rt_node is not None else None
            
            # 8. 전환가액
            exe_prc_node = root.find(".//TE[@ACODE='EXE_PRC']")
            conversion_price = cls._clean_int(cls._get_text(exe_prc_node)) if exe_prc_node is not None else None
            
            # 9. 전환에 따라 발행할 주식수
            stk_cnt_node = root.find(".//TE[@ACODE='STK_CNT']")
            conversion_shares = cls._clean_int(cls._get_text(stk_cnt_node)) if stk_cnt_node is not None else None
            
            # 10. 주식총수 대비 비율
            stk_rt_node = root.find(".//TE[@ACODE='STK_RT']")
            shares_ratio = cls._clean_float(cls._get_text(stk_rt_node)) if stk_rt_node is not None else None
            
            # 11. 전환청구기간시작일
            sb_bgn_node = root.find(".//TU[@AUNIT='SB_BGN_DT']")
            conversion_start_date = cls._parse_korean_date(cls._get_text(sb_bgn_node)) if sb_bgn_node is not None else None
            
            # 12. 전환청구기간종료일
            sb_end_node = root.find(".//TU[@AUNIT='SB_END_DT']")
            conversion_end_date = cls._parse_korean_date(cls._get_text(sb_end_node)) if sb_end_node is not None else None
            
            # 13. 청약일
            sbsc_node = root.find(".//TU[@AUNIT='SBSC_DT']")
            subscription_date = cls._parse_korean_date(cls._get_text(sbsc_node)) if sbsc_node is not None else None
            
            # 14. 납입일
            pym_node = root.find(".//TU[@AUNIT='PYM_DT']")
            payment_date = cls._parse_korean_date(cls._get_text(pym_node)) if pym_node is not None else None
            
            # 15. 이사회결의일
            drc_node = root.find(".//TU[@AUNIT='DRC_DT']")
            board_resolution_date = cls._parse_korean_date(cls._get_text(drc_node)) if drc_node is not None else None

            # 16. 자금조달 목적 (FundingPurpose 객체 생성)
            from ..domain.value_objects import FundingPurpose
            funding = FundingPurpose(
                facility=facility_fund or 0,
                operating=operating_fund or 0,
                acquisition=acquisition_fund or 0,
                debt_repayment=debt_repayment_fund or 0,
                business_acquisition=business_acquisition_fund or 0,
                other=other_fund or 0
            )

            # rcept_no 처리 Priority: 
            # 1. Argument로 전달받은 값
            # 2. 파일명에서 추출한 값 (common_info)
            final_rcept_no = rcept_no if rcept_no else common_info["rcept_no_from_filename"]

            decision = ConvertibleBondDecision(
                source_filename=common_info["source_filename"],
                company_name=common_info["company_name"],
                sequence_number=sequence_number,
                bond_type=bond_type,
                face_value_total=face_value_total,
                funding=funding,
                interest_rate=None,  # XML 파싱 로직에 이율 추출이 없음
                maturity_date=maturity_date,
                issue_method=issue_method,
                conversion_ratio=conversion_ratio,
                conversion_price=conversion_price,
                conversion_shares=conversion_shares,
                shares_ratio=shares_ratio,
                conversion_start_date=conversion_start_date,
                conversion_end_date=conversion_end_date,
                subscription_date=subscription_date,
                payment_date=payment_date,
                board_resolution_date=board_resolution_date,
                report_name=common_info["report_name"],
                is_correction=common_info["is_correction"],
                rcept_no=final_rcept_no,
                parent_rcp_no=parent_rcp_no
            )

            # 후처리: 공시일(disclosure_date)이 없으면 rcept_no에서 유추
            if not decision.disclosure_date:
                date_str = None
                # rcept_no의 앞 8자리
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
            # print(f"[Parser Error] {file_path}: {e}") # 로그 과다 방지
            return None

    @staticmethod
    def _parse_korean_date(text: str) -> Optional[datetime.date]:
        """한글 날짜 파싱: '2029년 01월 07일' -> date 객체
        
        Args:
            text: 한글 날짜 문자열
            
        Returns:
            파싱된 date 객체. 실패 시 None
        """
        if not text or text == '-' or text.strip() == '':
            return None
        
        text = text.strip()
        
        try:
            # 1. YYYY년 MM월 DD일
            match = re.search(r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일', text)
            if match:
                year, month, day = match.groups()
                return datetime(int(year), int(month), int(day)).date()
                
            # 2. YYYY.MM.DD
            match = re.search(r'(\d{4})\.(\d{1,2})\.(\d{1,2})', text)
            if match:
                year, month, day = match.groups()
                return datetime(int(year), int(month), int(day)).date()
                
            # 3. YYYY-MM-DD
            match = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', text)
            if match:
                year, month, day = match.groups()
                return datetime(int(year), int(month), int(day)).date()
                
            # 4. YYYY/MM/DD
            match = re.search(r'(\d{4})/(\d{1,2})/(\d{1,2})', text)
            if match:
                year, month, day = match.groups()
                return datetime(int(year), int(month), int(day)).date()

            # 5. YYYYMMDD (8자리 숫자)
            match = re.search(r'^(\d{8})$', text)
            if match:
                val = match.group(1)
                return datetime(int(val[:4]), int(val[4:6]), int(val[6:])).date()

        except:
            pass
        return None
