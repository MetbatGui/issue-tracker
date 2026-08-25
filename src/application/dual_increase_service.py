"""유무상증자 데이터 처리 서비스

비즈니스 로직을 조합하여 고수준 워크플로우를 제공합니다.

유무상증자 공시는 한 건이 유상증자 결정과 무상증자 결정으로 동시에 이루어집니다. 이 서비스는
그 공시를 수집·파싱해서 둘로 쪼개는 역할만 하고, 저장은 CapitalIncreaseService/BonusSharesService가
이미 소유한 SQLite SSOT(유상증자.db/무상증자.db)에 그대로 upsert합니다 — 쪼갠 결정도 결국
CapitalIncreaseDecision/BonusSharesDecision과 동일한 엔티티이므로 별도 스토리지를 둘 이유가
없고, DB upsert는 순서 무관이라 오케스트레이션 실행 순서에 결과가 좌우되던 문제(기존 Excel
직접 병합 방식의 약점)도 함께 사라집니다.
"""
import sys
import glob
from typing import List

from ..domain import CapitalIncreaseDecision, BonusSharesDecision
from ..infrastructure import DualIncreaseXmlParser
from .base_report_service import BaseReportService
from .capital_increase_services import CapitalIncreaseService
from .bonus_services import BonusSharesService
from .daily_orchestration_service import LocalUpdateResult


# UTF-8 인코딩 설정 (윈도우 콘솔용)
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


__all__ = ["DualIncreaseService"]


class DualIncreaseService(BaseReportService):
    """유무상증자 데이터 처리 서비스

    다운로드, 파싱, 그리고 유상/무상 두 결정으로 분리해 각자의 서비스에 위임 저장합니다.
    """

    def __init__(
        self,
        data_directory: str = "data/유무상증자",
        capital_data_directory: str = "data/유상증자",
        bonus_data_directory: str = "data/무상증자",
        api_key: str = None,
        enable_google_drive: bool = True
    ):
        """서비스를 초기화합니다.

        Args:
            data_directory: 유무상증자 공시 XML을 저장할 디렉토리
            capital_data_directory: 유상분을 위임할 CapitalIncreaseService의 데이터 디렉토리
            bonus_data_directory: 무상분을 위임할 BonusSharesService의 데이터 디렉토리
            api_key: DART API 키 (None이면 .env에서 로드)
            enable_google_drive: 구글 드라이브 업로드 활성화 여부
        """
        # 이 서비스 자체는 별도 구글 드라이브 폴더를 갖지 않음 - 업로드는 capital_service/bonus_service에 위임
        super().__init__(
            data_directory=data_directory,
            api_key=api_key,
            enable_google_drive=False,
            excel_filename="유무상증자_원본.xlsx"
        )
        self.parser = DualIncreaseXmlParser()

        # 유상/무상 결정 저장·엑셀재구성·업로드를 그대로 위임할 서비스 (같은 DB/Excel 파일을 소유)
        self.capital_service = CapitalIncreaseService(
            data_directory=capital_data_directory,
            api_key=api_key,
            enable_google_drive=enable_google_drive,
        )
        self.bonus_service = BonusSharesService(
            data_directory=bonus_data_directory,
            api_key=api_key,
            enable_google_drive=enable_google_drive,
        )

    def get_relation_map(self) -> dict:
        """유상/무상 각 서비스의 DB 기준 관계맵을 합쳐서 반환합니다.

        유무상증자 공시에서 파생된 결정도 rcept_no가 원본 공시와 동일하게 유지되므로,
        정정이력(parent_rcp_no)은 이미 각 서비스의 DB에 저장되어 있습니다.
        """
        merged = self.capital_service.get_relation_map()
        merged.update(self.bonus_service.get_relation_map())
        return merged

    def _existing_rcept_nos(self, rcept_nos: List[str]) -> set[str]:
        """유무상 공시는 유상·무상 DB 양쪽에 모두 있을 때만 완료로 판단한다."""
        capital_existing = self.capital_service.repository.existing_rcept_nos(rcept_nos)
        bonus_existing = self.bonus_service.repository.existing_rcept_nos(rcept_nos)
        return capital_existing & bonus_existing

    def parse_and_export_to_excel(self, relation_map: dict = None, export: bool = True) -> int:
        """XML 파일들을 파싱해 유상/무상 결정으로 분리한 뒤, 각 서비스의 DB에 반영하고
        각 서비스의 엑셀을 재구성합니다.
        """
        self.logger.info("\n" + "=" * 50)
        self.logger.info("유무상증자 XML 파싱 및 DB 반영")
        self.logger.info("=" * 50)

        xml_files = self._pending_xml_files(self._existing_rcept_nos)

        if not xml_files:
            self.logger.warning("처리할 XML 파일이 없습니다.")
            if export:
                return self.capital_service.export_to_excel() + self.bonus_service.export_to_excel()
            return 0

        self.logger.info(f"{len(xml_files)}개의 XML 파일을 처리합니다...")

        # 관계 맵 로드 (유상/무상 DB 기준)
        base_map = self.get_relation_map()
        if relation_map:
            base_map.update(relation_map)
        relation_map = base_map

        capital_decisions: List[CapitalIncreaseDecision] = []
        bonus_decisions: List[BonusSharesDecision] = []

        for xml_file in xml_files:
            rcept_no = self._extract_rcept_no(xml_file)
            parent_rcp = relation_map.get(rcept_no) if rcept_no else None

            cap, bonus = self.parser.parse(xml_file, parent_rcp_no=parent_rcp)

            if cap and not cap.is_limited_liability_company():
                capital_decisions.append(cap)
            if bonus and not bonus.is_limited_liability_company():
                bonus_decisions.append(bonus)

        self.logger.info(f"파싱 완료: 유상분 {len(capital_decisions)}건, 무상분 {len(bonus_decisions)}건")

        if capital_decisions:
            self.capital_service.repository.upsert(capital_decisions)
        if bonus_decisions:
            self.bonus_service.repository.upsert(bonus_decisions)

        if export:
            self.capital_service.export_to_excel()
            self.bonus_service.export_to_excel()

        return len(capital_decisions) + len(bonus_decisions)

    def _local_update_result(self) -> LocalUpdateResult:
        return LocalUpdateResult(
            targets=(
                self.capital_service._local_update_result().targets
                + self.bonus_service._local_update_result().targets
            )
        )

    def close(self) -> None:
        """위임한 유상·무상 서비스의 SQLite 작업 사본도 함께 정리한다."""
        self.capital_service.close()
        self.bonus_service.close()
        super().close()

    def _result_after_collection(self, downloaded_files: List[str], relation_map: dict) -> LocalUpdateResult:
        if downloaded_files:
            changed_count = self.parse_and_export_to_excel(relation_map, export=False)
            if changed_count:
                if not self.capital_service.database_session.persist():
                    raise RuntimeError("유상증자 SQLite SSOT 반영 실패")
                if not self.bonus_service.database_session.persist():
                    raise RuntimeError("무상증자 SQLite SSOT 반영 실패")
                return self._local_update_result()
            return LocalUpdateResult.empty()

        has_missing_output = (
            (not self.capital_service.excel_path.exists() and self.capital_service.repository.get_all())
            or (not self.bonus_service.excel_path.exists() and self.bonus_service.repository.get_all())
        )
        return self._local_update_result() if has_missing_output else LocalUpdateResult.empty()

    def full_update(self, start_date: str = "20200101", end_date: str = None) -> LocalUpdateResult:
        """전체 업데이트 워크플로우를 실행합니다."""
        self.logger.info("유무상증자 전체 업데이트 시작")

        downloaded_files, relation_map = self.run_pipeline(
            self.api_client.collect_dual_increase_reports,
            start_date,
            end_date,
            existing_rcept_nos=self._existing_rcept_nos,
        )

        result = self._result_after_collection(downloaded_files, relation_map)
        self.logger.info("유무상증자 전체 업데이트 완료")
        return result

    def daily_update(self, days_back: int = 1, today=None) -> LocalUpdateResult:
        """일일 업데이트 워크플로우를 실행합니다.

        최근 N일간의 데이터를 다운로드하고 유상/무상 각 서비스의 DB/엑셀에 반영합니다.
        """
        from datetime import datetime, timedelta

        self.logger.info("유무상증자 일일 업데이트 시작")

        today = today or datetime.now()
        start_date = (today - timedelta(days=days_back)).strftime("%Y%m%d")

        self.logger.info(f"수집 기간: {start_date} ~ Today")

        downloaded_files, relation_map = self.run_pipeline(
            self.api_client.collect_dual_increase_reports,
            start_date,
            skip_if_no_new_files=True,
            existing_rcept_nos=self._existing_rcept_nos,
        )

        result = self._result_after_collection(downloaded_files, relation_map)
        self.logger.info("유무상증자 일일 업데이트 완료")
        return result
