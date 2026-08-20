
"""유무상증자 데이터 처리 서비스

비즈니스 로직을 조합하여 고수준 워크플로우를 제공합니다.
유무상증자 데이터는 별도의 파일(유무상_유상분.xlsx, 유무상_무상분.xlsx)로 저장됩니다.
"""
import os
import sys
import glob
from pathlib import Path
from typing import List, Tuple

from ..domain import CapitalIncreaseDecision, BonusSharesDecision
from ..infrastructure import (
    DualIncreaseXmlParser,
    CapitalIncreaseExcelWriter,
    BonusSharesExcelWriter,
)
from ..infrastructure.excel_utils import apply_auto_column_width
from .base_report_service import BaseReportService


# UTF-8 인코딩 설정 (윈도우 콘솔용)
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


__all__ = ["DualIncreaseService"]


class DualIncreaseService(BaseReportService):
    """유무상증자 데이터 처리 서비스
    
    다운로드, 파싱, 그리고 유상/무상 엑셀 파일로 분리 저장합니다.
    """

    def __init__(
        self,
        data_directory: str = "data/유무상증자",
        api_key: str = None,
        enable_google_drive: bool = True
    ):
        """서비스를 초기화합니다.
        
        Args:
            data_directory: 유무상증자 데이터 저장 디렉토리
            api_key: DART API 키 (None이면 .env에서 로드)
            enable_google_drive: 구글 드라이브 업로드 활성화 여부
        """
        # Super 클래스에는 '유무상증자' 기본 정보를 전달하되, 
        # 실제 업로드는 개별 폴더 ID를 사용하여 수행합니다.
        super().__init__(
            data_directory=data_directory,
            api_key=api_key,
            enable_google_drive=enable_google_drive,
            google_folder_id_env_var="DUAL_INCREASE_GOOGLE_FOLDER_ID", 
            excel_filename="유무상증자_원본.xlsx" 
        )
        self.parser = DualIncreaseXmlParser()
        
        # 메인 엑셀 파일 경로
        self.capital_excel_path = Path("data/유상증자/유상증자.xlsx")
        self.bonus_excel_path = Path("data/무상증자/무상증자.xlsx")
        
        self.capital_writer = CapitalIncreaseExcelWriter(str(self.capital_excel_path))
        self.bonus_writer = BonusSharesExcelWriter(str(self.bonus_excel_path))

        # 개별 구글 드라이브 폴더 ID 로드
        if enable_google_drive:
            self.capital_folder_id = os.getenv("CAPITAL_INCREASE_GOOGLE_FOLDER_ID")
            self.bonus_folder_id = os.getenv("BONUS_SHARES_GOOGLE_FOLDER_ID")
            
            # 부모 클래스에서 기본 폴더 ID가 없어 어댑터가 생성되지 않았더라도,
            # 개별 폴더 ID가 있다면 어댑터를 생성합니다.
            if not self.google_drive and (self.capital_folder_id or self.bonus_folder_id):
                from ..infrastructure import GoogleDriveAdapter
                try:
                    self.google_drive = GoogleDriveAdapter()
                    self.logger.info("Google Drive 어댑터가 개별 폴더 설정을 통해 초기화되었습니다.")
                except Exception as e:
                    self.logger.error(f"Google Drive 어댑터 수동 초기화 실패: {e}")

            if not self.capital_folder_id or not self.bonus_folder_id:
                self.logger.warning("유상/무상 개별 Google Drive 폴더 ID가 설정되지 않았습니다.")

    def _load_map_from_excel(self) -> dict:
        """유상증자 및 무상증자 메인 엑셀에서 관계 맵을 로드합니다."""
        import pandas as pd
        relation_map = {}
        
        for path in [self.capital_excel_path, self.bonus_excel_path]:
            if not path.exists():
                continue
                
            try:
                # header=1 (startrow=1 convention) 시도 후, 실패하면 header=0
                try:
                    existing_data = pd.read_excel(path, sheet_name=None, header=1)
                except:
                    existing_data = pd.read_excel(path, sheet_name=None, header=0)

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
                print(f"⚠️ Error loading relation map from {path}: {e}")
                
        return relation_map

    def parse_and_export_to_excel(self, relation_map: dict = None) -> int:
        """XML 파일들을 파싱하여 유상/무상 엑셀에 각각 병합 저장합니다.

        기존 엑셀 파일이 있다면 로드하여 병합(Merge)합니다.

        Args:
            relation_map: 외부에서 전달받은 관계 맵 (download_reports_with_history에서 생성)
        """
        import pandas as pd
        
        self.logger.info("=" * 50)
        self.logger.info("📊 유무상증자 XML 파싱 및 엑셀 병합")
        self.logger.info("=" * 50)

        # XML 파일 목록 가져오기
        xml_files = glob.glob(str(self.xml_directory / "*.xml"))

        if not xml_files:
            print("❌ 처리할 XML 파일이 없습니다.")
            return 0

        self.logger.info(f"📂 {len(xml_files)}개의 XML 파일을 처리합니다...")

        # 관계 맵 로드 및 병합
        base_map = self.get_relation_map()
        if relation_map:
            base_map.update(relation_map)
            print(f"🔍 로드된 관계 맵: {len(base_map)}건 (외부: {len(relation_map)}건)")
        else:
            print(f"🔍 로드된 관계 맵: {len(base_map)}건")
        relation_map = base_map

        # 파싱
        capital_decisions: List[CapitalIncreaseDecision] = []
        bonus_decisions: List[BonusSharesDecision] = []
        
        import re
        import os
        
        for xml_file in xml_files:
            # 접수번호 추출
            rcept_no = self._extract_rcept_no(xml_file)
            
            # 부모 접수번호 찾기
            parent_rcp = relation_map.get(rcept_no) if rcept_no else None
            
            cap, bonus = self.parser.parse(xml_file, parent_rcp_no=parent_rcp)

            if cap and not cap.is_limited_liability_company():
                capital_decisions.append(cap)
            if bonus and not bonus.is_limited_liability_company():
                bonus_decisions.append(bonus)

        self.logger.info(f"✅ 파싱 완료: 유상분 {len(capital_decisions)}건, 무상분 {len(bonus_decisions)}건")

        # 최초공시일 계산
        self._resolve_original_dates(capital_decisions)
        self._resolve_original_dates(bonus_decisions)

        # 1. 유상증자 병합 저장
        if capital_decisions:
            self._merge_to_main_excel(
                self.capital_writer.output_path, 
                capital_decisions, 
                is_capital=True
            )
            
        # 2. 무상증자 병합 저장
        if bonus_decisions:
            self._merge_to_main_excel(
                self.bonus_writer.output_path, 
                bonus_decisions, 
                is_capital=False
            )

        return len(capital_decisions) + len(bonus_decisions)

    def daily_update(self, days_back: int = 1) -> None:
        """일일 업데이트 워크플로우를 실행합니다.
        
        최근 N일간의 데이터를 다운로드하고 기존 엑셀에 병합합니다.
        """
        from datetime import datetime, timedelta
        
        print("\n" + "📅" * 25)
        print(" " * 10 + f"유무상증자 데이터 Daily 업데이트")
        print("📅" * 25 + "\n")

        # 날짜 계산
        today = datetime.now()
        start_date = (today - timedelta(days=days_back)).strftime("%Y%m%d")
        end_date = today.strftime("%Y%m%d")
        
        print(f"📆 수집 기간: {start_date} ~ {end_date}")

        # 1. 최근 데이터 다운로드 (맵 업데이트 포함)
        downloaded_files, relation_map = self.download_reports_with_history(
            self.api_client.collect_dual_increase_reports,
            start_date,
            end_date
        )
        
        # 2. 다운로드한 파일만 인코딩 변환
        self._convert_downloaded_files(downloaded_files)

        # 3. 파싱 및 엑셀 병합 저장 (이력 정보 전달)
        count = self.parse_and_export_to_excel(relation_map=relation_map)
        self.logger.info(f"📊 파싱 및 병합 완료 건수: {count}")
        
        # 4. 업로드 (메인 파일 업로드)
        if count > 0 and hasattr(self, 'enable_google_drive') and self.enable_google_drive:
             # 경로가 str일 수 있으므로 Path 객체로 보장
             self._upload_to_google_drive_path(Path(self.capital_writer.output_path), self.capital_folder_id)
             self._upload_to_google_drive_path(Path(self.bonus_writer.output_path), self.bonus_folder_id)

        print("\n" + "✨" * 25)
        print(" " * 10 + "유무상증자 Daily 업데이트 완료")
        print("✨" * 25 + "\n")

    def _merge_to_main_excel(self, file_path: Path, new_decisions: List, is_capital: bool) -> None:
        """메인 엑셀 파일에 데이터를 병합하여 저장합니다."""
        import pandas as pd

        self.logger.info(f"🔄 병합 중: {file_path}")

        existing_dfs = self._load_existing_sheets(file_path)
        new_df = self._new_decisions_to_df(new_decisions, is_capital)

        all_dfs = existing_dfs + ([new_df] if not new_df.empty else [])
        if not all_dfs:
            print("  ⚠️ 병합할 데이터가 없습니다.")
            return

        merged_df = pd.concat(all_dfs, ignore_index=True)
        print(f"  🔗 병합 후: {len(merged_df)}건")

        merged_df = self._dedupe_by_rcept_no(merged_df)

        self._save_year_sheets(merged_df, file_path, is_capital)
        print(f"✅ 저장 완료: {file_path}")

    def _load_existing_sheets(self, file_path: Path) -> List:
        """기존 메인 엑셀 파일에서 연도별 시트를 로드합니다.

        파일이 없거나 로드에 실패하면 빈 리스트를 반환합니다.
        """
        import pandas as pd

        if not file_path.exists():
            return []

        try:
            # Try header=1 first (CapitalIncreaseExcelWriter uses startrow=1)
            try:
                existing_sheets = pd.read_excel(file_path, sheet_name=None, header=1)
                # Check if it looks correct (has key column)
                if existing_sheets and not all('접수번호' in df.columns for df in existing_sheets.values() if not df.empty):
                    raise ValueError("Some sheets missing '접수번호' with header=1")
            except Exception:
                existing_sheets = pd.read_excel(file_path, sheet_name=None, header=0)

            dfs = []
            existing_count = 0
            for sheet, df in existing_sheets.items():
                if '접수번호' in df.columns:
                    try:
                        df['연도'] = int(sheet)
                    except (TypeError, ValueError):
                        df['연도'] = sheet
                    existing_count += len(df)
                    dfs.append(df)

            print(f"  📂 기존 데이터 로드: {existing_count}건 ({len(existing_sheets)}개 시트)")
            return dfs
        except Exception as e:
            print(f"  ⚠️ 기존 파일 로드 실패 (새로 생성합니다): {e}")
            return []

    def _new_decisions_to_df(self, new_decisions: List, is_capital: bool):
        """신규 결정 목록을 DataFrame으로 변환합니다.

        Writer의 _to_row_dict 로직을 재사용하기 위해 기존 Writer 인스턴스를 사용합니다.
        """
        import pandas as pd

        writer = self.capital_writer if is_capital else self.bonus_writer
        new_rows = [writer._to_row_dict(d) for d in new_decisions]
        new_df = pd.DataFrame(new_rows)
        print(f"  ➕ 신규 데이터: {len(new_df)}건")
        return new_df

    def _dedupe_by_rcept_no(self, merged_df):
        """접수번호 기준 중복을 제거합니다 (뒤에 병합된 데이터를 우선 유지).

        기존 시트는 Excel에서 숫자로, 신규 데이터는 문자열로 읽혀 접수번호의 dtype이
        섞일 수 있어(예: 20240101000001 vs "20240101000001") 비교 전에 문자열로 정규화합니다.
        """
        if '접수번호' not in merged_df.columns:
            return merged_df

        before_dedup = len(merged_df)
        merged_df = merged_df.copy()
        merged_df['접수번호'] = merged_df['접수번호'].astype(str).str.replace(r'\.0$', '', regex=True)
        merged_df = merged_df.drop_duplicates(subset=['접수번호'], keep='last')
        print(f"  🗑️ 중복 제거: {before_dedup - len(merged_df)}건 제거됨 (최종 {len(merged_df)}건)")
        return merged_df

    def _save_year_sheets(self, merged_df, file_path: Path, is_capital: bool) -> None:
        """병합된 DataFrame을 연도별 시트로 분리하여 엑셀 파일로 저장합니다."""
        # 연도 없는 데이터 필터링
        merged_df = merged_df[merged_df["연도"].notna()]

        # 일자 기준 오름차순 정렬
        if "일자" in merged_df.columns:
            merged_df = merged_df.sort_values(by="일자", ascending=True)

        # 연도별로 그룹화
        years = sorted(merged_df["연도"].unique())

        # 디렉토리 생성
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # 컬럼 순서 선택 (is_capital에 따라)
        cols = self.capital_writer.EXCEL_COLUMNS if is_capital else self.bonus_writer.EXCEL_COLUMNS

        import pandas as pd
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            for year in years:
                # 연도 컬럼이 float일 수 있으므로 int 변환 안전하게
                try:
                    year_val = int(year)
                except (TypeError, ValueError):
                    year_val = str(year)

                # 해당 연도 데이터 추출
                year_df = merged_df[merged_df["연도"] == year]

                # 컬럼이 존재하는지 확인 후 선택
                available_cols = [c for c in cols if c in year_df.columns]
                year_df = year_df[available_cols]

                sheet_name = str(year_val)
                year_df.to_excel(writer, sheet_name=sheet_name, index=False, startrow=1)

                # 열 너비 자동 조정 (Best Fit) 적용
                apply_auto_column_width(writer.sheets[sheet_name])

                self.logger.info(f"  [{sheet_name}] 시트: {len(year_df)}건 (Best Fit 적용)")

    def full_update(self, start_date: str = "20200101", end_date: str = None) -> None:
        """전체 업데이트 워크플로우를 실행합니다."""
        print("\n" + "🚀" * 25)
        print(" " * 10 + "유무상증자 데이터 전체 업데이트 (Main 병합)")
        print("🚀" * 25 + "\n")

        # 1. 다운로드 (맵 업데이트 포함)
        # 유무상증자는 별도 History Scraper를 돌리더라도, Parent가 '유상증자'일수도 '유무상'일수도 있음.
        # 일단 기본 로직 사용.
        downloaded_files, relation_map = self.download_reports_with_history(
            self.api_client.collect_dual_increase_reports,
            start_date,
            end_date
        )

        # 2. 다운로드한 파일만 인코딩 변환
        self._convert_downloaded_files(downloaded_files)

        # 3. 파싱 및 엑셀 병합 저장 (이력 정보 전달)
        self.parse_and_export_to_excel(relation_map=relation_map)
        
        # 4. 구글 드라이브 업로드 (Main 파일 업로드)
        # Main 파일을 업로드해야 함.
        # 하지만 다른 서비스(Capital/Bonus)가 나중에 돌면 또 업로드할 것임.
        # 여기서는 업로드 생략하거나 Main 파일 업로드.
        if hasattr(self, 'enable_google_drive') and self.enable_google_drive:
            self._upload_to_google_drive_path(self.capital_writer.output_path, self.capital_folder_id)
            self._upload_to_google_drive_path(self.bonus_writer.output_path, self.bonus_folder_id)

        print("\n" + "🎉" * 25)
        print(" " * 15 + "전체 업데이트 완료!")
        print("🎉" * 25 + "\n")

    def _upload_to_google_drive_path(self, path: Path, folder_id: str = None):
        """특정 경로 파일 특정 폴더로 업로드"""
        # folder_id가 인자로 전달되지 않으면 기본 ID 사용
        target_folder = folder_id if folder_id else self.google_drive_folder_id
        
        if not self.google_drive or not target_folder:
            return
        if path.exists():
            try:
                self.google_drive.upload_file(path, target_folder, path.name)
                self.logger.info(f"☁️ 구글 드라이브 업로드: {path.name} (Folder ID: {target_folder})")
            except Exception as e:
                self.logger.error(f"❌ 업로드 실패 ({path.name}): {e}")
