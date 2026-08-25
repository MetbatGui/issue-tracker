"""전환사채 데이터 처리 서비스

비즈니스 로직을 조합하여 고수준 워크플로우를 제공합니다.

DB(SQLite)가 SSOT입니다: XML 파싱 결과는 ConvertibleBondSqliteRepository에 upsert되고,
Excel은 매 실행마다 DB 전체를 읽어 재구성되는 산출물입니다.
"""
import sys
import glob
from pathlib import Path
from typing import List

from ..domain import ConvertibleBondDecision
from ..infrastructure import (
    ConvertibleBondXmlParser,
    ConvertibleBondExcelWriter,
)
from ..infrastructure.convertible_bond_sqlite_repository import ConvertibleBondSqliteRepository
from .base_report_service import BaseReportService
from .daily_orchestration_service import LocalUpdateResult, SyncTarget


# UTF-8 인코딩 설정 (윈도우 콘솔용)
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


__all__ = ["ConvertibleBondService"]


class ConvertibleBondService(BaseReportService):
    """전환사채 데이터 처리 서비스

    다운로드, 파싱, DB 저장, 엑셀 재구성 워크플로우를 조합합니다.
    """

    def __init__(
        self,
        data_directory: str = "data/전환사채",
        api_key: str = None,
        enable_google_drive: bool = True
    ):
        """서비스를 초기화합니다.

        Args:
            data_directory: 데이터 저장 디렉토리
            api_key: DART API 키 (None이면 .env에서 로드)
            enable_google_drive: 구글 드라이브 업로드 활성화 여부
        """
        super().__init__(
            data_directory=data_directory,
            api_key=api_key,
            enable_google_drive=enable_google_drive,
            google_folder_id_env_var="CONVERTIBLE_BOND_GOOGLE_FOLDER_ID",
            excel_filename="전환사채.xlsx"
        )
        self.parser = ConvertibleBondXmlParser()
        self.excel_writer = ConvertibleBondExcelWriter(output_path=str(self.excel_path))
        self.repository = ConvertibleBondSqliteRepository(str(self.data_directory / "전환사채.db"))

    def get_relation_map(self) -> dict:
        """DB에 저장된 parent_rcp_no 관계를 관계맵으로 반환합니다.

        DB가 SSOT이므로 relation_map.json/Excel 폴백(BaseReportService의 기본 구현)은 쓰지 않습니다.
        """
        return {
            d.rcept_no: d.parent_rcp_no
            for d in self.repository.get_all()
            if d.parent_rcp_no
        }

    def _parse_file_with_map(self, file_path: str, relation_map: dict) -> ConvertibleBondDecision:
        """관계 맵을 사용하여 XML 파일을 파싱합니다."""

        # 접수번호 추출
        rcept_no = self._extract_rcept_no(file_path)

        parent_rcp = relation_map.get(rcept_no) if rcept_no else None

        return self.parser.parse(file_path, rcept_no=rcept_no, parent_rcp_no=parent_rcp)

    def parse_and_export_to_excel(self, relation_map: dict = None, export: bool = True) -> int:
        """XML 파일들을 파싱해 DB에 반영한 뒤, DB 전체로 엑셀을 재구성합니다."""
        print("\n" + "=" * 50)
        print("📊 XML 파싱 및 DB 반영")
        print("=" * 50)

        # XML 파일 목록 가져오기
        xml_files = glob.glob(str(self.xml_directory / "*.xml"))

        if not xml_files:
            print("❌ 처리할 XML 파일이 없습니다.")
            return 0

        print(f"📂 {len(xml_files)}개의 XML 파일을 처리합니다...")

        # 관계 맵 로드 (DB 기준)
        base_map = self.get_relation_map()
        if relation_map:
            base_map.update(relation_map)
        relation_map = base_map

        # 파싱
        decisions: List[ConvertibleBondDecision] = []
        for xml_file in xml_files:
            decision = self._parse_file_with_map(xml_file, relation_map)
            if decision:
                decisions.append(decision)

        print(f"✅ {len(decisions)}건의 데이터를 파싱했습니다.")

        if decisions:
            self.repository.upsert(decisions)
            print(f"💾 DB 반영 완료: {len(decisions)}건")

        return self.export_to_excel() if export else len(decisions)

    def _local_update_result(self) -> LocalUpdateResult:
        database_path = Path(self.repository.db_path)
        return LocalUpdateResult(targets=[
            SyncTarget(
                database_path=database_path,
                excel_path=self.excel_path,
                export_excel=self.export_to_excel,
                upload_excel=lambda: self._upload_file_to_google_drive(self.excel_path),
                upload_database=lambda: self._upload_file_to_google_drive(database_path),
            )
        ])

    def _result_after_collection(self, downloaded_files: List[str], relation_map: dict) -> LocalUpdateResult:
        if downloaded_files:
            return self._local_update_result() if self.parse_and_export_to_excel(relation_map, export=False) else LocalUpdateResult.empty()
        if not self.excel_path.exists() and self.repository.get_all():
            return self._local_update_result()
        return LocalUpdateResult.empty()

    def export_to_excel(self) -> int:
        """DB에 저장된 전체 데이터를 엑셀로 재구성합니다."""
        decisions = self.repository.get_all()

        if not decisions:
            print("⚠️ 저장할 데이터가 없습니다.")
            return 0

        # 최초공시일 계산 (parent_rcp_no 체인을 따라가는 파생값이라 DB에는 저장하지 않고 매번 계산)
        self._resolve_original_dates(decisions)

        self.excel_writer.write(decisions)
        return len(decisions)

    def full_update(self, start_date: str = "20200101", end_date: str = None) -> LocalUpdateResult:
        """전체 업데이트 워크플로우를 실행합니다."""
        print("\n" + "🚀" * 25)
        print(" " * 10 + "전환사채 데이터 전체 업데이트")
        print("🚀" * 25 + "\n")

        downloaded_files, relation_map = self.run_pipeline(
            self.api_client.collect_convertible_bond_reports,
            start_date,
            end_date
        )

        result = self._result_after_collection(downloaded_files, relation_map)
        print("\n" + "🎉" * 25)
        print(" " * 15 + "전체 업데이트 완료!")
        print("🎉" * 25 + "\n")
        return result

    def daily_update(self, days_back: int = 30) -> LocalUpdateResult:
        """일일 업데이트 워크플로우를 실행합니다.

        최근 N일간의 데이터를 다운로드하고 기존 엑셀에 병합합니다.
        """
        from datetime import datetime, timedelta

        print("\n" + "📅" * 25)
        print(" " * 10 + f"전환사채 데이터 Daily 업데이트")
        print("📅" * 25 + "\n")

        # 날짜 계산
        today = datetime.now()
        start_date = (today - timedelta(days=days_back)).strftime("%Y%m%d")

        print(f"📆 수집 기간: {start_date} ~ Today")

        downloaded_files, relation_map = self.run_pipeline(
            self.api_client.collect_convertible_bond_reports,
            start_date,
            skip_if_no_new_files=True
        )

        print("\n" + "🎉" * 25)
        print(" " * 15 + "Daily 업데이트 완료!")
        result = self._result_after_collection(downloaded_files, relation_map)
        print("🎉" * 25 + "\n")
        return result
