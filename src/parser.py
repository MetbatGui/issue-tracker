import os
from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional
from lxml import etree

# --------------------------------------------------------------------------
# 1. 도메인 모델 (Domain Models)
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class StockInfo:
    """주식 수량 정보"""
    common: int
    preferred: int

    @property
    def total(self) -> int:
        return self.common + self.preferred

@dataclass(frozen=True)
class FundingPurpose:
    """자금 조달 목적"""
    facility: int      # 시설자금
    operating: int     # 운영자금
    acquisition: int   # 타법인증권 취득자금
    other: int         # 기타자금

@dataclass(frozen=True)
class CapitalIncreaseDecision:
    """유상증자 결정 데이터 엔티티"""
    source_filename: str
    company_name: str
    
    # 주식 관련
    new_shares: StockInfo          # 신주 발행 수
    par_value: int                 # 1주당 액면가
    total_shares_before: int       # 증자 전 발행주식 총수 (보통주 기준)
    issue_price: int               # 신주 발행가액 (예정)
    
    # 자금 용도
    funding: FundingPurpose
    
    # 방식 및 비율
    method: str                    # 증자 방식 (텍스트)
    assign_per_share: float        # 1주당 신주배정주식수
    
    # 날짜 정보
    board_resolution_date: Optional[date] # 이사회결의일
    disclosure_date: Optional[date]       # 공시일
    record_date: Optional[date]           # 신주배정기준일
    subscription_date: Optional[date]     # 청약예정일 (시작일)
    payment_date: Optional[date]          # 납입일

# --------------------------------------------------------------------------
# 2. 파서 클래스 (Parser Logic)
# --------------------------------------------------------------------------
class DartXmlParser:
    @staticmethod
    def _clean_int(text: str) -> int:
        """문자열을 정수로 변환 (쉼표 제거, '-' 처리)"""
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
        """문자열을 실수로 변환"""
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
    def _parse_date(node) -> Optional[date]:
        """XML 노드에서 날짜 추출 (속성값 우선)"""
        if node is None:
            return None
        
        # 1. AUNITVALUE 속성 (YYYYMMDD) 우선
        date_str = node.get("AUNITVALUE")
        
        # 2. 속성이 없으면 텍스트에서 숫자만 추출
        if not date_str:
            raw_text = "".join(node.itertext()).strip()
            date_str = "".join(filter(str.isdigit, raw_text))

        # 3. 날짜 변환
        if date_str and len(date_str) == 8:
            try:
                return datetime.strptime(date_str, "%Y%m%d").date()
            except ValueError:
                return None
        return None

    @staticmethod
    def _get_text(node) -> str:
        """안전한 텍스트 추출 (중첩 태그 포함)"""
        if node is None:
            return ""
        # 쉼표는 텍스트일 경우 제거하지 않음 (숫자 변환 시에만 제거)
        return "".join(node.itertext()).strip()

    @classmethod
    def parse(cls, file_path: str) -> Optional[CapitalIncreaseDecision]:
        """XML 파일을 파싱하여 도메인 객체 반환"""
        try:
            # recover 모드를 사용하여 Entity 에러 무시
            parser = etree.XMLParser(recover=True)
            tree = etree.parse(file_path, parser)
            root = tree.getroot()

            # --- 1. 기본 정보 ---
            crp_nm_node = root.find(".//TE[@ACODE='CRP_NM']")
            
            # --- 2. 주식 수량 (신주) ---
            cst_node = root.find(".//TE[@ACODE='CST_CNT']")
            pst_node = root.find(".//TE[@ACODE='PST_CNT']")
            stock_info = StockInfo(
                common=cls._clean_int(cls._get_text(cst_node)),
                preferred=cls._clean_int(cls._get_text(pst_node))
            )

            # --- 3. 금액 및 기존 주식 ---
            par_val_node = root.find(".//TE[@ACODE='FVAL']")
            bfr_stock_node = root.find(".//TE[@ACODE='BFR_CST_CNT']") # 증자전 보통주
            iss_price_node = root.find(".//TE[@ACODE='CST_ISS_VAL']") # 발행가액

            # --- 4. 자금 용도 ---
            fund_info = FundingPurpose(
                facility=cls._clean_int(cls._get_text(root.find(".//TE[@ACODE='FND_USE1']"))),
                operating=cls._clean_int(cls._get_text(root.find(".//TE[@ACODE='FND_USE2']"))),
                acquisition=cls._clean_int(cls._get_text(root.find(".//TE[@ACODE='ANC_ACQ_AMT']"))),
                other=cls._clean_int(cls._get_text(root.find(".//TE[@ACODE='FND_USE3']")))
            )

            # --- 5. 방식 및 비율 ---
            method_node = root.find(".//TU[@AUNIT='CI_MTH']") # 증자방식
            ratio_node = root.find(".//TE[@ACODE='NEW_ASN_CNT']") # 1주당 배정주식수

            # --- 6. 날짜 정보 ---
            drc_node = root.find(".//TU[@AUNIT='DRC_DT']")  # 이사회결의일
            dis_node = root.find(".//TU[@AUNIT='DIS_DT']")  # 공시일
            rec_node = root.find(".//TU[@AUNIT='ALL_BS_DT']") # 신주배정기준일
            pym_node = root.find(".//TU[@AUNIT='PYM_DT']")    # 납입일
            
            # 청약예정일: 구주주 청약 시작일(SH_BGN_DT)을 우선으로 함. 없으면 일반공모 등 확인 필요하나 여기선 구주주 우선
            sub_node = root.find(".//TU[@AUNIT='SH_BGN_DT']") 

            # 엔티티 생성 및 반환
            return CapitalIncreaseDecision(
                source_filename=os.path.basename(file_path),
                company_name=cls._get_text(crp_nm_node) or "Unknown",
                new_shares=stock_info,
                par_value=cls._clean_int(cls._get_text(par_val_node)),
                total_shares_before=cls._clean_int(cls._get_text(bfr_stock_node)),
                issue_price=cls._clean_int(cls._get_text(iss_price_node)),
                funding=fund_info,
                method=cls._get_text(method_node),
                assign_per_share=cls._clean_float(cls._get_text(ratio_node)),
                board_resolution_date=cls._parse_date(drc_node),
                disclosure_date=cls._parse_date(dis_node),
                record_date=cls._parse_date(rec_node),
                subscription_date=cls._parse_date(sub_node),
                payment_date=cls._parse_date(pym_node)
            )
        except Exception as e:
            print(f"[Parser Error] {file_path}: {e}")
            return None