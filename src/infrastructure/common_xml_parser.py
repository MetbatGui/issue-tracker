
"""Common XML Parser Infrastructure

Shared parsing logic for DART XML reports (Capital Increase, Bonus Shares, etc.).
"""
import os
import re
from datetime import datetime
from typing import Optional, Any
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
