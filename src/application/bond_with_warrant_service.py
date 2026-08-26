"""신주인수권부사채 분석 서비스

신주인수권부사채 공시 데이터를 수집, 파싱하고 엑셀로 저장하는 서비스입니다.

DB(SQLite)가 SSOT입니다: XML 파싱 결과는 BondWithWarrantSqliteRepository에 upsert되고,
Excel은 매 실행마다 DB 전체를 읽어 재구성되는 산출물입니다.
"""
import io
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timedelta

from .base_report_service import BaseReportService
from ..domain import BondWithWarrantDecision
from ..infrastructure.bond_with_warrant_xml_parser import BondWithWarrantXmlParser
from ..infrastructure.bond_with_warrant_excel_writer import BondWithWarrantExcelWriter
from ..infrastructure.bond_with_warrant_sqlite_repository import BondWithWarrantSqliteRepository
from ..infrastructure.sqlite_storage_session import SqliteStorageSession
from ..infrastructure.dart_api import DownloadedXml
from .daily_orchestration_service import LocalUpdateResult, SyncTarget


__all__ = ["BondWithWarrantService"]


class BondWithWarrantService(BaseReportService):
    """신주인수권부사채 분석 서비스"""

    def __init__(
        self,
        dart_api_key: str,
        data_directory: str = "data/신주인수권부사채",
        output_path: str = "data/신주인수권부사채/신주인수권부사채.xlsx",
        enable_google_drive: bool = True
    ):
        """서비스 초기화

        Args:
            dart_api_key: DART API 키
            data_directory: 데이터 저장 디렉토리
            output_path: 결과 엑셀 파일 경로
            enable_google_drive: 구글 드라이브 업로드 활성화 여부
        """
        super().__init__(
            data_directory=data_directory,
            api_key=dart_api_key,
            enable_google_drive=enable_google_drive,
            google_folder_id_env_var="BOND_WITH_WARRANT_GOOGLE_FOLDER_ID",
            excel_filename="신주인수권부사채.xlsx"
        )
        self.output_path = output_path

        self.xml_parser = BondWithWarrantXmlParser()
        self.excel_writer = BondWithWarrantExcelWriter(str(self.excel_path))
        self.database_session = SqliteStorageSession(self.source_storage, self.data_directory / "신주인수권부사채.db")
        self.repository = BondWithWarrantSqliteRepository(str(self.database_session.working_path))

    def get_relation_map(self) -> dict:
        """DB에 저장된 parent_rcp_no 관계를 관계맵으로 반환합니다.

        DB가 SSOT이므로 relation_map.json/Excel 폴백(BaseReportService의 기본 구현)은 쓰지 않습니다.
        """
        return {
            d.rcept_no: d.parent_rcp_no
            for d in self.repository.get_all()
            if d.parent_rcp_no
        }

    def _parse_document_with_map(self, document: DownloadedXml, relation_map: dict) -> Optional[BondWithWarrantDecision]:
        """메모리 XML과 관계 맵으로 결정 객체를 만든다."""
        return self.xml_parser.parse(
            io.BytesIO(document.content), rcept_no=document.rcept_no,
            parent_rcp_no=relation_map.get(document.rcept_no), source_filename=document.source_filename,
        )

    def parse_and_export_to_excel(self, documents: List[DownloadedXml], relation_map: dict = None, export: bool = True) -> int:
        """XML 파일들을 파싱해 DB에 반영한 뒤, DB 전체로 엑셀을 재구성합니다."""
        self.logger.info("\n" + "=" * 50)
        self.logger.info("📊 XML 파싱 및 DB 반영")
        self.logger.info("=" * 50)

        if not documents:
            self.logger.warning("처리할 메모리 XML이 없습니다.")
            return self.export_to_excel() if export else 0

        self.logger.info(f"{len(documents)}개의 메모리 XML을 처리합니다...")

        # 관계 맵 로드 (DB 기준)
        base_map = self.get_relation_map()
        if relation_map:
            base_map.update(relation_map)
        relation_map = base_map

        decisions: List[BondWithWarrantDecision] = []
        for document in documents:
            decision = self._parse_document_with_map(document, relation_map)
            if decision:
                decisions.append(decision)

        self.logger.info(f"{len(decisions)}건의 데이터를 파싱했습니다.")

        if decisions:
            self.repository.upsert(decisions)
            self.logger.info(f"DB 반영 완료: {len(decisions)}건")

        return self.export_to_excel() if export else len(decisions)

    def _local_update_result(self) -> LocalUpdateResult:
        database_path = self.database_session.storage_path
        return LocalUpdateResult(targets=[
            SyncTarget(
                database_path=database_path,
                excel_path=self.excel_path,
                export_excel=self.export_to_excel,
                upload_excel=lambda: self._upload_file_to_google_drive(self.excel_path),
                upload_database=lambda: self._persist_and_upload_database(database_path),
            )
        ])

    def _persist_and_upload_database(self, database_path: Path) -> None:
        if not self.database_session.persist():
            raise RuntimeError(f"SQLite SSOT 반영 실패: {database_path}")
        self._upload_file_to_google_drive(database_path)

    def _result_after_collection(self, documents: List[DownloadedXml], relation_map: dict) -> LocalUpdateResult:
        if documents:
            changed_count = self.parse_and_export_to_excel(documents, relation_map, export=False)
            if changed_count:
                if not self.database_session.persist():
                    raise RuntimeError("SQLite SSOT 반영 실패")
                return self._local_update_result()
            return LocalUpdateResult.empty()
        if not self.excel_path.exists() and self.repository.get_all():
            return self._local_update_result()
        return LocalUpdateResult.empty()

    def export_to_excel(self) -> int:
        """DB에 저장된 전체 데이터를 엑셀로 재구성합니다."""
        decisions = self.repository.get_all()

        if not decisions:
            self.logger.warning("저장할 데이터가 없습니다.")
            return 0

        # 최초공시일 계산 (parent_rcp_no 체인을 따라가는 파생값이라 DB에는 저장하지 않고 매번 계산)
        self._resolve_original_dates(decisions)

        self.excel_writer.write(decisions)
        return len(decisions)

    def export_update(self) -> LocalUpdateResult:
        """SSOT DB로 Excel을 재생성하고 오케스트레이터에 동기화 대상을 반환한다."""
        return self._local_update_result() if self.repository.get_all() else LocalUpdateResult.empty()

    def daily_update(self, days: int = 30, today=None) -> LocalUpdateResult:
        """일일 업데이트 (최근 N일)"""
        end_date = today or datetime.now()
        start_date = end_date - timedelta(days=days)
        start_str = start_date.strftime("%Y%m%d")

        self.logger.info(f"신주인수권부사채 일일 업데이트 시작: {start_str} ~")

        documents, relation_map = self.run_pipeline(
            self.api_client.collect_bond_with_warrant_reports,
            start_str,
            skip_if_no_new_files=True,
            existing_rcept_nos=self.repository.existing_rcept_nos,
        )
        return self._result_after_collection(documents, relation_map)

    def full_update(self, start_date: str = "20200101") -> LocalUpdateResult:
        """전체 업데이트"""
        self.logger.info(f"신주인수권부사채 전체 업데이트 시작: {start_date} ~")

        documents, relation_map = self.run_pipeline(
            self.api_client.collect_bond_with_warrant_reports,
            start_date,
            existing_rcept_nos=self.repository.existing_rcept_nos,
        )
        return self._result_after_collection(documents, relation_map)
