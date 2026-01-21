
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
        
        # Initialize components
        self.api_client = DartApiClient(api_key=api_key, save_directory=str(self.data_directory))
        self.history_scraper = DartHistoryScraper()
        self.file_converter = FileEncodingConverter()
        
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
                    print(f"⚠️ {google_folder_id_env_var} environment variable not set.")
            except Exception as e:
                print(f"⚠️ Google Drive initialization failed: {e}")
                self.google_drive = None

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
        
        print("=" * 50)
        print("📥 Report Download & History Tracking")
        print("=" * 50)
        
        # 1. Collect initial reports
        reports = collect_method(start_date, end_date)
        
        # Extract downloaded paths
        downloaded_files = [report['xml_path'] for report in reports if 'xml_path' in report]
        
        # 2. History Tracking (Hybrid Approach)
        print("\n🔍 Scanning for correction history...")
        
        # Load existing map
        relation_map = self._load_map_from_excel()
        
        for report in reports:
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
                            
        print(f"\n✅ Total {len(reports)} reports (Total files including history: {len(downloaded_files)}) processed.")
        return downloaded_files, relation_map

    def _convert_downloaded_files(self, file_paths: List[str]) -> dict:
        """Convert encoding of downloaded files to UTF-8."""
        if not file_paths:
            return {"converted": 0, "already_utf8": 0, "errors": 0}
        
        print("\n" + "=" * 50)
        print(f"🔄 Converting {len(file_paths)} files to UTF-8")
        print("=" * 50)
        
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
        
        print(f"\n✅ Converted: {converted} | Already UTF-8: {already_utf8} | Errors: {errors}")
        return {"converted": converted, "already_utf8": already_utf8, "errors": errors}

    def _load_map_from_excel(self) -> dict:
        """Load (rcept_no -> parent_rcp_no) map from existing Excel file."""
        import pandas as pd
        relation_map = {}
        
        if not self.excel_path.exists():
            return relation_map
            
        try:
            # Try loading with header=1 (startrow=1 convention)
            try:
                existing_data = pd.read_excel(self.excel_path, sheet_name=None, header=1)
            except:
                existing_data = pd.read_excel(self.excel_path, sheet_name=None, header=0)

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
            print("⚠️ No Excel file to upload.")
            return
        
        try:
            print("\n" + "=" * 50)
            print("☁️ Uploading to Google Drive")
            print("=" * 50)
            
            file_id = self.google_drive.upload_file(
                self.excel_path,
                self.google_drive_folder_id,
                self.excel_path.name
            )
            print(f"✅ Upload Complete (File ID: {file_id})")
        except Exception as e:
            print(f"❌ Upload Failed: {e}")

    @abstractmethod
    def parse_and_export_to_excel(self) -> int:
        """Abstract method to be implemented by subclasses."""
        pass
