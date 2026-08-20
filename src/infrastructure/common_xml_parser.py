
"""Common XML Parser Infrastructure

Shared parsing logic for DART XML reports (Capital Increase, Bonus Shares, etc.).
"""
import os
import re
from datetime import datetime
from typing import Optional, Any, Callable, Iterable, Tuple
from lxml import etree

__all__ = ["BaseXmlParser"]


class BaseXmlParser:
    """Base DART XML Parser containing common utility methods."""

    @staticmethod
    def _clean_int(text: str) -> int:
        """Convert text to integer."""
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
        """Convert text to float."""
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
        """Extract date from an XML node."""
        if node is None:
            return None

        # AUNITVALUE attribute (YYYYMMDD) priority
        date_str = node.get("AUNITVALUE")

        # If attribute missing, extract digits from text
        if not date_str:
            raw_text = "".join(node.itertext()).strip()
            date_str = "".join(filter(str.isdigit, raw_text))

        # Date conversion
        if date_str and len(date_str) == 8:
            try:
                return datetime.strptime(date_str, "%Y%m%d").date()
            except ValueError:
                return None
        return None

    @staticmethod
    def _get_text(node) -> str:
        """Safely extract text from an XML node."""
        if node is None:
            return ""
        return "".join(node.itertext()).strip()

    @staticmethod
    def _parse_korean_date(text: str) -> Optional[datetime.date]:
        """한글/구분자 혼용 날짜 문자열을 파싱합니다.

        지원 형식: 'YYYY년 MM월 DD일', 'YYYY.MM.DD', 'YYYY-MM-DD', 'YYYY/MM/DD', 'YYYYMMDD'

        Args:
            text: 날짜 문자열

        Returns:
            파싱된 date 객체. 실패 시 None
        """
        if not text or text == '-' or text.strip() == '':
            return None

        text = text.strip()

        try:
            match = re.search(r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일', text)
            if match:
                year, month, day = match.groups()
                return datetime(int(year), int(month), int(day)).date()

            match = re.search(r'(\d{4})\.(\d{1,2})\.(\d{1,2})', text)
            if match:
                year, month, day = match.groups()
                return datetime(int(year), int(month), int(day)).date()

            match = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', text)
            if match:
                year, month, day = match.groups()
                return datetime(int(year), int(month), int(day)).date()

            match = re.search(r'(\d{4})/(\d{1,2})/(\d{1,2})', text)
            if match:
                year, month, day = match.groups()
                return datetime(int(year), int(month), int(day)).date()

            match = re.search(r'^(\d{8})$', text)
            if match:
                val = match.group(1)
                return datetime(int(val[:4]), int(val[4:6]), int(val[6:])).date()

        except (ValueError, TypeError):
            pass
        return None

    @classmethod
    def _extract_fields(
        cls,
        root: Any,
        tag: str,
        attr: str,
        field_specs: Iterable[Tuple[str, str, Callable[[str], Any]]]
    ) -> dict:
        """`tag[@attr='code']` 형태의 노드들을 필드명 -> 값 딕셔너리로 일괄 추출합니다.

        예: `_extract_fields(root, "TE", "ACODE", [("bond_type", "PL_KND", str), ...])`
        DART 사채형 보고서(TE/ACODE, TU/AUNIT)처럼 같은 패턴이 반복되는 필드 추출에서
        if/else 나열 대신 매핑 테이블 + 루프로 처리하기 위한 헬퍼입니다.

        Args:
            root: XML 루트 엘리먼트
            tag: 노드 태그명 (예: "TE", "TU")
            attr: 코드가 담긴 속성명 (예: "ACODE", "AUNIT")
            field_specs: (필드명, 코드값, 텍스트 -> 값 변환 함수) 튜플 목록

        Returns:
            필드명 -> 변환된 값 (노드가 없으면 None) 딕셔너리
        """
        result = {}
        for field_name, code, caster in field_specs:
            node = root.find(f".//{tag}[@{attr}='{code}']")
            result[field_name] = caster(cls._get_text(node)) if node is not None else None
        return result

    @classmethod
    def _extract_common_info(cls, file_path: str, root: Any) -> dict:
        """Extract common information (Company Name, Report Name, Correction Status).
        
        Args:
            file_path: Path to the XML file.
            root: Root element of the XML tree.
            
        Returns:
            Dictionary containing extracted common fields.
        """
        # 1. Company Name Parsing (Filename Priority: "Company_rcpNo.xml")
        base_name = os.path.basename(file_path)
        if "_" in base_name:
            company_name = base_name.split("_")[0]
        else:
            # Fallback
            company_name_node = root.find(".//TE[@ACODE='CRP_NM']")
            company_name = cls._get_text(company_name_node)
            if not company_name:
                header_name_node = root.find(".//COMPANY-NAME")
                company_name = cls._get_text(header_name_node)
        
        # 2. Report Name Parsing
        doc_name_node = root.find(".//DOCUMENT-NAME")
        report_name = cls._get_text(doc_name_node)

        # 3. Correction Status Check
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
        
        # 4. Rcept No Extraction (from filename if available)
        # Assumes format: Company_YYYYMMDDnnnnnn.xml
        rcept_no = ""
        match_rcp = re.search(r'_(\d{14})\.xml$', base_name)
        if match_rcp:
            rcept_no = match_rcp.group(1)
            
        return {
            "source_filename": base_name,
            "company_name": company_name,
            "report_name": report_name,
            "is_correction": is_correction,
            "rcept_no_from_filename": rcept_no
        }
