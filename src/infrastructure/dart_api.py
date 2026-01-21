"""DART Open API 클라이언트

Open DART API를 호출하여 공시 데이터를 수집합니다.
"""
import os
import re
import time
import zipfile
import io
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

import requests
from dotenv import load_dotenv


__all__ = ["DartApiClient"]


class DartApiClient:
    """DART Open API 클라이언트
    
    공시검색 API와 원본파일 다운로드 기능을 제공합니다.
    """

    def __init__(self, api_key: Optional[str] = None, save_directory: str = "data/유상증자"):
        """클라이언트를 초기화합니다.
        
        Args:
            api_key: DART API 키. None이면 .env에서 로드
            save_directory: XML 파일을 저장할 디렉토리
        """
        if api_key is None:
            load_dotenv()
            api_key = os.getenv("DART_API_KEY")
            if not api_key:
                raise ValueError("DART_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")

        self.api_key = api_key
        self.save_path = Path(save_directory)
        self.xml_save_path = self.save_path / "xml"

        # 디렉토리 생성
        self.xml_save_path.mkdir(parents=True, exist_ok=True)

    def fetch_disclosure_list(
        self,
        bgn_de: str,
        end_de: str,
        page_no: int = 1,
        page_count: int = 100
    ) -> Optional[Dict[str, Any]]:
        """공시검색 API를 호출합니다.
        
        Args:
            bgn_de: 시작일자 (YYYYMMDD)
            end_de: 종료일자 (YYYYMMDD)
            page_no: 페이지 번호
            page_count: 페이지당 건수
            
        Returns:
            API 응답 JSON 딕셔너리. 실패 시 None
        """
        url = "https://opendart.fss.or.kr/api/list.json"
        params = {
            "crtfc_key": self.api_key,
            "bgn_de": bgn_de,
            "end_de": end_de,
            "pblntf_ty": "B",  # 주요사항보고서
            "page_no": page_no,
            "page_count": page_count,
            "last_reprt_at": "Y"
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            time.sleep(0.1)  # API 부하 조절
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"[Error] 목록 검색 실패: {e}")
            return None

    def download_document_xml(self, rcept_no: str, corp_name: str) -> Optional[Path]:
        """상세 원본 파일(document.xml)을 다운로드합니다.
        
        Args:
            rcept_no: 접수번호
            corp_name: 회사명
            
        Returns:
            다운로드된 파일 경로. 실패 시 None
        """
        url = "https://opendart.fss.or.kr/api/document.xml"
        params = {
            "crtfc_key": self.api_key,
            "rcept_no": rcept_no
        }

        # 파일명 안전하게 생성
        safe_corp_name = re.sub(r'[\\/*?:"<>|]', "", corp_name)
        filename = f"{safe_corp_name}_{rcept_no}.xml"
        file_path = self.xml_save_path / filename

        # 이미 다운로드된 경우 건너뛰기
        if file_path.exists():
            return file_path

        try:
            response = requests.get(url, params=params, timeout=60)
            response.raise_for_status()

            # ZIP 파일 압축 해제
            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                xml_filename_in_zip = z.namelist()[0]
                xml_data = z.read(xml_filename_in_zip)

                with open(file_path, "wb") as f:
                    f.write(xml_data)

            time.sleep(0.2)  # API 과부하 방지
            return file_path

        except Exception as e:
            print(f"  └ [Error] XML 다운로드 실패 ({corp_name}): {e}")
            return None

    @staticmethod
    def filter_capital_increase_reports(data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """유상증자 보고서를 필터링합니다 (유무상증자 제외).
        
        수집 대상:
        - 유상증자결정
        - 유상증자결정(자율공시)(종속회사의주요경영사항)
        - 유상증자결정(종속회사의주요경영사항)
        - 주요사항보고서(유상증자결정)
        - 주요사항보고서(유상증자결정)(기재정정)
        
        Args:
            data_list: API 응답의 공시 목록
            
        Returns:
            필터링된 공시 목록
        """
        if not data_list:
            return []

        # "유상증자"를 포함하지만 "유무상"은 제외
        return [
            item for item in data_list
            if "유상증자" in item.get("report_nm", "") and "유무상" not in item.get("report_nm", "")
        ]

    @staticmethod
    def filter_bonus_shares_reports(data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """무상증자 보고서를 필터링합니다 (유무상증자 제외).
        
        수집 대상:
        - 무상증자결정
        - 무상증자결정(자율공시)(종속회사의주요경영사항)
        - 무상증자결정(종속회사의주요경영사항)
        - 주요사항보고서(무상증자결정)
        - 주요사항보고서(무상증자결정)(기재정정)
        
        Args:
            data_list: API 응답의 공시 목록
            
        Returns:
            필터링된 공시 목록
        """
        if not data_list:
            return []

        # "무상증자"를 포함하지만 "유무상"은 제외
        return [
            item for item in data_list
            if "무상증자" in item.get("report_nm", "") and "유무상" not in item.get("report_nm", "")
        ]
    
    @staticmethod
    def filter_dual_increase_reports(data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """유무상증자 보고서를 필터링합니다.
        
        수집 대상:
        - 유무상증자결정
        - 유무상증자결정(자율공시)(종속회사의주요경영사항)
        - 유무상증자결정(종속회사의주요경영사항)
        - 주요사항보고서(유무상증자결정)
        - 주요사항보고서(유무상증자결정)(기재정정)
        
        Args:
            data_list: API 응답의 공시 목록
            
        Returns:
            필터링된 공시 목록
        """
        if not data_list:
            return []

        return [
            item for item in data_list
            if "유무상증자" in item.get("report_nm", "")
        ]

    def _collect_reports_with_filter(
        self,
        start_date: str,
        end_date: Optional[str],
        interval_days: int,
        filter_func,
        report_type_name: str
    ) -> List[Dict[str, Any]]:
        """필터 함수를 사용하여 보고서를 수집하는 공통 로직
        
        Args:
            start_date: 시작일자 (YYYYMMDD)
            end_date: 종료일자 (YYYYMMDD). None이면 오늘
            interval_days: API 호출 간격 (일)
            filter_func: 필터링 함수
            report_type_name: 보고서 유형명 (로그용)
            
        Returns:
            수집된 공시 목록 (xml_path 추가됨)
        """
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")

        curr_start = datetime.strptime(start_date, "%Y%m%d")
        final_end = datetime.strptime(end_date, "%Y%m%d")
        all_filtered_reports = []
        
        print(f"[수집 시작] {start_date} ~ {end_date} ({report_type_name})")
        print(f"[XML 저장] {self.xml_save_path}")

        while curr_start <= final_end:
            curr_end = curr_start + timedelta(days=interval_days)
            if curr_end > final_end:
                curr_end = final_end

            bgn_de = curr_start.strftime("%Y%m%d")
            end_de = curr_end.strftime("%Y%m%d")

            print(f"\n[기간 검색] {bgn_de} ~ {end_de}")

            page = 1
            while True:
                result = self.fetch_disclosure_list(bgn_de, end_de, page_no=page)

                if not result:
                    break
                if result.get('status') != '000':
                    if result.get('status') != '013':  # 데이터 없음
                        print(f"  [경고] API 메시지: {result.get('message')}")
                    break

                list_data = result.get('list', [])
                if not list_data:
                    break

                # 필터링 및 XML 다운로드
                # KOSPI(Y), KOSDAQ(K) 만 필터링
                list_data = [
                    item for item in list_data 
                    if item.get('corp_cls') in ['Y', 'K']
                ]

                filtered = filter_func(list_data)
                for item in filtered:
                    xml_path = self.download_document_xml(
                        item['rcept_no'],
                        item['corp_name']
                    )
                    if xml_path:
                        item['xml_path'] = str(xml_path)

                all_filtered_reports.extend(filtered)

                print(f"  - p.{page} 완료: {len(filtered)}건 추가 (누적 {len(all_filtered_reports)}건)", end="\r")

                total_page = int(result.get('total_page', 1))
                if page >= total_page:
                    break
                page += 1

            curr_start = curr_end + timedelta(days=1)

        print("\n\n[완료] 전체 수집 및 XML 다운로드 완료.")
        return all_filtered_reports

    def collect_reports(
        self,
        start_date: str,
        end_date: Optional[str] = None,
        interval_days: int = 90,
        report_type: str = "capital_increase"
    ) -> List[Dict[str, Any]]:
        """기간 내 공시를 수집하고 XML을 다운로드합니다 (하위 호환용).
        
        Args:
            start_date: 시작일자 (YYYYMMDD)
            end_date: 종료일자 (YYYYMMDD). None이면 오늘
            interval_days: API 호출 간격 (일)
            report_type: 보고서 유형 ("capital_increase", "bonus_shares", "dual_increase")
            
        Returns:
            수집된 공시 목록 (xml_path 추가됨)
        """
        # 필터 함수 및 이름 선택
        if report_type == "bonus_shares":
            filter_func = self.filter_bonus_shares_reports
            report_type_name = "무상증자"
        elif report_type == "dual_increase":
            filter_func = self.filter_dual_increase_reports
            report_type_name = "유무상증자"
        else:  # capital_increase (기본값)
            filter_func = self.filter_capital_increase_reports
            report_type_name = "유상증자"
        
        return self._collect_reports_with_filter(
            start_date=start_date,
            end_date=end_date,
            interval_days=interval_days,
            filter_func=filter_func,
            report_type_name=report_type_name
        )
    
    def collect_capital_increase_reports(
        self,
        start_date: str,
        end_date: Optional[str] = None,
        interval_days: int = 90
    ) -> List[Dict[str, Any]]:
        """유상증자 보고서만 수집합니다.
        
        수집 대상:
        - 주요사항보고서(유상증자결정)
        
        Args:
            start_date: 시작일자 (YYYYMMDD)
            end_date: 종료일자 (YYYYMMDD). None이면 오늘
            interval_days: API 호출 간격 (일)
            
        Returns:
            유상증자 공시 목록
        """
        return self._collect_reports_with_filter(
            start_date=start_date,
            end_date=end_date,
            interval_days=interval_days,
            filter_func=self.filter_capital_increase_reports,
            report_type_name="유상증자"
        )
    
    def collect_bonus_shares_reports(
        self,
        start_date: str,
        end_date: Optional[str] = None,
        interval_days: int = 90
    ) -> List[Dict[str, Any]]:
        """무상증자 보고서만 수집합니다 (유무상증자 제외).
        
        수집 대상:
        - 무상증자결정
        - 무상증자결정(자율공시)(종속회사의주요경영사항)
        - 무상증자결정(종속회사의주요경영사항)
        - 주요사항보고서(무상증자결정)
        - 주요사항보고서(무상증자결정)(기재정정)
        
        주의: 유무상증자는 제외됩니다.
        
        Args:
            start_date: 시작일자 (YYYYMMDD)
            end_date: 종료일자 (YYYYMMDD). None이면 오늘
            interval_days: API 호출 간격 (일)
            
        Returns:
            무상증자 공시 목록
        """
        return self._collect_reports_with_filter(
            start_date=start_date,
            end_date=end_date,
            interval_days=interval_days,
            filter_func=self.filter_bonus_shares_reports,
            report_type_name="무상증자"
        )
    
    def collect_dual_increase_reports(
        self,
        start_date: str,
        end_date: Optional[str] = None,
        interval_days: int = 90
    ) -> List[Dict[str, Any]]:
        """유무상증자 보고서만 수집합니다.
        
        수집 대상:
        - 유무상증자결정
        - 유무상증자결정(자율공시)(종속회사의주요경영사항)
        - 유무상증자결정(종속회사의주요경영사항)
        - 주요사항보고서(유무상증자결정)
        - 주요사항보고서(유무상증자결정)(기재정정)
        
        Args:
            start_date: 시작일자 (YYYYMMDD)
            end_date: 종료일자 (YYYYMMDD). None이면 오늘
            interval_days: API 호출 간격 (일)
            
        Returns:
            유무상증자 공시 목록
        """
        return self._collect_reports_with_filter(
            start_date=start_date,
            end_date=end_date,
            interval_days=interval_days,
            filter_func=self.filter_dual_increase_reports,
            report_type_name="유무상증자"
        )
