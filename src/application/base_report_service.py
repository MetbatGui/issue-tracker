
"""Base Report Service

Common logic for DART report processing, including history tracking, file management, and Google Drive upload.
"""
import os
import glob
from pathlib import Path
from typing import List, Optional, Tuple, Any, Callable
from abc import ABC, abstractmethod

from ..infrastructure import (
    DartApiClient,
    FileEncodingConverter,
    GoogleDriveAdapter,
    DartHistoryScraper
)
from ..logger import get_logger


class BaseReportService(ABC):
    """Base class for DART report services."""

    def __init__(
        self,
        data_directory: str,
        api_key: Optional[str] = None,
        enable_google_drive: bool = True,
        google_folder_id_env_var: Optional[str] = None,
        excel_filename: str = "output.xlsx"
    ):
        """Initialize the base service.
        
        Args:
            data_directory: Directory to save data.
            api_key: DART API Key.
            enable_google_drive: Whether to enable Google Drive upload.
            google_folder_id_env_var: Environment variable name for Google Drive Folder ID.
            excel_filename: Name of the output Excel file.
        """
        self.data_directory = Path(data_directory)
        self.xml_directory = self.data_directory / "xml"
        self.excel_path = self.data_directory / excel_filename
        self.enable_google_drive = enable_google_drive
        
        self.logger = get_logger(self.__class__.__name__)
        
        # Initialize components
        self.api_client = DartApiClient(api_key=api_key, save_directory=str(self.data_directory))
        self.history_scraper = DartHistoryScraper()
        self.file_converter = FileEncodingConverter()
        
        # Relation Map Path
        self.relation_map_path = self.data_directory / "relation_map.json"
        
        # Initialize Google Drive
        self.google_drive = None
        self.google_drive_folder_id = None
        if enable_google_drive:
            try:
                from dotenv import load_dotenv
                load_dotenv()
                if google_folder_id_env_var:
                    self.google_drive_folder_id = os.getenv(google_folder_id_env_var)
                
                if self.google_drive_folder_id:
                    self.google_drive = GoogleDriveAdapter()
                else:
                    self.logger.warning(f"{google_folder_id_env_var} environment variable not set.")
            except Exception as e:
                self.logger.error(f"Google Drive initialization failed: {e}")
                self.google_drive = None

    def get_relation_map(self) -> dict:
        """관게 맵을 로드합니다. (JSON 우선, 없으면 Excel에서 마이그레이션)"""
        # 1. JSON 로드 시도
        relation_map = self._load_relation_map_from_json()
        
        
        # 2. JSON이 없거나 비어있으면 Excel에서 로드 (마이그레이션)
        if not relation_map:
            self.logger.info("relation_map.json 없음. Excel에서 관계 맵 추출 시도...")
            relation_map = self._load_map_from_excel()
            
            # 마이그레이션 결과 저장
            if relation_map:
                self.logger.info(f"Excel에서 {len(relation_map)}건 관계 발견 및 JSON 저장")
                self._save_relation_map_to_json(relation_map)
                
        return relation_map

    def _load_relation_map_from_json(self) -> dict:
        """JSON 파일에서 관계 맵을 로드합니다."""
        import json
        if not self.relation_map_path.exists():
            return {}
            
        try:
            with open(self.relation_map_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.warning(f"관계 맵 JSON 수정 실패: {e}")
            return {}

    def _save_relation_map_to_json(self, relation_map: dict) -> None:
        """관계 맵을 JSON 파일로 저장합니다."""
        import json
        try:
            with open(self.relation_map_path, 'w', encoding='utf-8') as f:
                json.dump(relation_map, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"관계 맵 JSON 저장 실패: {e}")

    def download_reports_with_history(
        self,
        collect_method: Callable[[str, Optional[str]], List[dict]],
        start_date: str,
        end_date: Optional[str] = None
    ) -> Tuple[List[str], dict]:
        """Download reports and track correction history.
        
        Args:
            collect_method: Method to call for initial report collection (e.g., api_client.collect_capital_increase_reports).
            start_date: Start date (YYYYMMDD).
            end_date: End date (YYYYMMDD).
            
        Returns:
            Tuple of (downloaded_file_paths, relation_map).
        """
        import json
        
        self.logger.info("=" * 50)
        self.logger.info("📥 Report Download & History Tracking")
        self.logger.info("=" * 50)
        
        # 1. Collect initial reports
        reports = collect_method(start_date, end_date)
        
        # Extract downloaded paths
        downloaded_files = [report['xml_path'] for report in reports if 'xml_path' in report]
        
        # 2. History Tracking (Hybrid Approach)
        self.logger.info("🔍 Scanning for correction history...")
        
        # Load existing map (JSON preferred)
        relation_map = self.get_relation_map()
        initial_map_size = len(relation_map)
        
        for i, report in enumerate(reports, 1):
            if i % 10 == 0:
                 self.logger.debug(f"  - Processing report {i}/{len(reports)}...")

            # Check for correction indicators in report name
            if "기재정정" in report.get("report_nm", ""):
                curr_rcp = report.get("rcept_no")
                if not curr_rcp:
                    continue
                    
                # Scrape history
                history_ids = self.history_scraper.get_history_rcp_list(curr_rcp)
                
                # Update map (adjacent pairs)
                for i in range(1, len(history_ids)):
                    parent = history_ids[i-1]
                    child = history_ids[i]
                    relation_map[child] = parent
                
                # Download missing XMLs
                for hist_rcp in history_ids:
                    # Check if we already have it is hard without exact filename, 
                    # but download_document_xml checks efficiently.
                    xml_path = self.api_client.download_document_xml(hist_rcp, report.get("corp_name", "Unknown"))
                    if xml_path:
                        path_str = str(xml_path)
                        if path_str not in downloaded_files:
                            downloaded_files.append(path_str)
                            
        # Save updated map if changed
        if len(relation_map) > initial_map_size:
            self.logger.info(f"💾 관계 맵 업데이트: {initial_map_size} -> {len(relation_map)}건")
            self._save_relation_map_to_json(relation_map)
                            
        self.logger.info(f"Total {len(reports)} reports (Total files including history: {len(downloaded_files)}) processed.")
        return downloaded_files, relation_map

    def _convert_downloaded_files(self, file_paths: List[str]) -> dict:
        """Convert encoding of downloaded files to UTF-8."""
        if not file_paths:
            return {"converted": 0, "already_utf8": 0, "errors": 0}
        
        self.logger.info("=" * 50)
        self.logger.info(f"🔄 Converting {len(file_paths)} files to UTF-8")
        self.logger.info("=" * 50)
        
        converted = 0
        already_utf8 = 0
        errors = 0
        
        for file_path_str in file_paths:
            file_path = Path(file_path_str)
            result = self.file_converter.detect_and_read(file_path)
            
            if result and result[0].lower() != 'utf-8':
                if self.file_converter.convert_to_utf8(file_path):
                    converted += 1
                else:
                    errors += 1
            elif result and result[0].lower() == 'utf-8':
                already_utf8 += 1
            else:
                errors += 1
        
        self.logger.info(f"Converted: {converted} | Already UTF-8: {already_utf8} | Errors: {errors}")
        return {"converted": converted, "already_utf8": already_utf8, "errors": errors}

    def run_pipeline(
        self,
        collect_method: Callable[[str, Optional[str]], List[dict]],
        start_date: str,
        end_date: Optional[str] = None
    ) -> None:
        """공통 실행 파이프라인
        
        1. 다운로드 (이력 추적 포함)
        2. 인코딩 변환
        3. 파싱 및 엑셀 저장
        4. 구글 드라이브 업로드
        """
        # 1. 다운로드
        downloaded_files, relation_map = self.download_reports_with_history(
            collect_method, start_date, end_date
        )
        
        # 2. 인코딩 변환
        self._convert_downloaded_files(downloaded_files)
        
        # 3. 파싱 및 저장 (relation_map을 인자로 전달하여 최신 관계 정보 반영)
        self.parse_and_export_to_excel(relation_map=relation_map)
        
        # 4. 구글 드라이브 업로드
        self._upload_to_google_drive()

    def _load_map_from_excel(self) -> dict:
        """Load (rcept_no -> parent_rcp_no) map from existing Excel file."""
        import pandas as pd
        relation_map = {}
        
        if not self.excel_path.exists():
            return relation_map
            
        try:
            # Load all sheets
            existing_data = {}
            try:
                # 1. 시도: header=1 (기존 서비스 표준)
                excel_file = pd.ExcelFile(self.excel_path)
                
                for sheet_name in excel_file.sheet_names:
                    # header=1 시도
                    df = pd.read_excel(excel_file, sheet_name=sheet_name, header=1)
                    
                    # 컬럼 확인 ('접수번호'가 없으면 header=0일 수 있음)
                    if '접수번호' not in df.columns or '상위접수번호' not in df.columns:
                        try:
                             # header=0 시도
                             df_alt = pd.read_excel(excel_file, sheet_name=sheet_name, header=0)
                             if '접수번호' in df_alt.columns and '상위접수번호' in df_alt.columns:
                                 df = df_alt
                        except:
                             pass
                             
                    # 처리할 데이터프레임이 존재하는지 확인 (기존 로직과 통합)
                    existing_data[sheet_name] = df

            except Exception as load_err:
                 print(f"⚠️ Failed to open Excel file: {load_err}")
                 return {}

            for sheet_name, df in existing_data.items():
                if '접수번호' in df.columns and '상위접수번호' in df.columns:
                    valid_rows = df[df['상위접수번호'].notna() & (df['상위접수번호'] != "")]
                    for _, row in valid_rows.iterrows():
                        child = str(row['접수번호']).strip()
                        parent = str(row['상위접수번호']).strip()
                        
                        # Handle float conversion artifacts
                        if child.endswith('.0'):
                            child = child[:-2]
                        if parent.endswith('.0'):
                            parent = parent[:-2]
                            
                        if child and parent:
                            relation_map[child] = parent
        except Exception as e:
            print(f"⚠️ Error loading relation map from Excel: {e}")
            
        return relation_map

    def _upload_to_google_drive(self) -> None:
        """Upload Excel file to Google Drive."""
        if not self.google_drive or not self.google_drive_folder_id:
            return
        
        if not self.excel_path.exists():
            self.logger.warning("No Excel file to upload.")
            return
        
        try:
            self.logger.info("=" * 50)
            self.logger.info("☁️ Uploading to Google Drive")
            self.logger.info("=" * 50)
            
            file_id = self.google_drive.upload_file(
                self.excel_path,
                self.google_drive_folder_id,
                self.excel_path.name
            )
            self.logger.info(f"Upload Complete (File ID: {file_id})")
        except Exception as e:
            self.logger.error(f"Upload Failed: {e}")

    @abstractmethod
    def parse_and_export_to_excel(self, relation_map: dict = None) -> int:
        """Abstract method to be implemented by subclasses.
        
        Args:
            relation_map: Map of rcept_no -> parent_rcp_no (optional)
        """
        pass

    def _extract_rcept_no(self, file_path: str) -> Optional[str]:
        """파일 경로에서 접수번호를 추출합니다."""
        import re
        import os
        match = re.search(r'_(\d{14})\.xml$', os.path.basename(file_path))
        return match.group(1) if match else None

    def _resolve_original_dates(self, decisions: List[Any]) -> None:
        """정정 공시의 최초 원본 공시일을 찾아 설정합니다."""
        if not decisions:
            return

        # 1. 접수번호 맵핑 및 Dictionary 변환
        decision_map = {d.rcept_no: d for d in decisions if hasattr(d, 'rcept_no') and d.rcept_no}
        
        # 2. 각 결정에 대해 원본 찾기
        import dataclasses
        
        for i, decision in enumerate(decisions):
            # 이미 설정된 경우 패스 (만약 있다면)
            if hasattr(decision, 'original_disclosure_date') and decision.original_disclosure_date:
                continue
            
            # parent_rcp_no나 disclosure_date 속성이 없으면 패스
            if not hasattr(decision, 'parent_rcp_no') or not hasattr(decision, 'disclosure_date'):
                continue
                
            current = decision
            visited = set()
            root_date = decision.disclosure_date
            
            # 상위로 탐색
            while current.parent_rcp_no and current.parent_rcp_no in decision_map:
                parent = decision_map[current.parent_rcp_no]
                
                # 순환 참조 방지
                if parent.rcept_no in visited:
                    break
                visited.add(parent.rcept_no)
                
                current = parent
                if hasattr(current, 'disclosure_date') and current.disclosure_date:
                    root_date = current.disclosure_date
            
            # 찾은 root_date를 설정 (불변 객체이므로 교체)
            if root_date:
                decisions[i] = dataclasses.replace(decision, original_disclosure_date=root_date)
